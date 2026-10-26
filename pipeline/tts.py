"""中文配音。

后端：
- kokoro（默认）：sherpa-onnx + Kokoro-82M 多语种模型，完全离线，中文男声 zm_yunxi。
  首次运行会从 GitHub Release 自动下载模型（约 350 MB）到 ~/.cache/gongcheng-tts/。
- edge：微软 edge-tts（zh-CN-YunxiNeural），需要能访问 speech.platform.bing.com。

所有后端都输出 24 kHz 单声道 float32 numpy 数组。
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import os
import subprocess
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24000
CACHE = Path(os.environ.get("GONGCHENG_CACHE", Path.home() / ".cache" / "gongcheng-tts"))
KOKORO_NAME = "kokoro-multi-lang-v1_0"
KOKORO_URL = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/{KOKORO_NAME}.tar.bz2"
# kokoro-multi-lang-v1_0 的中文音色编号
KOKORO_VOICES = {
    "zf_xiaobei": 45, "zf_xiaoni": 46, "zf_xiaoxiao": 47, "zf_xiaoyi": 48,
    "zm_yunjian": 49, "zm_yunxi": 50, "zm_yunxia": 51, "zm_yunyang": 52,
}


def _ensure_kokoro() -> Path:
    d = CACHE / KOKORO_NAME
    if (d / "model.onnx").exists():
        return d
    CACHE.mkdir(parents=True, exist_ok=True)
    print(f"[tts] 下载 Kokoro 模型：{KOKORO_URL}")
    tmp = CACHE / f"{KOKORO_NAME}.tar.bz2"
    urllib.request.urlretrieve(KOKORO_URL, tmp)
    with tarfile.open(tmp) as tf:
        tf.extractall(CACHE)
    tmp.unlink()
    return d


class KokoroTTS:
    name = "kokoro"

    def __init__(self, voice: str = "zm_yunxi", speed: float = 1.0):
        import sherpa_onnx

        d = _ensure_kokoro()
        kokoro = sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=str(d / "model.onnx"),
            voices=str(d / "voices.bin"),
            tokens=str(d / "tokens.txt"),
            data_dir=str(d / "espeak-ng-data"),
            dict_dir=str(d / "dict"),
            lexicon=f"{d / 'lexicon-us-en.txt'},{d / 'lexicon-zh.txt'}",
        )
        cfg = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(kokoro=kokoro, num_threads=os.cpu_count() or 2),
            rule_fsts=",".join(str(d / f) for f in ("date-zh.fst", "number-zh.fst", "phone-zh.fst")),
        )
        self.tts = sherpa_onnx.OfflineTts(cfg)
        self.sid = KOKORO_VOICES[voice]
        self.speed = speed
        self.tag = f"kokoro-{voice}-{speed}"

    def __call__(self, text: str) -> np.ndarray:
        a = self.tts.generate(text, sid=self.sid, speed=self.speed)
        y = np.asarray(a.samples, dtype=np.float32)
        if a.sample_rate != SR:
            y = _resample(y, a.sample_rate)
        return y


class EdgeTTS:
    name = "edge"

    def __init__(self, voice: str = "zh-CN-YunxiNeural", speed: float = 1.0):
        import edge_tts  # noqa: F401

        self.voice = voice if voice.startswith("zh-") else "zh-CN-YunxiNeural"
        self.rate = f"{round((speed - 1) * 100):+d}%"
        self.tag = f"edge-{self.voice}-{self.rate}"

    def __call__(self, text: str) -> np.ndarray:
        import edge_tts

        async def run():
            buf = b""
            proxy = os.environ.get("HTTPS_PROXY")
            async for chunk in edge_tts.Communicate(text, self.voice, rate=self.rate, proxy=proxy).stream():
                if chunk["type"] == "audio":
                    buf += chunk["data"]
            return buf

        mp3 = asyncio.run(run())
        wav = subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", str(SR), "-f", "wav", "pipe:1"],
            input=mp3, capture_output=True, check=True).stdout
        y, _ = sf.read(io.BytesIO(wav), dtype="float32")
        return y


def _resample(y: np.ndarray, sr: int) -> np.ndarray:
    from scipy.signal import resample_poly
    from math import gcd

    g = gcd(sr, SR)
    return resample_poly(y, SR // g, sr // g).astype(np.float32)


def trim_silence(y: np.ndarray, thresh: float = 0.01, pad: float = 0.03) -> np.ndarray:
    idx = np.flatnonzero(np.abs(y) > thresh)
    if idx.size == 0:
        return y
    p = int(pad * SR)
    return y[max(idx[0] - p, 0): idx[-1] + p]


def make_engine(backend: str, voice: str, speed: float):
    if backend == "edge":
        return EdgeTTS(voice, speed)
    if backend == "kokoro":
        return KokoroTTS(voice, speed)
    if backend == "auto":
        try:
            eng = EdgeTTS(voice, speed)
            eng("测试")
            return eng
        except Exception as e:  # 网络不通等
            print(f"[tts] edge-tts 不可用（{type(e).__name__}），改用离线 Kokoro")
            return KokoroTTS(voice if voice in KOKORO_VOICES else "zm_yunxi", speed)
    raise ValueError(f"未知配音后端 {backend}")


def synth_cached(engine, text: str, cache_dir: Path) -> np.ndarray:
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{engine.tag}|{text}".encode()).hexdigest()[:16]
    f = cache_dir / f"{key}.wav"
    if f.exists():
        y, _ = sf.read(f, dtype="float32")
        return y
    y = trim_silence(engine(text))
    sf.write(f, y, SR)
    return y
