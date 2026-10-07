# 已接受的优化配音 · 2026-10-07

[试听成品](audio/narration.wav) · [逐字文稿](audio/narration.txt) · [交付清单](delivery.json)

这是用户本轮试听接受的原文件，23.78 秒、32 kHz、单声道 PCM16。保留原始音频字节，
没有重新设计音色或增加朗诵处理。可直接导入剪辑软件。视频制作需要 48 kHz 时，
在导入或交付转换环节重采样并另存，原成品用于溯源。

模型采用个人 GPT 第 12 轮与优化 SoVITS 第 12 轮（816 步），9.35 秒原声参考。
配置保持整段生成、常速、段间 100 ms；不强制压尾音、不移调、不拉伸语速。
`profile.json` 记录完整设置及文件指纹。权重用 Git LFS 保存：克隆后执行 `git lfs pull`。

## 继续生成（可选）

生成工具需要单独准备 GPT-SoVITS 与 PyTorch/CUDA 环境；没有自动下载或安装行为。
本次运行环境为 GPT-SoVITS v2ProPlus、PyTorch 2.7.1+cu128、RTX 5070 Laptop 8 GB。
GPT-SoVITS 的 `pretrained_models/` 需要 chinese-roberta-wwm-ext-large、chinese-hubert-base、
以及 `sv/pretrained_eres2netv2w24s4ep4.ckpt`。运行时环境及基础模型不作为视频项目依赖。

在仓库根目录使用装有上述依赖的 Python：

```text
python voicepacks/tools/generate_gpt_sovits.py --pack voicepacks/optimized-2026-10-07 --runtime /path/to/GPT-SoVITS --text-file /path/to/script.txt --output local-data/new-voice
python -m scripts.voice_delivery local-data/new-voice/delivery.json
```

Windows 本机也可双击 `生成配音.cmd`，修改旁边的 `文案.txt`。此入口使用仓库旁现有
训练环境和 GPT-SoVITS，可用 `VOICE_PYTHON` 与 `GPT_SOVITS_HOME` 环境变量替换位置。
输出写入忽略的 `local-data/voice-output/`，不会覆盖成品或已有生成目录。

更换模型只需要新的包和其配置，视频端无需改代码。GPU 即使固定种子也可能有微小
数值差异；配置保证生成条件可追溯，不宣称重新生成会逐字节一致。
