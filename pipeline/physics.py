"""示意性漏磁场计算（轴对称 r-z 有限差分，仅用于画图，不代表任何真实产品）。

模型：心式变压器的一个“铁窗”。
- 铁心柱在 r < core_r，上下铁轭在 |z| > yoke_z，外侧 r = outer_r 处是旁柱/油箱壁。
  铁按理想导磁体（mu -> 无穷）处理：窗口边界上磁力线垂直进入铁面（Neumann 边界）。
- 内绕组（低压）、外绕组（高压）是均匀电流密度的圆筒，电流方向相反、安匝相等。
- 求解磁通函数 psi = r * A_phi：
      d/dr( (1/r) dpsi/dr ) + (1/r) d2psi/dz2 = -J
  磁力线就是 psi 的等值线；B_r = -(1/r) dpsi/dz，B_z = (1/r) dpsi/dr；
  体力密度 f = J_phi * phi^ x B = J * (B_z, -B_r)。

坐标：r 为径向（画面横向，离开铁心为正），z 为轴向（画面纵向）。单位任意，只保留形状和方向。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.interpolate import RegularGridInterpolator


@dataclass
class WindingSection:
    """铁窗 + 内外两个同心绕组。只描述剖面右半边，左半边与之镜像对称。"""

    core_r: float = 0.9          # 铁心柱半径
    lv: tuple = (1.15, 1.65)     # 内绕组（低压）径向范围
    hv: tuple = (2.15, 2.65)     # 外绕组（高压）径向范围
    half_h: float = 2.5          # 绕组半高
    yoke_z: float = 3.1          # 铁轭下表面高度
    outer_r: float = 3.6         # 窗口外边界
    res: float = 0.02

    def __post_init__(self):
        r = np.arange(self.core_r + self.res / 2, self.outer_r, self.res)
        z = np.arange(-self.yoke_z + self.res / 2, self.yoke_z, self.res)
        self.r, self.z = r, z
        R, Z = np.meshgrid(r, z, indexing="ij")
        inside = np.abs(Z) <= self.half_h
        J = np.zeros_like(R)
        m_lv = inside & (R >= self.lv[0]) & (R <= self.lv[1])
        m_hv = inside & (R >= self.hv[0]) & (R <= self.hv[1])
        # 安匝平衡（离散意义上精确平衡）：两绕组总电流大小相等、方向相反
        J[m_lv] = 1.0 / m_lv.sum()
        J[m_hv] = -1.0 / m_hv.sum()
        J *= 1.0 / (self.res * self.res) * 0.5  # 只是缩放
        self.Jgrid = J
        self.psi_grid = self._solve(r, z, J)
        P = self.psi_grid
        dr = self.res
        dpsi_dr = np.gradient(P, dr, axis=0)
        dpsi_dz = np.gradient(P, dr, axis=1)
        self.Br = -dpsi_dz / R
        self.Bz = dpsi_dr / R
        kw = dict(bounds_error=False, fill_value=0.0)
        self._ip = {
            "psi": RegularGridInterpolator((r, z), P, **kw),
            "Br": RegularGridInterpolator((r, z), self.Br, **kw),
            "Bz": RegularGridInterpolator((r, z), self.Bz, **kw),
        }

    def _solve(self, r, z, J):
        nr, nz = len(r), len(z)
        h = self.res
        idx = np.arange(nr * nz).reshape(nr, nz)
        rows, cols, vals = [], [], []

        def add(i, j, v):
            rows.append(i); cols.append(j); vals.append(v)

        r_half_p = r + h / 2
        r_half_m = r - h / 2
        for i in range(nr):
            for j in range(nz):
                k = idx[i, j]
                diag = 0.0
                if i + 1 < nr:  # r 方向通量（超出边界即 Neumann，直接略去）
                    c = 1.0 / (r_half_p[i] * h * h)
                    add(k, idx[i + 1, j], c); diag -= c
                if i - 1 >= 0:
                    c = 1.0 / (r_half_m[i] * h * h)
                    add(k, idx[i - 1, j], c); diag -= c
                c = 1.0 / (r[i] * h * h)
                if j + 1 < nz:
                    add(k, idx[i, j + 1], c); diag -= c
                if j - 1 >= 0:
                    add(k, idx[i, j - 1], c); diag -= c
                add(k, k, diag)
        A = sp.csr_matrix((vals, (rows, cols)), shape=(nr * nz, nr * nz)).tolil()
        b = -J.ravel().copy()
        # 纯 Neumann 问题有常数自由度：固定一个点
        A[0, :] = 0
        A[0, 0] = 1.0
        b[0] = 0.0
        psi = spla.spsolve(A.tocsr(), b)
        return psi.reshape(nr, nz)

    # ---- 场量 -------------------------------------------------------------
    def B(self, r, z):
        pts = np.stack(np.broadcast_arrays(np.abs(np.asarray(r, float)), np.asarray(z, float)), -1)
        return self._ip["Br"](pts), self._ip["Bz"](pts)

    def J_at(self, r, z):
        r = np.asarray(r, float); z = np.asarray(z, float)
        inside = np.abs(z) <= self.half_h
        j = np.where(inside & (r >= self.lv[0]) & (r <= self.lv[1]), 1.0, 0.0)
        return np.where(inside & (r >= self.hv[0]) & (r <= self.hv[1]), -1.0, j)

    def force(self, r, z):
        """洛伦兹力密度方向 f = J_phi * (B_z, -B_r)，返回 (f_r, f_z)（单位任意）。"""
        br, bz = self.B(r, z)
        j = self.J_at(r, z)
        return j * bz, -j * br

    # ---- 磁力线 -----------------------------------------------------------
    def field_lines(self, n_lines: int = 8, lo: float = 0.08, hi: float = 0.92):
        """返回右半剖面的磁力线（每条为 (N,2) 数组 [r, z]），由强到弱排列。"""
        import contourpy

        R, Z = np.meshgrid(self.r, self.z, indexing="ij")
        P = self.psi_grid
        pmin, pmax = P.min(), P.max()
        gen = contourpy.contour_generator(R, Z, P)
        lines = []
        # psi 在两绕组之间的缝隙里变化最快；取 psi 的均匀间隔，线密度就反映磁场强弱
        for frac in np.linspace(lo, hi, n_lines):
            segs = gen.lines(pmin + frac * (pmax - pmin))
            lines.extend(np.asarray(s) for s in segs if len(s) > 10)
        return lines

    def disc_axial_forces(self, which: str, n_discs: int):
        """把绕组按高度分成 n_discs 个线饼，返回每个线饼的中心高度和平均轴向力。"""
        r0, r1 = self.lv if which == "lv" else self.hv
        edges = np.linspace(-self.half_h, self.half_h, n_discs + 1)
        rs = np.linspace(r0, r1, 7)[1:-1]
        zc, fz = [], []
        for a, b in zip(edges[:-1], edges[1:]):
            zs = np.linspace(a, b, 7)[1:-1]
            R, Z = np.meshgrid(rs, zs)
            _, f = self.force(R, Z)
            zc.append(0.5 * (a + b)); fz.append(f.mean())
        return np.array(zc), np.array(fz)
