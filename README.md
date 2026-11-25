# 本地语音输入（SenseVoice · 完全离线）

按住说话、松手出字：把语音在**本机**转成文字，并自动粘贴回你正在用的窗口——可以配合微信、以及任何没有语音功能的聊天 / AI 软件使用。

> 语音识别全程在本地完成，不上传、不联网。

## 功能

- 🎤 短话：按住「按住说话」按钮；长话：点一下「按一下说话」再点停止
- 📋 自动把识别结果粘贴回你之前正在用的窗口（焦点自动切回）
- ⚡ 基于 SenseVoiceSmall（INT8 量化，约 228 MB），纯 CPU 即可运行
- 🔌 完全离线，隐私安全

## 环境要求

- Windows 10 / 11
- Python 3.10 及以上（已在 3.12 / 3.14 测试）
- 一个可用的麦克风

## 安装

```bash
pip install -r requirements.txt
```

## 准备语音模型

程序会按以下顺序查找模型文件（`model.int8.onnx` 和 `tokens.txt`）：

1. 本目录下的 `models/sensevoice-onnx/`
2. `~/.dsh/speech-to-text/sensevoice/models/sensevoice-onnx/`

推荐用 sherpa-onnx 官方导出的 SenseVoice INT8 模型。Windows PowerShell 下载并解压：

```powershell
cd 到本项目目录
Invoke-WebRequest -Uri "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2" -OutFile model.tar.bz2
tar -xjf model.tar.bz2
mkdir models\sensevoice-onnx -Force
Copy-Item "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17\model.int8.onnx" "models\sensevoice-onnx\"
Copy-Item "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17\tokens.txt" "models\sensevoice-onnx\"
```

## 运行

```bash
python voice_input.py
```

Windows 用户也可以直接双击 `启动语音输入.bat`（会自动创建虚拟环境并安装依赖）。

## 使用

1. 打开微信或任意输入框，让光标在输入框里闪烁
2. 短话：按住「按住说话」按钮说话，松手出字
3. 长话：点一下「按一下说话」按钮开始，说完再点一下停止并发送
4. 文字会自动粘贴进输入框

> 如果松手后文字没有自动贴进去：文字已复制到剪贴板，在输入框里按 `Ctrl+V` 手动粘贴即可。

## 配置

编辑 `voice_input.py` 顶部的配置项：

| 配置 | 说明 | 默认 |
| --- | --- | --- |
| `MAX_SECONDS` | 单次最长录音秒数 | 120 |
| `USE_ITN` | 数字/单位归一化（如「二十三年」→「2023年」） | True |
| `NUM_THREADS` | 识别线程数 | 2 |
| `PLAY_BEEP` | 开始/结束提示音 | True |

## 第三方组件与许可

本项目代码采用 **MIT 许可证**，可自由使用、修改、分发（含商用），详见 [LICENSE](LICENSE)。

用到的第三方组件：

- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)（Apache-2.0）
- [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) 模型（FunAudioLLM / 阿里，使用请遵守其模型许可）
- [sounddevice](https://python-sounddevice.readthedocs.io/)（MIT）
- [pynput](https://github.com/moses-palmer/pynput)（LGPL-3.0）
- [pyperclip](https://github.com/asweigart/pyperclip)（BSD）
- [numpy](https://numpy.org/)（BSD）

> ⚠️ 本项目代码为 MIT；但若分发二进制安装包，仍需遵守上述第三方组件的许可要求（尤其 pynput 的 LGPL 条款与 SenseVoice 模型许可）。
