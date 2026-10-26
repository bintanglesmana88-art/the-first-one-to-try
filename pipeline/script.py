"""解析一期的 script.md。

格式（示例见 episodes/ep01_short_circuit_winding/script.md）：

    ---
    title: 变压器短路时，绕组为什么会变形？
    voice: zm_yunxi
    speed: 1.0
    ---

    ## S01_Hook | 开场钩子
    - 一台变压器，出口突然短路。
    - 外加说明文字（不以 "- " 开头的行不会被朗读）

- 每个 "## 类名 | 说明" 是一个分镜，类名必须和 scenes.py 里的 Manim 场景类同名。
- 每个 "- " 开头的行是一句旁白，配音和字幕都按句生成。
- 行内写法 [字幕显示|朗读文本]：字幕显示前者，配音朗读后者。
  例如 [GB/T 1094.5|G B T 一零九四点五]。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_INLINE = re.compile(r"\[([^\[\]|]+)\|([^\[\]]+)\]")


@dataclass
class Line:
    raw: str

    @property
    def display(self) -> str:
        return _INLINE.sub(lambda m: m.group(1), self.raw)

    @property
    def spoken(self) -> str:
        return _INLINE.sub(lambda m: m.group(2), self.raw)


@dataclass
class Shot:
    key: str
    title: str
    lines: list[Line] = field(default_factory=list)


@dataclass
class Script:
    meta: dict
    shots: list[Shot]

    @property
    def text(self) -> str:
        return "".join(l.display for s in self.shots for l in s.lines)


def load(path: str | Path) -> Script:
    text = Path(path).read_text(encoding="utf-8")
    meta = {}
    if text.startswith("---"):
        _, fm, text = text.split("---", 2)
        meta = yaml.safe_load(fm) or {}
    # 自动生成的时长表不参与解析
    text = re.sub(r"<!-- timing:start -->.*?<!-- timing:end -->", "", text, flags=re.S)
    shots: list[Shot] = []
    for line in text.splitlines():
        m = re.match(r"^##\s+(\w+)\s*(?:\|\s*(.*))?$", line)
        if m:
            shots.append(Shot(m.group(1), (m.group(2) or "").strip()))
            continue
        m = re.match(r"^-\s+(.+)$", line)
        if m and shots:
            shots[-1].lines.append(Line(m.group(1).strip()))
    if not shots:
        raise ValueError(f"{path} 里没有找到分镜（## 类名 | 说明）")
    return Script(meta, shots)
