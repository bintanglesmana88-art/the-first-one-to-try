"""配音自检：用离线中文语音识别（sherpa-onnx Paraformer）把每句配音转回文字，
和脚本逐句对比，找出读错、漏读的句子。

用法：python -m pipeline.asr_check episodes/ep01_short_circuit_winding
"""
from __future__ import annotations

import difflib
import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf

from . import script as script_mod
from . import tts

NAME = "sherpa-onnx-paraformer-zh-small-2024-03-09"
URL = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/{NAME}.tar.bz2"


def _model() -> Path:
    d = tts.CACHE / NAME
    if not (d / "model.int8.onnx").exists():
        tts.CACHE.mkdir(parents=True, exist_ok=True)
        tmp = tts.CACHE / f"{NAME}.tar.bz2"
        print(f"[asr] 下载识别模型：{URL}")
        urllib.request.urlretrieve(URL, tmp)
        with tarfile.open(tmp) as tf:
            tf.extractall(tts.CACHE)
        tmp.unlink()
    return d


def _norm(s: str) -> str:
    return re.sub(r"[^\w]", "", s)


def main(ep: str):
    import sherpa_onnx

    d = _model()
    rec = sherpa_onnx.OfflineRecognizer.from_paraformer(
        paraformer=str(d / "model.int8.onnx"), tokens=str(d / "tokens.txt"), num_threads=4)
    ep = Path(ep)
    scr = script_mod.load(ep / "script.md")
    timing = json.loads((ep / "build" / "timing.json").read_text(encoding="utf-8"))
    worst = []
    for shot, tshot in zip(scr.shots, timing["shots"]):
        wav, sr = sf.read(ep / "build" / "audio" / f"{shot.key}.wav", dtype="float32")
        for line, cue in zip(shot.lines, tshot["cues"]):
            seg = wav[int(cue["start"] * sr): int(cue["end"] * sr)]
            st = rec.create_stream()
            st.accept_waveform(sr, seg)
            rec.decode_stream(st)
            heard = st.result.text
            ratio = difflib.SequenceMatcher(None, _norm(line.spoken), _norm(heard)).ratio()
            worst.append((ratio, shot.key, line.spoken, heard))
            flag = "  " if ratio > 0.85 else "!!"
            print(f"{flag} {ratio:.2f} | {line.spoken}\n        听到：{heard}")
    worst.sort()
    print("\n最可疑的 5 句：")
    for r, k, a, b in worst[:5]:
        print(f"  {r:.2f} [{k}] {a} → {b}")


if __name__ == "__main__":
    main(sys.argv[1])
