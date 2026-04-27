# Changelog

## V1.0.0 — 2026-04-27

**新增** — 初始化 audio-gen TTS CLI。

- 引擎:edge-tts >= 6.1.9(微软 Edge 后端,免费、无 API key;旧版 6.1.0~6.1.8 有 WSS bug 故钉版本)
- 入口:`generate.py` — CLI 支持位置参数 / `--file` / stdin 三种输入方式
- 参数:`--voice`(默认 `zh-CN-XiaoxiaoNeural`)、`--rate`、`--volume`、`--out`、`--retries`、`--timeout`、`--list-voices`
- 健壮性:指数退避重试(默认 3 次)+ asyncio 单次超时(默认 30s)+ 0 字节兜底检查
- 输出:默认 `out/<ns_timestamp>_<voice>.mp3`(纳秒+voice 名,避免并发撞名)
- 退出码:`0` 成功 / `1` 参数缺文本 / `2` 网络/重试耗尽 / `3` 0 字节空音频
- 版本常量 `__version__` 内嵌脚本顶部
- 工程文件:`requirements.txt`、`.gitignore`、`out/.gitkeep`

**为什么** — 用户授权从空目录搭一个声音生成 agent 工具链,选 edge-tts 因为绿地项目无 GPU、最快上手、中文质量优秀。
