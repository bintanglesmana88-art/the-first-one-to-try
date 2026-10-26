# 全自动工程原理动画流水线

电力设备原理科普短视频（B 站 / 抖音）。写好一期的旁白脚本和分镜代码，一条命令出 1080p 成片：

**脚本 `script.md` → 逐句中文配音 → 时间轴 → Manim 逐镜渲染（动画卡着配音走）→ 按配音时间轴切字幕 → ffmpeg 合成 MP4 + 封面**

全程不需要任何外部素材：画面是代码画的示意动画，磁力线和受力箭头由一个示意物理模型数值算出（`pipeline/physics.py`），保证方向正确。

## 已完成的期

| 期 | 标题 | 成片 | 时长 |
|---|---|---|---|
| EP01 | 变压器短路时，绕组为什么会变形？ | [`episodes/ep01_short_circuit_winding/ep01.mp4`](episodes/ep01_short_circuit_winding/ep01.mp4)（封面 `cover.png`，字幕 `ep01.srt`） | 116.8 秒 |

## 安装（Ubuntu / Debian）

```bash
bash setup.sh
```

它会做三件事：

1. 装系统依赖：`ffmpeg`、Pango/Cairo（Manim 需要）、中文字体 **Noto Sans CJK**（`fonts-noto-cjk`，画面和字幕都用它）。
2. 建 Python 虚拟环境 `.venv` 并安装 `requirements.txt`（Manim Community 0.22、sherpa-onnx 等）。
3. 下载离线配音模型（约 350 MB，缓存到 `~/.cache/gongcheng-tts/`）。

## 一条命令重做一期

```bash
.venv/bin/python -m pipeline build episodes/ep01_short_circuit_winding
```

输出（都在该期目录下）：`ep01.mp4` 成片（字幕已压进画面）、`ep01.srt` 字幕文件（上传平台时可单独用）、`cover.png` 封面，并把每镜实际时长写回 `script.md` 文末。中间文件在 `build/`（不入库）。

常用参数：

| 参数 | 作用 |
|---|---|
| `--preview` | 540p / 15fps 快速预览，输出 `ep01_preview.mp4` |
| `--only S03_LeakageField,S04_RadialForce` | 只重渲染某几个分镜（调画面用，不合成） |
| `--tts-only` | 只生成配音和时间轴 |
| `--tts kokoro\|edge\|auto` | 配音后端，默认 `kokoro`（见下） |
| `--jobs 4` | 并行渲染的进程数 |

配音自检（可选）：用离线中文语音识别把每句配音转回文字，和脚本对比，找读错的字：

```bash
.venv/bin/python -m pipeline.asr_check episodes/ep01_short_circuit_winding
```

## 配音方案

- **默认：sherpa-onnx + Kokoro-82M 多语种模型，中文男声 `zm_yunxi`，完全离线。**
  模型从 sherpa-onnx 的 GitHub Release 自动下载。语速在 `script.md` 头部的 `speed` 调（EP01 用 1.1，约每秒 4.5 字）。
- 可选：微软 `edge-tts`（`zh-CN-YunxiNeural`），加 `--tts edge`。EP01 制作时所在的云端环境访问不了微软语音服务（`speech.platform.bing.com` 被网络策略拦截），gTTS（Google）也不通，所以 EP01 用的是 Kokoro。`--tts auto` 会先试 edge，不通再自动退回 Kokoro。
- 多音字读错时，在脚本里用 `[字幕|读法]` 改读法，例如 `[屈曲|屈驱]`（词典把“屈曲”标成了 qū qǔ）。

## 新增一期

```bash
.venv/bin/python -m pipeline new ep02_leakage_flux "漏磁到底从哪里来？"
```

会从 `pipeline/template/` 复制出 `episodes/ep02_leakage_flux/`，然后：

1. 编辑 `script.md`：每个 `## 类名 | 说明` 是一个分镜，每个 `- ` 开头的行是一句旁白（配音、字幕都按句生成）。
2. 编辑 `scenes.py`：每个分镜写一个同名的 `NarratedScene` 子类。用 `self.at(i)` 等到第 i 句旁白开始再出对应画面，最后 `self.finish()` 补齐到配音结束；`Cover` 类画封面。可直接复用 `pipeline/narrated.py` 里的剖面图 `Section`（铁心 + 内外绕组 + 磁力线 + 径向/轴向力箭头）、俯视图 `TopView`、标签 `tag` 等。画面下方 `y < -3` 留给字幕。
3. 先 `--preview` 看效果，满意后去掉 `--preview` 出正片。

## 目录结构

```
pipeline/
  build.py       主流程（命令行入口：python -m pipeline）
  script.py      解析 script.md
  tts.py         配音（Kokoro 离线 / edge-tts）
  subtitles.py   按配音时间轴切字幕、生成 SRT
  narrated.py    Manim 场景基类（按旁白卡点）+ 可复用画面组件
  physics.py     示意性漏磁场模型（轴对称有限差分，铁心按理想导磁体）
  asr_check.py   配音自检（离线语音识别）
  template/      新一期的模板
episodes/
  ep01_short_circuit_winding/
    script.md    旁白全文 + 每镜时长
    scenes.py    分镜动画
    ep01.mp4     成片
    ep01.srt     字幕
    cover.png    封面
```

## 内容原则

- 画面全部是示意性二维剖面动画，不使用任何真实工程的数据或图片；数量级用“约”“可达”表述。
- 每期成片前，由独立的审稿代理只核对物理和标准表述，按意见修改后再出最终成片。

### EP01 审稿记录（独立审稿代理，只核对物理和标准表述）

已核对通过：内绕组受压向内、外绕组受拉向外；端部径向漏磁产生轴向力，指向绕组中部；50 Hz 来自“衰减直流分量 × 交流”，100 Hz 来自“交流²”。

审稿后的修改：

1. **（错误）电流符号画反了**：右侧剖面原来画的是内绕组 ⊙、外绕组 ⊗，和同屏的磁场箭头、力箭头不满足 F = IL×B。已改为右侧内绕组 ⊗、外绕组 ⊙（左侧相反）。
2. 把“洛伦兹力 F = I × B”改为“安培力 F = I L × B（本质是洛伦兹力）”。
3. “短路电流可达额定的十几到几十倍”改为“短路电流的**峰值**可达……”。
4. “短路时两绕组电流方向相反”改为“电流方向相反，短路时又特别大”（反向是安匝平衡的结果，平时就成立）。
5. “端部线饼受力最大，容易歪倒”改为“端部线饼单个受力最大，容易被压弯”。原文没有混淆“单饼受力最大的位置（端部）”和“垫块累积压力最大的位置（中部）”，只是“歪倒”的归因不准，所以改了说法。
6. 直流分量加上“最严重时”。“交流²”后面补上“外加恒定分量”。“力方向不变”改成从“i² 不会为负”推出来。
7. “短路试验或计算校核”改为“**动稳定**能力：短路承受能力试验，或计算加设计评估”（与 GB/T 1094.5 的表述一致）。
8. 总结里“把绕组里外撑开”改为“把内外绕组往两边推开”。
