"""第 1 期分镜：变压器短路时，绕组为什么会变形？

每个类对应 script.md 里的一个 "## 类名"。self.at(i) 表示“等到第 i 句旁白开始”。
画面全部是示意图；磁力线和力的方向来自 pipeline/physics.py 的示意模型计算。
画面下方 y < -3 的区域留给字幕。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from manim import *  # noqa: F401,F403

from pipeline.narrated import (
    ACCENT, BG, DIM, FIELD, FORCE, HV, LV, SPACER, TEXT, NarratedScene, Section, T, TopView,
    buckle_shape, corner_tag, current_symbol, lightning, model, ring, tag,
)

TITLE = "变压器短路时，绕组为什么会变形？"
SEC_C = LEFT * 3.0 + UP * 0.45   # 剖面图位置
PANEL_X = 3.6                     # 右侧文字区中心


def section_with_field(center=SEC_C, discs=0, field_opacity=0.35, scale=0.78):
    sec = Section(center=center, scale=scale, discs=discs)
    fl = sec.field(width=2.2).set_stroke(opacity=field_opacity)
    return sec, fl


def vertical_text(text, size=28, color=TEXT):
    return VGroup(*[T(ch, size, color=color, bold=True) for ch in text]).arrange(DOWN, buff=0.06)


def zoom_inset(sec, p0, center, radius=1.05, zoom=3.0):
    """放大镜：把剖面上 p0=(r, z) 附近放大 zoom 倍画在 center 处，并分解该点的 B。"""
    m = model()
    k = sec.s * zoom
    r0, z0 = p0
    C = np.array(center, float)

    def mp(r, z):
        return C + np.array([k * (r - r0), k * (z - z0), 0.0])

    disk = Circle(radius=radius, color=TEXT, stroke_width=3).set_fill(BG, 1).move_to(C)
    content = VGroup()
    lv_rect = Polygon(mp(m.lv[0], -m.half_h), mp(m.lv[1], -m.half_h), mp(m.lv[1], m.half_h), mp(m.lv[0], m.half_h))
    content.add(Intersection(lv_rect, Circle(radius=radius * 0.985).move_to(C), color=LV, fill_opacity=0.85,
                             stroke_width=0))
    for line in m.field_lines(n_lines=16, lo=0.03, hi=0.97):
        pts = [mp(r, z) for r, z in line]
        run = []
        for q in pts + [None]:
            if q is not None and np.linalg.norm(q - C) < radius * 0.97:
                run.append(q)
                continue
            if len(run) >= 4:
                content.add(VMobject().set_points_smoothly(run).set_stroke(FIELD, 2.5, opacity=0.9))
            run = []
    br, bz = m.B(r0, z0)
    br, bz = float(np.ravel(br)[0]), float(np.ravel(bz)[0])
    n = np.hypot(br, bz)
    L = 1.0
    tipB = C + L * np.array([br / n, bz / n, 0])
    tipR = C + L * np.array([br / n, 0, 0])
    vb = Arrow(C, tipB, buff=0, color=TEXT, stroke_width=7, max_tip_length_to_length_ratio=0.3)
    lb = T("B", 28, color=TEXT, bold=True).next_to(tipB, LEFT, buff=0.1)
    lb.add_to_back(BackgroundRectangle(lb, color=BG, fill_opacity=0.8, buff=0.04))
    vr = Arrow(C, tipR, buff=0, color=FORCE, stroke_width=8, max_tip_length_to_length_ratio=0.35)
    vz = DashedLine(tipR, tipB, color=TEXT, stroke_width=3)
    lr = T("径向分量", 22, color=FORCE, bold=True).next_to(vr, UP, buff=0.12)
    lr.add_to_back(BackgroundRectangle(lr, color=BG, fill_opacity=0.8, buff=0.05))
    cap = T("放大", 20, color=DIM).next_to(disk, UP, buff=0.05)
    spot = Circle(radius=0.3, color=TEXT, stroke_width=3).move_to(sec.p(r0, z0))
    link = VGroup(spot, Line(spot.get_right(), disk.get_left(), color=TEXT, stroke_width=2))
    return VGroup(VGroup(disk, cap), content, vb, lb, vr, vz, lr), link


# ============================================================ S01 开场钩子
class S01_Hook(NarratedScene):
    def construct(self):
        m = model()
        sec = Section(center=LEFT * 3.9 + DOWN * 0.15, scale=0.58)
        top_r = sec.p(m.hv[1], m.half_h)
        bot_r = sec.p(m.hv[1], -m.half_h)
        term_x = sec.p(m.outer_r + 0.5, 0)[0] + 0.9
        a1, a2 = np.array([term_x, top_r[1] - 0.2, 0]), np.array([term_x, bot_r[1] + 0.2, 0])
        leads = VGroup(Line(top_r + LEFT * 0.1, a1, color=TEXT, stroke_width=4),
                       Line(bot_r + LEFT * 0.1, a2, color=TEXT, stroke_width=4),
                       Dot(a1, 0.09, color=TEXT), Dot(a2, 0.09, color=TEXT))
        title = T(TITLE, 46, bold=True).to_edge(UP, buff=0.4)
        self.add(sec, leads, title)

        # “一台变压器，出口突然短路”
        short = Line(a1, a2, color=FORCE, stroke_width=8)
        bolt = lightning(short.get_center() + RIGHT * 0.55, h=1.2)
        self.wait_until(self.cue(0, 1.2))
        self.play(Create(short), run_time=0.25)
        self.play(FadeIn(bolt, scale=1.6), sec.lv.animate.set_fill(FORCE, 0.9),
                  sec.hv.animate.set_fill(FORCE, 0.9), Flash(short.get_center(), color=ACCENT, flash_radius=0.9),
                  run_time=0.35)
        word = tag("出口短路！", FORCE, 34).next_to(bolt, DOWN, buff=0.3)
        self.play(Wiggle(VGroup(sec, leads, short), scale_value=1.02, rotation_angle=0.015 * TAU),
                  FadeIn(word, scale=1.3), run_time=0.6)

        # “几十毫秒内，绕组就可能被挤变形”——俯视图：内绕组被压得向内凹
        self.at(1)
        top_c = RIGHT * 3.9 + DOWN * 0.1
        amp = ValueTracker(0.0)
        tv = always_redraw(lambda: TopView(top_c, scale=0.85, buckle=amp.get_value(),
                                           expand=amp.get_value() * 0.4))
        cap = T("俯视", 24, color=DIM).next_to(top_c + UP * 2.25, UP, buff=0.05)
        self.play(FadeIn(tv), FadeIn(cap), run_time=0.5)
        clock = tag("几十毫秒", ACCENT, 30).next_to(top_c + DOWN * 2.3, DOWN, buff=0.05)
        self.play(FadeIn(clock), run_time=0.3)
        self.play(amp.animate.set_value(0.2), run_time=1.6, rate_func=rush_into)

        # “这股力，到底从哪来？”
        self.at(2)
        q = T("这股力，从哪来？", 60, color=ACCENT, bold=True).move_to(DOWN * 0.1)
        bg = BackgroundRectangle(q, color=BG, fill_opacity=0.88, buff=0.35)
        self.play(FadeIn(bg), Write(q), run_time=0.9)
        self.finish()


# ============================================================ S02 力和电流平方
class S02_Squared(NarratedScene):
    def construct(self):
        self.add(corner_tag())
        # “先说结论：力来自短路电流和漏磁场”
        c1 = tag("短路电流", LV, 34)
        c2 = tag("漏磁场", FIELD, 34)
        c3 = tag("电磁力", FORCE, 34)
        eq = VGroup(c1, T("×", 44), c2, T("→", 44), c3).arrange(RIGHT, buff=0.35).move_to(UP * 2.55)
        head = T("先说结论", 30, color=DIM).next_to(eq, UP, buff=0.25)
        self.play(FadeIn(head), LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in eq], lag_ratio=0.25),
                  run_time=1.8)

        # “短路电流，可达额定电流的十几到几十倍”——柱状图
        self.at(1)
        base = DOWN * 2.2
        x1, x2 = LEFT * 4.6, LEFT * 2.4
        axis = Line(base + LEFT * 5.6, base + LEFT * 1.2, color=DIM, stroke_width=2)
        b1 = Rectangle(width=1.1, height=0.18).set_fill(LV, 1).set_stroke(width=0)
        b1.move_to(x1 + base, aligned_edge=DOWN)
        hgt = ValueTracker(0.18)
        b2 = always_redraw(lambda: Rectangle(width=1.1, height=hgt.get_value()).set_fill(FORCE, 1)
                           .set_stroke(width=0).move_to(x2 + base, aligned_edge=DOWN))
        l1 = T("额定电流", 24, color=DIM).next_to(x1 + base, DOWN, buff=0.15)
        l2 = T("短路电流", 24, color=DIM).next_to(x2 + base, DOWN, buff=0.15)
        self.play(Create(axis), FadeIn(b1), FadeIn(l1), FadeIn(b2), FadeIn(l2), run_time=0.6)
        self.play(hgt.animate.set_value(3.5), run_time=1.4, rate_func=rush_from)
        times = T("十几～几十倍", 30, color=FORCE, bold=True).next_to(x2 + base + UP * 3.5, UP, buff=0.15)
        self.play(FadeIn(times, shift=UP * 0.2), run_time=0.4)

        # “而电磁力，和电流的平方成正比”
        self.at(2)
        law = T("F ∝ I²", 64, color=ACCENT, bold=True).move_to(RIGHT * 3.3 + UP * 1.0)
        self.play(Write(law), run_time=1.0)

        # “电流涨十倍，力就涨一百倍”——10×10 方格
        self.at(3)
        small = Square(0.16).set_fill(FORCE, 1).set_stroke(width=0)
        grid = VGroup(*[Square(0.16).set_fill(FORCE, 1).set_stroke(BG, 1) for _ in range(100)])
        grid.arrange_in_grid(10, 10, buff=0.02)
        left_g = VGroup(small, T("I ×1 → F ×1", 26, color=DIM)).arrange(DOWN, buff=0.25)
        right_g = VGroup(grid, T("I ×10 → F ×100", 26, color=TEXT)).arrange(DOWN, buff=0.25)
        demo = VGroup(left_g, right_g).arrange(RIGHT, buff=0.9, aligned_edge=DOWN).move_to(RIGHT * 3.3 + DOWN * 1.2)
        self.play(FadeIn(left_g), run_time=0.4)
        self.play(LaggedStart(*[FadeIn(s, scale=0.3) for s in grid], lag_ratio=0.012, run_time=1.4),
                  FadeIn(right_g[1]))

        # “所以短路时，力可达平时的几百倍”
        self.at(4)
        big = tag("力：可达平时的几百倍", FORCE, 40).move_to(UP * 1.0 + RIGHT * 3.3)
        self.play(ReplacementTransform(law, big), run_time=0.6)
        self.play(Indicate(big, color=ACCENT, scale_factor=1.12), run_time=0.8)
        self.finish()


# ============================================================ S03 漏磁场
class S03_LeakageField(NarratedScene):
    def construct(self):
        self.add(corner_tag())
        m = model()
        # “把变压器竖着切开”——俯视图 → 剖面
        tv = TopView(SEC_C, scale=0.78)
        cut = DashedLine(SEC_C + LEFT * 3.4, SEC_C + RIGHT * 3.4, color=ACCENT, stroke_width=4)
        lab_top = T("俯视", 24, color=DIM).next_to(tv, UP, buff=0.1)
        self.add(tv, lab_top)
        self.play(Create(cut), run_time=0.5)
        sec = Section(center=SEC_C, scale=0.78)
        lab_sec = T("纵剖面", 24, color=DIM).next_to(sec, UP, buff=0.08)
        self.play(FadeOut(cut), ReplacementTransform(tv.core, sec.iron), ReplacementTransform(tv.lv, sec.lv),
                  ReplacementTransform(tv.hv, sec.hv), ReplacementTransform(lab_top, lab_sec), run_time=0.8)

        # “中间是铁心，里圈是低压绕组，外圈是高压绕组”
        self.at(1)
        lab_core = T("铁心", 26).move_to(sec.p(0, 0.0))
        lab_lv = VGroup(T("低压绕组", 26, color=LV), T("（内）", 22, color=LV)).arrange(DOWN, buff=0.06)
        lab_hv = VGroup(T("高压绕组", 26, color=HV), T("（外）", 22, color=HV)).arrange(DOWN, buff=0.06)
        lab_lv.move_to(RIGHT * 2.0 + UP * 1.9)
        lab_hv.move_to(RIGHT * 2.0 + UP * 0.5)
        ln_lv = Line(lab_lv.get_left(), sec.p((m.lv[0] + m.lv[1]) / 2, 1.9), color=LV, stroke_width=2, buff=0.1)
        ln_hv = Line(lab_hv.get_left(), sec.p((m.hv[0] + m.hv[1]) / 2, 0.1), color=HV, stroke_width=2, buff=0.1)
        self.play(FadeIn(lab_core), Indicate(sec.core, color=DIM, scale_factor=1.02), run_time=0.6)
        self.wait_until(self.cue(1, 1.2))
        self.play(FadeIn(lab_lv), Create(ln_lv), Indicate(sec.lv, color=LV, scale_factor=1.03), run_time=0.8)
        self.wait_until(self.cue(1, 2.6))
        self.play(FadeIn(lab_hv), Create(ln_hv), Indicate(sec.hv, color=HV, scale_factor=1.03), run_time=0.8)

        # “短路时，两个绕组的电流方向相反，”
        self.at(2)
        marks = sec.current_marks()
        legend = VGroup(
            VGroup(current_symbol(ORIGIN, True, 0.13, TEXT), T("电流流出纸面", 22, color=DIM)).arrange(RIGHT, buff=0.15),
            VGroup(current_symbol(ORIGIN, False, 0.13, TEXT), T("电流流入纸面", 22, color=DIM)).arrange(RIGHT, buff=0.15),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15).move_to(RIGHT * 5.3 + UP * 2.9)
        self.play(LaggedStart(*[FadeIn(x, scale=0.5) for x in marks], lag_ratio=0.03), FadeIn(legend), run_time=1.4)
        opp = tag("电流方向相反", ACCENT, 28).move_to(RIGHT * 4.6 + DOWN * 0.6)
        self.play(FadeIn(opp, shift=UP * 0.2), run_time=0.4)

        # “它们之间的缝隙里，就有很强的漏磁场。”
        self.at(3)
        fl = sec.field()
        lab_f = tag("漏磁场", FIELD, 30).move_to(RIGHT * 4.6 + DOWN * 0.6)
        self.play(FadeOut(opp), LaggedStart(*[Create(l) for l in fl], lag_ratio=0.04), run_time=2.0)
        self.play(FadeIn(lab_f), run_time=0.4)

        # “绕组中部，磁力线基本沿轴向，上下走；”
        self.at(4)
        rg = (m.lv[1] + m.hv[0]) / 2
        boxes = VGroup(*[Rectangle(width=0.62 * 0.78, height=2.2 * 0.78, color=ACCENT, stroke_width=4)
                         .move_to(sec.p(rg, 0, s)) for s in (-1, 1)])
        arrows = sec.field_arrows(color=ACCENT)
        ax = tag("中部：沿轴向（上下）", ACCENT, 28).move_to(RIGHT * 4.6 + DOWN * 1.35)
        self.play(Create(boxes), GrowArrow(arrows[0]), GrowArrow(arrows[1]), FadeIn(ax), run_time=1.0)

        # “到了两端，磁力线弯曲，出现径向分量。”——放大内绕组顶端，把 B 分解
        self.at(5)
        ends = VGroup(*[Circle(radius=0.55, color=FORCE, stroke_width=4).move_to(sec.p(rg, z, s))
                        for s in (-1, 1) for z in (m.half_h, -m.half_h)])
        rad = tag("两端：弯曲，出现径向分量", FORCE, 28).move_to(RIGHT * 4.6 + DOWN * 2.1)
        self.play(FadeOut(boxes), FadeOut(arrows), Create(ends), FadeIn(rad),
                  FadeOut(VGroup(lab_lv, ln_lv, lab_hv, ln_hv, legend)), run_time=0.8)
        inset, link = zoom_inset(sec, (1.4, m.half_h), RIGHT * 3.6 + UP * 1.55, radius=1.2, zoom=3.2)
        self.play(Create(link), FadeIn(inset[0]), run_time=0.4)
        self.play(FadeIn(inset[1]), GrowArrow(inset[2]), FadeIn(inset[3]), run_time=0.5)
        self.play(GrowArrow(inset[4]), Create(inset[5]), FadeIn(inset[6]), run_time=0.6)
        self.finish()


# ============================================================ S04 径向力
class S04_RadialForce(NarratedScene):
    def construct(self):
        self.add(corner_tag())
        sec, fl = section_with_field()
        marks = sec.current_marks(n=3)
        self.add(sec, fl, marks)

        # “电流在磁场里会受力，这就是洛伦兹力。”
        f1 = VGroup(T("洛伦兹力", 34, bold=True), T("F = I × B", 50, color=ACCENT, bold=True)).arrange(RIGHT, buff=0.4)
        f3 = T("电流在磁场里受力", 24, color=DIM)
        formula = VGroup(f1, f3).arrange(DOWN, buff=0.18).move_to(RIGHT * PANEL_X + UP * 2.85)
        self.play(FadeIn(f1[0]), Write(f1[1]), run_time=1.2)
        self.play(FadeIn(f3), run_time=0.4)

        # “轴向的磁场，产生径向的力：”
        self.at(1)
        ar = sec.field_arrows(color=FIELD)
        rule = tag("轴向磁场 → 径向力", FORCE, 28).move_to(RIGHT * PANEL_X + UP * 1.75)
        self.play(GrowArrow(ar[0]), GrowArrow(ar[1]), FadeIn(rule), run_time=0.8)
        f_hv = sec.radial_forces("hv")
        f_lv = sec.radial_forces("lv")
        self.play(LaggedStart(*[GrowArrow(a) for a in [*f_hv, *f_lv]], lag_ratio=0.05), run_time=1.2)

        # 右侧俯视小图
        tc = RIGHT * 2.45 + DOWN * 0.85
        amp = ValueTracker(0.0)
        exp = ValueTracker(0.0)
        tv = always_redraw(lambda: TopView(tc, scale=0.40, buckle=amp.get_value(), expand=exp.get_value()))
        cap = T("俯视", 20, color=DIM).next_to(tc + UP * 1.55, UP, buff=0.02)
        lx = 3.95  # 标签左边缘

        # “外绕组被往外撑，受拉；”
        self.at(2)
        self.play(FadeIn(tv), FadeIn(cap), run_time=0.4)
        out_arrows = VGroup(*[Arrow(tc + 1.12 * np.array([np.cos(a), np.sin(a), 0]),
                                    tc + 1.5 * np.array([np.cos(a), np.sin(a), 0]), buff=0, color=HV,
                                    stroke_width=5, max_tip_length_to_length_ratio=0.45)
                              for a in np.linspace(0, TAU, 8, endpoint=False)])
        hv_lab = VGroup(T("外绕组", 26, color=HV, bold=True), T("往外撑，受拉", 24, color=HV))
        hv_lab.arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        hv_lab.move_to([lx + hv_lab.width / 2, 0.3, 0])
        self.play(Indicate(f_hv, color=HV), exp.animate.set_value(0.12), FadeIn(out_arrows), FadeIn(hv_lab),
                  run_time=1.2)

        # “内绕组被往里压，压狠了会向内凹陷，这叫屈曲。”
        self.at(3)
        lv_lab = VGroup(T("内绕组", 26, color=LV, bold=True), T("往里压", 24, color=LV))
        lv_lab.arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        lv_lab.move_to([lx + lv_lab.width / 2, -0.85, 0])
        self.play(Indicate(f_lv, color=LV), FadeIn(lv_lab), run_time=0.9)
        self.wait_until(self.cue(3, 1.6))
        self.play(amp.animate.set_value(0.22), run_time=1.3, rate_func=rush_into)
        bk = tag("屈曲：向内凹陷", FORCE, 26)
        bk.move_to([lx + bk.width / 2, -1.85, 0])
        self.play(FadeIn(bk, scale=1.2), run_time=0.4)
        self.finish()


# ============================================================ S05 轴向力
class S05_AxialForce(NarratedScene):
    def construct(self):
        self.add(corner_tag())
        discs = 12
        sec, fl = section_with_field(discs=discs, field_opacity=0.3)
        spacers = sec.spacers(discs=discs)
        self.add(sec, spacers, fl)
        m = model()
        lx = 2.7  # 右侧文字左边缘

        def place(mob, y):
            return mob.move_to([lx + mob.width / 2, y, 0])

        # “再看两端：径向磁场，产生轴向的力，”
        rg = (m.lv[1] + m.hv[0]) / 2
        ends = VGroup(*[Circle(radius=0.6, color=FIELD, stroke_width=4).move_to(sec.p(rg, z, s))
                        for s in (-1, 1) for z in (m.half_h, -m.half_h)])
        self.play(Create(ends), fl.animate.set_stroke(opacity=0.75), run_time=0.8)
        rule = place(tag("端部径向磁场 → 轴向力", FORCE, 28), 2.75)
        self.play(FadeIn(rule), run_time=0.4)
        fa = VGroup(sec.axial_forces("lv", discs, max_len=1.0, color=ACCENT),
                    sec.axial_forces("hv", discs, max_len=1.0, color=ACCENT))
        self.wait_until(self.cue(0, 1.6))
        self.play(LaggedStart(*[GrowArrow(a) for a in [*fa[0], *fa[1]]], lag_ratio=0.03),
                  fl.animate.set_stroke(opacity=0.3), FadeOut(ends), run_time=1.2)

        # “把绕组沿着高度方向，往中间压。”
        self.at(1)
        xq = sec.p(m.outer_r + 0.5, 0)[0] + 0.55
        word = vertical_text("往中间压", 28, FORCE).move_to([xq, SEC_C[1], 0])
        squeeze = VGroup(
            Arrow([xq, sec.p(0, m.half_h + 0.4)[1], 0], word.get_top() + UP * 0.1, buff=0, color=FORCE,
                  stroke_width=10, max_tip_length_to_length_ratio=0.25),
            Arrow([xq, sec.p(0, -m.half_h - 0.4)[1], 0], word.get_bottom() + DOWN * 0.1, buff=0, color=FORCE,
                  stroke_width=10, max_tip_length_to_length_ratio=0.25),
        )
        self.play(GrowArrow(squeeze[0]), GrowArrow(squeeze[1]), FadeIn(word), run_time=0.9)
        self.play(sec.lv.animate.stretch(0.97, 1), sec.hv.animate.stretch(0.97, 1),
                  spacers.animate.stretch(0.97, 1), fa.animate.stretch(0.97, 1),
                  run_time=0.8, rate_func=there_and_back)

        # “端部的线饼受力最大，容易歪倒；”
        self.at(2)
        end_discs = VGroup(*[w[i] for grp in (sec.lv, sec.hv) for w in grp for i in (0, discs - 1)])
        d_lab = place(VGroup(T("端部线饼", 28, color=FORCE, bold=True), T("受力最大，容易歪倒", 24))
                      .arrange(DOWN, aligned_edge=LEFT, buff=0.08), 1.75)
        self.play(end_discs.animate.set_fill(FORCE, 1), FadeIn(d_lab), run_time=0.6)
        tilts = []
        for grp in (sec.lv, sec.hv):
            for side_i, w in enumerate(grp):
                side = -1 if side_i == 0 else 1
                tilts.append(Rotate(w[discs - 1], angle=-side * 0.12, about_point=w[discs - 1].get_center()))
                tilts.append(Rotate(w[0], angle=side * 0.12, about_point=w[0].get_center()))
        self.play(*tilts, run_time=0.8)

        # “力一层层往中间传，把线饼间的垫块越压越紧。”
        self.at(3)
        # 第 k 个垫块（第 k、k+1 个线饼之间）承受它下方所有线饼轴向力之和 → 越往中间越大
        zc, fz = m.disc_axial_forces("hv", discs)
        load = np.clip(np.cumsum(fz)[:-1] / np.cumsum(fz)[:-1].max(), 0, 1)
        anims = []
        for col in spacers:
            for k in range(discs - 1):
                for j in range(2):
                    sp = col[2 * k + j]
                    c = interpolate_color(ManimColor(SPACER), ManimColor(FORCE), load[k])
                    anims.append(sp.animate.set_fill(c, 1).stretch(1 - 0.45 * load[k], 1))
        # 垫块压力分布小图（横条长度 ∝ 累积压力）
        h = m.half_h
        z_sp = np.linspace(-h, h, discs + 1)[1:-1]
        bx = xq - 0.25
        bars = VGroup(*[Rectangle(width=1.5 * v + 0.02, height=0.12).set_fill(
            interpolate_color(ManimColor(SPACER), ManimColor(FORCE), v), 1).set_stroke(width=0)
            .move_to([bx + 0.75 * v + 0.01, sec.p(0, z)[1], 0]) for z, v in zip(z_sp, load)])
        bars_axis = Line([bx, sec.p(0, -h)[1], 0], [bx, sec.p(0, h)[1], 0], color=DIM, stroke_width=2)
        s_lab = place(VGroup(T("垫块", 28, color=SPACER, bold=True), T("越往中间，累积压力越大", 24))
                      .arrange(DOWN, aligned_edge=LEFT, buff=0.08), 0.75)
        bars_cap = T("垫块压力（示意）", 20, color=DIM).next_to(bars_axis, DOWN, buff=0.12, aligned_edge=LEFT)
        self.play(LaggedStart(*anims, lag_ratio=0.004), FadeIn(s_lab), FadeOut(squeeze), FadeOut(word), run_time=1.6)
        self.play(Create(bars_axis), LaggedStart(*[GrowFromEdge(b, LEFT) for b in bars], lag_ratio=0.05),
                  FadeIn(bars_cap), run_time=1.0)
        self.finish()


# ============================================================ S06 力随时间变化
class S06_TimeWave(NarratedScene):
    def construct(self):
        self.add(corner_tag())
        w = 2 * np.pi * 50
        tau = 0.045
        T_END = 0.12

        def i_ac(t):
            return -np.cos(w * t)

        def i_dc(t):
            return np.exp(-t / tau)

        def i(t):
            return i_ac(t) + i_dc(t)

        ax_i = Axes(x_range=[0, T_END, 0.02], y_range=[-1.2, 2.1, 1], x_length=7.6, y_length=2.3,
                    axis_config={"color": DIM, "stroke_width": 2}, tips=False)
        ax_f = Axes(x_range=[0, T_END, 0.02], y_range=[0, 4.0, 1], x_length=7.6, y_length=2.2,
                    axis_config={"color": DIM, "stroke_width": 2}, tips=False)
        ax_i.move_to(LEFT * 2.3 + UP * 1.75)
        ax_f.move_to(LEFT * 2.3 + DOWN * 1.05)
        li = T("短路电流 i", 24, color=LV)
        lf = T("电磁力 F ∝ i²", 24, color=FORCE)
        li.next_to(ax_i.get_corner(UL), RIGHT, buff=0.15).shift(UP * 0.2)
        lf.next_to(ax_f.get_corner(UL), RIGHT, buff=0.15).shift(UP * 0.2)
        tl = T("时间 →（每格 20 毫秒 = 50 Hz 的一个周期）", 20, color=DIM).next_to(ax_f, DOWN, buff=0.12)
        rx = 1.95  # 右侧文字左边缘

        def place(mob, y):
            return mob.move_to([rx + mob.width / 2, y, 0])

        # “力还会随时间变化。”
        self.play(Create(ax_i), FadeIn(li), run_time=0.6)
        ci = ax_i.plot(i, x_range=[0, T_END, 0.0005], color=LV, stroke_width=4)
        self.play(Create(ci), run_time=1.0, rate_func=linear)

        # “短路电流里，有一个慢慢衰减的直流分量。”
        self.at(1)
        cdc = DashedVMobject(ax_i.plot(i_dc, x_range=[0, T_END, 0.001], color=ACCENT, stroke_width=4), num_dashes=40)
        ldc = place(tag("衰减的直流分量（虚线）", ACCENT, 24), 2.45)
        self.play(Create(cdc), FadeIn(ldc), run_time=1.0)
        lac = place(T("叠加在 50 Hz 交流上", 24, color=LV), 1.85)
        self.play(FadeIn(lac), run_time=0.4)

        # “力跟着电流的平方走：”
        self.at(2)
        self.play(Create(ax_f), FadeIn(lf), FadeIn(tl), run_time=0.5)
        cf = ax_f.plot(lambda t: i(t) ** 2, x_range=[0, T_END, 0.0005], color=FORCE, stroke_width=4)
        self.play(Create(cf), run_time=1.0, rate_func=linear)

        # “直流分量乘上五十赫兹的交流，给出五十赫兹的力；”
        # i² = 交流² + 2·直流·交流 + 直流²
        self.at(3)
        expand = place(T("i² = 交流² + 2·直流·交流 + 直流²", 22, color=TEXT), 0.95)
        c50 = ax_f.plot(lambda t: 2 * i_ac(t) * i_dc(t) + 2.0, x_range=[0, T_END, 0.0005],
                        color=ACCENT, stroke_width=2.5)
        l50 = place(VGroup(T("2·直流·交流", 24, color=ACCENT, bold=True), T("→ 50 Hz 成分，逐渐衰减", 24, color=ACCENT))
                    .arrange(DOWN, aligned_edge=LEFT, buff=0.06), 0.15)
        self.play(FadeIn(expand), run_time=0.5)
        self.play(cf.animate.set_stroke(opacity=0.3), Create(c50), FadeIn(l50), run_time=1.3)

        # “交流自己平方，给出一百赫兹的力。”
        self.at(4)
        c100 = ax_f.plot(lambda t: i_ac(t) ** 2 + 0.1, x_range=[0, T_END, 0.0005], color=HV, stroke_width=2.5)
        l100 = place(VGroup(T("交流²", 24, color=HV, bold=True), T("→ 100 Hz 成分", 24, color=HV))
                     .arrange(DOWN, aligned_edge=LEFT, buff=0.06), -0.95)
        note = T("（分量上下错开画，只看频率）", 18, color=DIM).next_to(ax_f, UP, buff=0.05).align_to(ax_f, RIGHT)
        self.play(Create(c100), FadeIn(l100), FadeIn(note), run_time=1.3)

        # “所以力方向不变，一下下猛敲绕组，前几个周期最狠。”
        self.at(5)
        self.play(FadeOut(c50), FadeOut(c100), FadeOut(note), cf.animate.set_stroke(opacity=1), run_time=0.5)
        pos = place(tag("F ≥ 0：方向不变", FORCE, 26), -1.95)
        self.play(FadeIn(pos), run_time=0.4)
        peaks = Rectangle(width=ax_f.c2p(0.045, 0)[0] - ax_f.c2p(0, 0)[0], height=2.0, color=ACCENT, stroke_width=4)
        peaks.move_to(ax_f.c2p(0.0225, 1.95))
        first = T("前几个周期最大", 24, color=ACCENT, bold=True).next_to(peaks, RIGHT, buff=0.15).align_to(peaks, UP)
        self.wait_until(self.cue(5, 1.4))
        self.play(Create(peaks), FadeIn(first), run_time=0.7)
        dots = VGroup(*[Dot(ax_f.c2p(t, i(t) ** 2), radius=0.08, color=ACCENT) for t in (0.01, 0.03, 0.05)])
        self.play(LaggedStart(*[Flash(d, color=ACCENT, flash_radius=0.3) for d in dots], lag_ratio=0.4), run_time=1.2)
        self.finish()


# ============================================================ S07 后果和国标
class S07_Consequence(NarratedScene):
    def construct(self):
        self.add(corner_tag())

        # “后果就是：绕组变形，垫块压缩，绝缘受损。”
        def card(title, icon):
            box = RoundedRectangle(corner_radius=0.2, width=3.4, height=2.6, stroke_color=DIM, stroke_width=2)
            box.set_fill("#16212E", 1)
            icon.move_to(box.get_center() + UP * 0.35)
            t = T(title, 28, bold=True).next_to(box.get_bottom(), UP, buff=0.3)
            return VGroup(box, icon, t)

        ic1 = ring(ORIGIN, 0.35, 0.55, LV, dent=buckle_shape(0.14))
        blk = VGroup(Rectangle(width=1.1, height=0.33).set_fill(SPACER, 1).set_stroke(width=0),
                     Arrow(UP * 0.85, UP * 0.2, buff=0, color=FORCE, stroke_width=6),
                     Arrow(DOWN * 0.85, DOWN * 0.2, buff=0, color=FORCE, stroke_width=6))
        ins = VGroup(Rectangle(width=1.5, height=0.5).set_fill(HV, 0.85).set_stroke(width=0),
                     lightning(ORIGIN, 0.8, FORCE))
        cards = VGroup(card("绕组变形", ic1), card("垫块压缩", blk), card("绝缘受损", ins))
        cards.arrange(RIGHT, buff=0.45).move_to(UP * 0.4)
        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.3) for c in cards], lag_ratio=0.35), run_time=2.2)

        # “国标 GB/T 1094.5 专门规定了：变压器承受短路的能力，”
        self.at(1)
        self.play(cards.animate.scale(0.5).to_edge(UP, buff=0.55), run_time=0.6)
        std = VGroup(T("GB/T 1094.5", 60, color=ACCENT, bold=True),
                     T("电力变压器  第 5 部分：承受短路的能力", 30)).arrange(DOWN, buff=0.2)
        std_box = SurroundingRectangle(std, color=ACCENT, buff=0.3, corner_radius=0.15)
        g = VGroup(std_box, std).move_to(UP * 0.85)
        self.play(Create(std_box), FadeIn(std, shift=UP * 0.2), run_time=1.0)

        # “要用短路试验，或者计算校核来证明。”
        self.at(2)
        b1 = tag("短路承受能力试验", HV, 28)
        b2 = tag("计算 + 设计校核", LV, 28)
        orr = T("或", 28, color=DIM)
        branch = VGroup(b1, orr, b2).arrange(RIGHT, buff=0.5).next_to(g, DOWN, buff=0.5)
        self.play(FadeIn(b1, shift=UP * 0.2), run_time=0.5)
        self.play(FadeIn(orr), FadeIn(b2, shift=UP * 0.2), run_time=0.6)

        # “试验前后比一比短路电抗，变化超限，说明绕组可能变形了。”
        self.at(3)
        self.play(FadeOut(branch), run_time=0.4)
        y0 = -1.3
        bar = Line([-3.0, y0, 0], [3.0, y0, 0], color=DIM, stroke_width=3)
        ok = Rectangle(width=1.6, height=0.22).set_fill("#3DDC97", 0.6).set_stroke(width=0).move_to([0, y0, 0])
        xk = T("短路电抗", 26, bold=True).next_to(bar, LEFT, buff=0.3)
        tri_b = Triangle().set_fill(TEXT, 1).set_stroke(width=0).scale(0.13).rotate(PI).next_to([0, y0, 0], UP, buff=0.12)
        lab_b = T("试验前", 22, color=TEXT).next_to(tri_b, UP, buff=0.06)
        lim = T("允许变化范围", 20, color="#3DDC97").next_to(lab_b, LEFT, buff=0.6)
        self.play(Create(bar), FadeIn(ok), FadeIn(xk), FadeIn(tri_b), FadeIn(lab_b), FadeIn(lim), run_time=0.8)
        after_x = ValueTracker(0.0)
        after = always_redraw(lambda: VGroup(
            Triangle().set_fill(FORCE, 1).set_stroke(width=0).scale(0.13),
            T("试验后", 22, color=FORCE)).arrange(DOWN, buff=0.06)
            .next_to([after_x.get_value(), y0, 0], DOWN, buff=0.12))
        self.play(FadeIn(after), run_time=0.3)
        self.play(after_x.animate.set_value(2.0), run_time=1.2, rate_func=smooth)
        warn = tag("超出限值 → 绕组可能变形", FORCE, 26).move_to([1.6, y0 - 1.25, 0])
        self.play(FadeIn(warn, scale=1.2), run_time=0.4)
        self.finish()


# ============================================================ S08 总结与预告
class S08_Outro(NarratedScene):
    def construct(self):
        self.add(corner_tag())
        center = LEFT * 3.6 + UP * 0.45
        sec, fl = section_with_field(center, field_opacity=0.35, scale=0.66)
        self.add(sec, fl)

        # “一句话总结：中部轴向漏磁，把绕组里外撑开；”
        fr = VGroup(sec.radial_forces("lv", length=0.5), sec.radial_forces("hv", length=0.5))
        l1 = VGroup(tag("中部", FIELD, 28), T("轴向漏磁 → 里外撑开", 34, bold=True)).arrange(RIGHT, buff=0.3)
        l1.move_to([0.2 + l1.width / 2, 1.6, 0])
        head = T("一句话总结", 26, color=DIM).next_to(l1, UP, buff=0.35, aligned_edge=LEFT)
        self.play(FadeIn(head), run_time=0.4)
        self.play(LaggedStart(*[GrowArrow(a) for a in [*fr[0], *fr[1]]], lag_ratio=0.03),
                  FadeIn(l1, shift=LEFT * 0.2), run_time=1.2)

        # “端部径向漏磁，把绕组往中间压。”
        self.at(1)
        fa = VGroup(sec.axial_forces("lv", max_len=0.8, color=ACCENT), sec.axial_forces("hv", max_len=0.8, color=ACCENT))
        l2 = VGroup(tag("端部", FORCE, 28), T("径向漏磁 → 往中间压", 34, bold=True)).arrange(RIGHT, buff=0.3)
        l2.next_to(l1, DOWN, buff=0.45, aligned_edge=LEFT)
        self.play(LaggedStart(*[GrowArrow(a) for a in [*fa[0], *fa[1]]], lag_ratio=0.03),
                  FadeIn(l2, shift=LEFT * 0.2), run_time=1.2)

        # “下期聊聊：漏磁到底从哪来？”
        self.at(2)
        nxt = VGroup(T("下期预告", 26, color=DIM), T("漏磁到底从哪来？", 48, color=ACCENT, bold=True))
        nxt.arrange(DOWN, buff=0.15, aligned_edge=LEFT).next_to(l2, DOWN, buff=0.9, aligned_edge=LEFT)
        self.play(FadeIn(nxt, shift=UP * 0.3), run_time=0.8)
        self.finish()


# ============================================================ 封面
class Cover(Scene):
    def construct(self):
        center = LEFT * 3.75 + DOWN * 0.1
        sec = Section(center=center, scale=0.84)
        fl = sec.field(width=3).set_stroke(opacity=0.9)
        fr = VGroup(sec.radial_forces("lv", length=0.7), sec.radial_forces("hv", length=0.7),
                    sec.axial_forces("hv", max_len=0.9, color=ACCENT))
        self.add(sec, fl, fr)
        t1 = T("变压器短路", 92, bold=True)
        t2 = T("绕组为啥会变形？", 76, color=ACCENT, bold=True)
        sub = T("一分钟看懂短路电动力", 38, color=TEXT)
        g = VGroup(t1, t2, sub).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        g.move_to([0.45 + g.width / 2, 0.5, 0])
        ep = tag("EP01", FORCE, 34).next_to(g, UP, buff=0.35, aligned_edge=LEFT)
        chips = VGroup(tag("漏磁场", FIELD, 28), tag("洛伦兹力", HV, 28), tag("F ∝ I²", LV, 28)).arrange(RIGHT, buff=0.25)
        chips.next_to(g, DOWN, buff=0.5, aligned_edge=LEFT)
        self.add(g, ep, chips)
