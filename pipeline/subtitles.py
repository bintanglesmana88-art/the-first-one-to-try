"""按配音时间轴生成字幕（SRT）。

每句旁白有精确的起止时间（逐句合成配音得到）。一句太长时按标点切成几条，
句内各条按字数分配时间。
"""
from __future__ import annotations

import re

MAX_CHARS = 16
_BREAK = "，。；：！？、,;:!?"
_DROP_TAIL = "，。；：、,;:"


def _visual_len(s: str) -> float:
    # 英文字母和数字大约占半个汉字宽
    return sum(0.5 if ord(c) < 128 else 1.0 for c in s)


def split_line(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    # 先按标点切成小段（标点留在段尾）
    parts = re.findall(rf"[^{_BREAK}]+[{_BREAK}]*|[{_BREAK}]+", text)
    chunks: list[str] = []
    cur = ""
    for p in parts:
        if cur and _visual_len(cur + p) > max_chars:
            chunks.append(cur); cur = p
        else:
            cur += p
    if cur:
        chunks.append(cur)
    # 单段仍然过长时硬切
    out = []
    for c in chunks:
        while _visual_len(c) > max_chars + 2:
            out.append(c[:max_chars]); c = c[max_chars:]
        out.append(c)
    return out


def clean(chunk: str) -> str:
    return chunk.strip().rstrip(_DROP_TAIL).strip()


def cues_for_line(text: str, start: float, end: float) -> list[tuple[float, float, str]]:
    chunks = split_line(text)
    weights = [max(_visual_len(clean(c)), 1.0) + 0.6 * sum(ch in _BREAK for ch in c) for c in chunks]
    total = sum(weights)
    t = start
    cues = []
    for c, w in zip(chunks, weights):
        dt = (end - start) * w / total
        cues.append((t, t + dt, clean(c)))
        t += dt
    return [c for c in cues if c[2]]


def _ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(cues: list[tuple[float, float, str]]) -> str:
    out = []
    for i, (a, b, text) in enumerate(cues, 1):
        out.append(f"{i}\n{_ts(a)} --> {_ts(b)}\n{text}\n")
    return "\n".join(out)
