"""分镜模板。每个类对应 script.md 里的一个 "## 类名"。

- self.at(i)：等到本镜第 i 句旁白开始（i 从 0 数）。
- self.left(i)：距离第 i 句开始还剩多少秒，可用来给动画分配 run_time。
- self.finish()：补齐到本镜配音结束。
- 画面下方 y < -3 留给字幕。
可复用的画面组件见 pipeline/narrated.py（Section 剖面图、TopView 俯视图、tag 标签等）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from manim import *  # noqa: F401,F403

from pipeline.narrated import ACCENT, NarratedScene, Section, T, corner_tag, tag


class S01_Intro(NarratedScene):
    def construct(self):
        title = T("标题", 56, bold=True).to_edge(UP, buff=0.5)
        self.play(FadeIn(title), run_time=0.6)
        sec = Section(center=LEFT * 3 + UP * 0.3)
        self.play(FadeIn(sec), run_time=0.8)
        self.at(1)
        self.play(Indicate(sec.lv), run_time=1.0)
        self.finish()


class S02_Outro(NarratedScene):
    def construct(self):
        self.add(corner_tag("EP0X"))
        self.play(FadeIn(tag("一句话总结", ACCENT, 36)), run_time=0.6)
        self.at(1)
        self.play(FadeIn(T("下期预告", 40).shift(DOWN)), run_time=0.6)
        self.finish()


class Cover(Scene):
    def construct(self):
        self.add(T("封面标题", 96, bold=True))
