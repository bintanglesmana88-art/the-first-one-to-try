"""Manim 公共组件：按配音时间轴卡点的场景基类 + 变压器剖面/俯视图等可复用画面。"""
from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from manim import (
    BOLD, DOWN, LEFT, ORIGIN, RIGHT, UP, Arrow, Circle, Dot, Line, Rectangle, RoundedRectangle,
    Scene, Text, VGroup, VMobject, config,
)

from .physics import WindingSection

# ---------------------------------------------------------------- 风格
FONT = "Noto Sans CJK SC"
BG = "#0E1621"
TEXT = "#E8EEF5"
DIM = "#8A97A8"
CORE = "#4A5563"
CORE_EDGE = "#7C8796"
LV = "#F2A541"      # 内绕组（低压）
HV = "#4FA3E0"      # 外绕组（高压）
FIELD = "#7CFFCB"   # 磁力线
FORCE = "#FF5A5F"   # 力
ACCENT = "#FFD166"
SPACER = "#C9B79C"

config.background_color = BG


def T(text, size=36, color=TEXT, bold=False, **kw) -> Text:
    return Text(text, font=FONT, font_size=size, color=color, weight=BOLD if bold else "NORMAL", **kw)


def tag(text: str, color=ACCENT, size=26) -> VGroup:
    """圆角底色的小标签。"""
    t = T(text, size, color=BG, bold=True)
    box = RoundedRectangle(corner_radius=0.12, width=t.width + 0.4, height=t.height + 0.24,
                           fill_color=color, fill_opacity=1, stroke_width=0)
    return VGroup(box, t.move_to(box))


def corner_tag(text="EP01 · 变压器短路") -> Text:
    return T(text, 22, color=DIM).to_corner(UP + LEFT, buff=0.3)


# ---------------------------------------------------------------- 场景基类
class NarratedScene(Scene):
    """按配音时间轴推进的场景。

    build/timing.json 由流水线生成，记录每镜每句旁白的起止时间。
    场景里用 self.at(i) 等到第 i 句开始，self.finish() 补齐到配音总长。
    """

    key: str | None = None

    def setup(self):
        key = self.key or type(self).__name__
        path = Path(os.environ.get("NARRATION_TIMING", Path.cwd() / "build" / "timing.json"))
        self.cues, self.total = [], None
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for s in data["shots"]:
                if s["key"] == key:
                    self.cues = s["cues"]
                    self.total = s["duration"]
        if self.total is None:  # 没有时间轴时（单独调试画面）按每句 3 秒估算
            self.cues = [{"start": 0.3 + 3 * i, "end": 3.0 + 3 * i, "text": ""} for i in range(10)]
            self.total = 30.0

    @property
    def now(self) -> float:
        return self.renderer.time

    def cue(self, i: int, offset: float = 0.0) -> float:
        return self.cues[min(i, len(self.cues) - 1)]["start"] + offset

    def cue_end(self, i: int) -> float:
        return self.cues[min(i, len(self.cues) - 1)]["end"]

    def wait_until(self, t: float):
        dt = t - self.now
        if dt > 1e-3:
            self.wait(dt)
        elif dt < -0.35:
            print(f"[timing] {type(self).__name__}: 动画比旁白慢了 {-dt:.2f}s（t={self.now:.2f}）", file=sys.stderr)

    def at(self, i: int, offset: float = 0.0):
        self.wait_until(self.cue(i, offset))

    def left(self, i: int, offset: float = 0.0) -> float:
        """距离第 i 句开始还有多少秒（至少 0.3 秒），用来给动画分配时长。"""
        return max(self.cue(i, offset) - self.now, 0.3)

    def finish(self):
        self.wait_until(self.total)


# ---------------------------------------------------------------- 物理模型（缓存）
@lru_cache(maxsize=1)
def model() -> WindingSection:
    return WindingSection()


@lru_cache(maxsize=4)
def field_lines(n_lines=9):
    return model().field_lines(n_lines=n_lines, lo=0.06, hi=0.94)


# ---------------------------------------------------------------- 纵剖面
class Section(VGroup):
    """心式变压器一个芯柱的纵剖面：铁心框 + 左右各一组内（低压）/外（高压）绕组。

    物理坐标 (r, z) -> 画面坐标： x = cx + side * s * r， y = cy + s * z。
    """

    def __init__(self, center=ORIGIN, scale=0.78, discs: int = 0, frame=True, **kw):
        super().__init__(**kw)
        self.m = m = model()
        self.s = scale
        self.c = np.array(center, float)
        yk = 0.5  # 铁轭厚度（物理单位）
        self.iron = VGroup()
        # 中间芯柱 + 上下铁轭 + 两侧旁柱
        self.iron.add(self.rect(-m.core_r, m.core_r, -m.yoke_z, m.yoke_z))
        self.iron.add(self.rect(-m.outer_r - yk, m.outer_r + yk, m.yoke_z, m.yoke_z + yk))
        self.iron.add(self.rect(-m.outer_r - yk, m.outer_r + yk, -m.yoke_z - yk, -m.yoke_z))
        if frame:
            self.iron.add(self.rect(m.outer_r, m.outer_r + yk, -m.yoke_z, m.yoke_z))
            self.iron.add(self.rect(-m.outer_r - yk, -m.outer_r, -m.yoke_z, m.yoke_z))
        for r in self.iron:
            r.set_fill(CORE, 1).set_stroke(CORE_EDGE, 1.5)
        self.core = self.iron[0]
        h = m.half_h
        self.lv = VGroup(self.winding(-m.lv[1], -m.lv[0], LV, discs), self.winding(*m.lv, LV, discs))
        self.hv = VGroup(self.winding(-m.hv[1], -m.hv[0], HV, discs), self.winding(*m.hv, HV, discs))
        self.add(self.iron, self.lv, self.hv)

    # 坐标变换
    def p(self, r, z, side=1):
        return self.c + np.array([side * self.s * r, self.s * z, 0.0])

    def rect(self, x0, x1, z0, z1):
        a, b = self.p(x0, z0), self.p(x1, z1)
        return Rectangle(width=abs(b[0] - a[0]), height=abs(b[1] - a[1])).move_to((a + b) / 2)

    def winding(self, x0, x1, color, discs):
        h = self.m.half_h
        if not discs:
            return self.rect(x0, x1, -h, h).set_fill(color, 0.85).set_stroke(color, 2)
        g = VGroup()
        edges = np.linspace(-h, h, discs + 1)
        gap = 0.32 * (2 * h / discs)
        for a, b in zip(edges[:-1], edges[1:]):
            g.add(self.rect(x0, x1, a + gap / 2, b - gap / 2).set_fill(color, 0.9).set_stroke(color, 1))
        return g

    def spacers(self, which="both", discs=12):
        """线饼之间的垫块。返回 VGroup，每个元素按从下到上排列。"""
        h = self.m.half_h
        edges = np.linspace(-h, h, discs + 1)[1:-1]
        gap = 0.32 * (2 * h / discs)
        out = VGroup()
        for (r0, r1) in ([self.m.lv, self.m.hv] if which == "both" else [getattr(self.m, which)]):
            for side in (-1, 1):
                col = VGroup()
                for z in edges:
                    w = (r1 - r0) * 0.28
                    for rc in (r0 + w * 0.8, r1 - w * 0.8):
                        a = self.p(rc - w / 2, z - gap / 2, side)
                        b = self.p(rc + w / 2, z + gap / 2, side)
                        col.add(Rectangle(width=abs(b[0] - a[0]), height=abs(b[1] - a[1]))
                                .move_to((a + b) / 2).set_fill(SPACER, 1).set_stroke(width=0))
                out.add(col)
        return out

    def current_marks(self, n=5):
        """电流方向符号：⊙ 流出纸面，⊗ 流入纸面。

        画面 x 向右、z 向上，出纸面方向为 x × z = -y。内绕组电流 +phi 在右侧剖面指向 +y，
        即流入纸面：右侧内绕组 ⊗、外绕组 ⊙，左侧相反。这样同屏的 B 箭头和力箭头满足 F = I L × B。
        """
        g = VGroup()
        h = self.m.half_h
        zs = np.linspace(-h * 0.8, h * 0.8, n)
        for (r0, r1), sign in ((self.m.lv, 1), (self.m.hv, -1)):
            for side in (-1, 1):
                for z in zs:
                    out_of_page = (sign * side) < 0
                    g.add(current_symbol(self.p((r0 + r1) / 2, z, side), out_of_page, 0.13))
        return g

    def field(self, n_lines=9, color=FIELD, width=2.6):
        g = VGroup()
        for line in field_lines(n_lines):
            pts = line[:: max(1, len(line) // 120)]
            for side in (-1, 1):
                v = VMobject().set_points_smoothly([self.p(r, z, side) for r, z in pts])
                v.set_stroke(color, width, opacity=0.95)
                g.add(v)
        return g

    def field_arrows(self, color=FIELD, z=0.0):
        """在缝隙中部标出磁场方向（某一瞬间）。"""
        m = self.m
        g = VGroup()
        rg = (m.lv[1] + m.hv[0]) / 2
        _, bz = m.B(rg, z)
        d = np.sign(float(np.ravel(bz)[0]))
        for side in (-1, 1):
            c = self.p(rg, z, side)
            g.add(Arrow(c - d * 0.35 * UP, c + d * 0.35 * UP, buff=0, color=color, stroke_width=5,
                        max_tip_length_to_length_ratio=0.45))
        return g

    def radial_forces(self, which, zs=None, length=0.75, color=FORCE):
        m = self.m
        r0, r1 = getattr(m, which)
        zs = np.linspace(-1.8, 1.8, 5) if zs is None else zs
        rc = (r0 + r1) / 2
        g = VGroup()
        for side in (-1, 1):
            for z in zs:
                fr, _ = m.force(rc, z)
                d = np.sign(float(np.ravel(fr)[0]))  # +1 背离铁心，-1 指向铁心
                start = self.p(rc, z, side)
                g.add(Arrow(start, start + side * d * length * RIGHT, buff=0, color=color,
                            stroke_width=6, max_tip_length_to_length_ratio=0.35))
        return g

    def axial_forces(self, which, discs=12, max_len=0.9, color=FORCE, min_frac=0.12):
        """每个线饼一支轴向力箭头，长度正比于计算得到的轴向力。"""
        m = self.m
        r0, r1 = getattr(m, which)
        zc, fz = m.disc_axial_forces(which, discs)
        fmax = np.abs(fz).max()
        g = VGroup()
        for side in (-1, 1):
            for z, f in zip(zc, fz):
                if abs(f) < min_frac * fmax or np.sign(f) != -np.sign(z):
                    continue  # 只画明显的、指向中间的分量
                L = max_len * abs(f) / fmax
                start = self.p((r0 + r1) / 2, z, side)
                g.add(Arrow(start, start + np.sign(f) * L * UP, buff=0, color=color, stroke_width=6,
                            max_tip_length_to_length_ratio=0.4))
        return g

    def label(self, text, target, direction, color=TEXT, size=26, buff=0.9):
        t = T(text, size, color=color)
        t.next_to(target, direction, buff=buff)
        ln = Line(t.get_edge_center(-direction), target.get_center() if hasattr(target, "get_center") else target,
                  color=color, stroke_width=2, buff=0.08)
        return VGroup(t, ln)


def current_symbol(pos, out_of_page: bool, r=0.13, color=BG):
    c = Circle(radius=r, color=color, stroke_width=3).move_to(pos)
    if out_of_page:
        mark = Dot(pos, radius=r * 0.3, color=color)
    else:
        mark = VGroup(Line(pos + r * 0.65 * (UP + LEFT), pos + r * 0.65 * (DOWN + RIGHT), color=color, stroke_width=3),
                      Line(pos + r * 0.65 * (UP + RIGHT), pos + r * 0.65 * (DOWN + LEFT), color=color, stroke_width=3))
    return VGroup(c, mark)


# ---------------------------------------------------------------- 俯视图
def ring(center, r_in, r_out, color, n=180, dent=None, opacity=0.9):
    """圆环。dent(theta) 给出径向位移（正为向外），用来画屈曲/扩张。"""
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    d = dent(th) if dent else np.zeros_like(th)
    c = np.array(center, float)
    outer = [c + (r_out + di) * np.array([np.cos(t), np.sin(t), 0]) for t, di in zip(th, d)]
    inner = [c + (r_in + di) * np.array([np.cos(t), np.sin(t), 0]) for t, di in zip(th[::-1], d[::-1])]
    v = VMobject()
    v.set_points_as_corners(outer + [outer[0]])
    v.start_new_path(inner[0])
    v.add_points_as_corners(inner[1:] + [inner[0]])
    v.set_fill(color, opacity).set_stroke(color, 1.5)
    return v


def buckle_shape(amp, n=6):
    """内绕组屈曲：在撑条之间向内凹进去 n 个波。"""
    return lambda th: -amp * np.maximum(0, np.cos(n * th)) ** 2


class TopView(VGroup):
    """俯视图：铁心圆 + 内外绕组圆环。"""

    def __init__(self, center=ORIGIN, scale=0.6, buckle=0.0, expand=0.0, **kw):
        super().__init__(**kw)
        m = model()
        s = scale
        self.core = Circle(radius=m.core_r * s, color=CORE_EDGE, stroke_width=2).set_fill(CORE, 1).move_to(center)
        self.lv = ring(center, m.lv[0] * s, m.lv[1] * s, LV, dent=buckle_shape(buckle * s) if buckle else None)
        self.hv = ring(center, m.hv[0] * s, m.hv[1] * s, HV, dent=(lambda th: expand * s + 0 * th) if expand else None)
        self.add(self.core, self.lv, self.hv)


def lightning(center=ORIGIN, h=1.4, color=ACCENT):
    pts = np.array([[0.15, 0.5], [-0.12, 0.05], [0.08, 0.05], [-0.15, -0.5], [0.22, -0.02], [0.02, -0.02], [0.25, 0.5]])
    v = VMobject().set_points_as_corners([np.array([x * h, y * h, 0]) for x, y in pts] + [np.array([0.15 * h, 0.5 * h, 0])])
    return v.set_fill(color, 1).set_stroke(color, 2).move_to(center)
