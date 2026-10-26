"""一条命令做一期：脚本 → 配音 → 时间轴 → Manim 分镜渲染 → 字幕 → ffmpeg 合成。

用法：
    python -m pipeline build episodes/ep01_short_circuit_winding
    python -m pipeline build episodes/ep01_short_circuit_winding --only S03_LeakageField --preview
    python -m pipeline new ep02_leakage_flux "漏磁到底从哪里来？"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf

from . import script as script_mod
from . import subtitles, tts

ROOT = Path(__file__).resolve().parents[1]
FONT = "Noto Sans CJK SC"

LINE_GAP = 0.28    # 句间停顿（秒）
SHOT_HEAD = 0.3    # 每镜开头留白
SHOT_TAIL = 0.5    # 每镜结尾留白


def run(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout
    return float(out.strip())


# ---------------------------------------------------------------- 1. 配音 + 时间轴
def stage_tts(ep: Path, scr, backend: str) -> dict:
    build = ep / "build"
    engine = tts.make_engine(backend, scr.meta.get("voice", "zm_yunxi"), float(scr.meta.get("speed", 1.0)))
    print(f"[tts] 后端：{engine.tag}")
    timing = {"tts": engine.tag, "shots": []}
    audio_dir = build / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    gap = np.zeros(int(LINE_GAP * tts.SR), np.float32)
    for shot in scr.shots:
        pieces = [np.zeros(int(SHOT_HEAD * tts.SR), np.float32)]
        t = SHOT_HEAD
        cues = []
        for i, line in enumerate(shot.lines):
            y = tts.synth_cached(engine, line.spoken, build / "tts_cache")
            cues.append({"start": round(t, 3), "end": round(t + len(y) / tts.SR, 3), "text": line.display})
            pieces.append(y)
            t += len(y) / tts.SR
            if i < len(shot.lines) - 1:
                pieces.append(gap); t += LINE_GAP
        pieces.append(np.zeros(int(SHOT_TAIL * tts.SR), np.float32))
        wav = np.concatenate(pieces)
        sf.write(audio_dir / f"{shot.key}.wav", wav, tts.SR)
        timing["shots"].append({"key": shot.key, "title": shot.title,
                                "duration": round(len(wav) / tts.SR, 3), "cues": cues})
        print(f"[tts] {shot.key}: {len(wav) / tts.SR:.1f}s, {len(cues)} 句")
    (build / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    return timing


# ---------------------------------------------------------------- 2. Manim 渲染
def manim_cmd(ep: Path, scene: str, preview: bool, still: bool = False):
    build = ep / "build"
    cmd = [sys.executable, "-m", "manim", "render", "--disable_caching", "--progress_bar", "none",
           "--media_dir", build / "media" / scene, "-o", scene]
    if preview:
        cmd += ["-r", "960,540", "--fps", "15"]
    else:
        cmd += ["-r", "1920,1080", "--fps", "30"]
    if still:
        cmd += ["-s", "--format", "png"]
    cmd += [ep / "scenes.py", scene]
    return cmd


def find_output(ep: Path, scene: str, ext: str) -> Path:
    hits = sorted((ep / "build" / "media").rglob(f"{scene}{ext}"), key=lambda p: p.stat().st_mtime)
    if not hits:
        raise FileNotFoundError(f"找不到 {scene}{ext} 的渲染结果")
    return hits[-1]


def stage_render(ep: Path, keys: list[str], preview: bool, jobs: int):
    env = dict(os.environ, PYTHONPATH=f"{ROOT}{os.pathsep}{os.environ.get('PYTHONPATH', '')}")
    log_dir = ep / "build" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    def one(key):
        with open(log_dir / f"{key}.log", "w") as log:
            r = subprocess.run([str(c) for c in manim_cmd(ep, key, preview)], env=env, cwd=ep,
                               stdout=log, stderr=subprocess.STDOUT)
        if r.returncode:
            raise RuntimeError(f"渲染 {key} 失败，见 {log_dir / (key + '.log')}")
        print(f"[render] {key} 完成")
        return key

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        list(ex.map(one, keys))


# ---------------------------------------------------------------- 3. 合成
def stage_compose(ep: Path, timing: dict, out_name: str, preview: bool):
    build = ep / "build"
    concat_list = build / "concat.txt"
    lines, audio, cues = [], [], []
    offset = 0.0
    for shot in timing["shots"]:
        video = find_output(ep, shot["key"], ".mp4")
        vdur = probe_duration(video)
        lines.append(f"file '{video.resolve()}'")
        wav, _ = sf.read(build / "audio" / f"{shot['key']}.wav", dtype="float32")
        n = int(round(vdur * tts.SR))
        wav = np.pad(wav, (0, max(0, n - len(wav))))[:n]  # 音频与该镜视频严格等长
        audio.append(wav)
        sc = shot["cues"]
        for i, c in enumerate(sc):
            nxt = sc[i + 1]["start"] if i + 1 < len(sc) else c["end"] + SHOT_TAIL * 0.8
            end = min(nxt, c["end"] + 0.3)
            cues += [(offset + a, offset + b, t) for a, b, t in subtitles.cues_for_line(c["text"], c["start"], end)]
        offset += vdur
    concat_list.write_text("\n".join(lines) + "\n")
    narration = build / "narration.wav"
    sf.write(narration, np.concatenate(audio), tts.SR)
    srt = ep / f"{out_name}.srt"
    srt.write_text(subtitles.to_srt(cues), encoding="utf-8")

    style = (f"FontName={FONT},FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
             f"BackColour=&H80000000,BorderStyle=1,Outline=1.6,Shadow=0.6,Bold=1,MarginV=18")
    srt_esc = str(srt.resolve()).replace("\\", "/").replace(":", r"\:")
    out = ep / f"{out_name}.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-i", narration,
         "-vf", f"subtitles='{srt_esc}':force_style='{style}'",
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-c:v", "libx264", "-preset", "medium", "-crf", "22" if preview else "19",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
         "-movflags", "+faststart", "-shortest", out])
    print(f"[compose] 输出 {out}（{probe_duration(out):.1f} 秒）")
    return out


def stage_cover(ep: Path):
    env = dict(os.environ, PYTHONPATH=f"{ROOT}{os.pathsep}{os.environ.get('PYTHONPATH', '')}")
    run(manim_cmd(ep, "Cover", preview=False, still=True), env=env, cwd=ep)
    png = find_output(ep, "Cover", ".png")
    shutil.copy(png, ep / "cover.png")
    print(f"[cover] 输出 {ep / 'cover.png'}")


def update_script_timing(ep: Path, timing: dict, total: float):
    path = ep / "script.md"
    text = path.read_text(encoding="utf-8")
    rows = ["| 分镜 | 内容 | 时长（秒） |", "|---|---|---|"]
    for s in timing["shots"]:
        rows.append(f"| {s['key']} | {s['title']} | {s['duration']:.1f} |")
    rows.append(f"| **合计** | 成片（含字幕） | **{total:.1f}** |")
    block = ("<!-- timing:start -->\n## 每镜时长（由流水线按配音自动生成）\n\n"
             f"配音：`{timing['tts']}`\n\n" + "\n".join(rows) + "\n<!-- timing:end -->")
    text = re.sub(r"<!-- timing:start -->.*?<!-- timing:end -->", block, text, flags=re.S)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- 命令行
def cmd_build(args):
    ep = Path(args.episode).resolve()
    scr = script_mod.load(ep / "script.md")
    keys = [s.key for s in scr.shots]
    if args.only:
        keys = [k for k in keys if k in args.only.split(",")]
    timing = stage_tts(ep, scr, args.tts)
    if args.tts_only:
        return
    stage_render(ep, keys, args.preview, args.jobs)
    if args.only:
        print("[build] 只渲染了部分分镜，跳过合成。")
        return
    name = ep.name.split("_")[0]
    out = stage_compose(ep, timing, name + ("_preview" if args.preview else ""), args.preview)
    if not args.preview:
        stage_cover(ep)
        update_script_timing(ep, timing, probe_duration(out))


def cmd_new(args):
    ep = ROOT / "episodes" / args.name
    if ep.exists():
        sys.exit(f"{ep} 已存在")
    tpl = ROOT / "pipeline" / "template"
    shutil.copytree(tpl, ep)
    s = (ep / "script.md").read_text(encoding="utf-8").replace("{{TITLE}}", args.title)
    (ep / "script.md").write_text(s, encoding="utf-8")
    print(f"已创建 {ep}。编辑 script.md 和 scenes.py 后运行：\n  python -m pipeline build {ep.relative_to(ROOT)}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="pipeline", description="全自动工程原理动画流水线")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="生成一期视频")
    b.add_argument("episode", help="期目录，如 episodes/ep01_short_circuit_winding")
    b.add_argument("--tts", default="kokoro", choices=["kokoro", "edge", "auto"],
                   help="配音后端：kokoro=离线（默认），edge=微软 edge-tts，auto=先试 edge 再退回 kokoro")
    b.add_argument("--preview", action="store_true", help="540p/15fps 快速预览")
    b.add_argument("--only", help="只渲染指定分镜（逗号分隔），不合成")
    b.add_argument("--tts-only", action="store_true", help="只生成配音和时间轴")
    b.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 0), help="并行渲染进程数")
    b.set_defaults(func=cmd_build)
    n = sub.add_parser("new", help="新建一期（从模板复制）")
    n.add_argument("name", help="目录名，如 ep02_leakage_flux")
    n.add_argument("title", help="标题")
    n.set_defaults(func=cmd_new)
    args = p.parse_args(argv)
    args.func(args)
