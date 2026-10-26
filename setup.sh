#!/usr/bin/env bash
# 一次性安装：系统依赖 + Python 虚拟环境 + 离线配音模型。
# 用法：bash setup.sh        （Ubuntu/Debian，需要 sudo 或 root）
set -euo pipefail
cd "$(dirname "$0")"

SUDO=""
if [ "$(id -u)" != "0" ]; then SUDO="sudo"; fi

echo "== 1/3 系统依赖（ffmpeg、Pango/Cairo、中文字体 Noto Sans CJK）"
$SUDO apt-get update -qq
DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq \
  ffmpeg libcairo2-dev libpango1.0-dev pkg-config python3-venv python3-dev fonts-noto-cjk

echo "== 2/3 Python 虚拟环境 .venv"
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip setuptools wheel
.venv/bin/pip install -q -r requirements.txt

echo "== 3/3 下载离线配音模型（Kokoro 多语种，约 350 MB，缓存在 ~/.cache/gongcheng-tts）"
.venv/bin/python -c "from pipeline.tts import _ensure_kokoro; print(_ensure_kokoro())"

fc-list :lang=zh | grep -q "Noto Sans CJK SC" && echo "中文字体 OK" || echo "警告：没找到 Noto Sans CJK SC 字体"
echo "安装完成。试试：.venv/bin/python -m pipeline build episodes/ep01_short_circuit_winding"
