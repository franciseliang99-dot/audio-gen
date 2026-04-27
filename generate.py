#!/usr/bin/env python3
"""TTS CLI: text -> mp3 via edge-tts (Microsoft Edge backend, free, no API key)."""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

import edge_tts

__version__ = "1.0.0"

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_RETRIES = 3
DEFAULT_TIMEOUT = 30.0
ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


async def _synth_once(text: str, voice: str, rate: str, volume: str,
                      out: Path, timeout: float) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tts = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
    await asyncio.wait_for(tts.save(str(out)), timeout=timeout)


async def synth(text: str, voice: str, rate: str, volume: str,
                out: Path, timeout: float, retries: int) -> None:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            await _synth_once(text, voice, rate, volume, out, timeout)
            if out.exists() and out.stat().st_size > 0:
                return
            raise RuntimeError("empty audio stream")
        except Exception as e:
            last_err = e
            if attempt < retries:
                wait = 2 ** (attempt - 1)
                print(f"  attempt {attempt}/{retries} failed ({e!r}); retry in {wait}s",
                      file=sys.stderr)
                await asyncio.sleep(wait)
    raise RuntimeError(f"all {retries} attempts failed; last error: {last_err!r}")


async def list_zh_voices() -> None:
    voices = await edge_tts.list_voices()
    for v in sorted(voices, key=lambda x: x["ShortName"]):
        if v["Locale"].startswith("zh-"):
            print(f"{v['ShortName']:34s} {v['Gender']:7s} {v['Locale']}")


def resolve_text(args: argparse.Namespace) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8").strip()
    if args.text:
        return args.text.strip()
    if not sys.stdin.isatty():
        data = sys.stdin.read().strip()
        if data:
            return data
    return ""


def main() -> int:
    p = argparse.ArgumentParser(
        prog="generate.py",
        description="TTS via edge-tts. Text -> mp3.",
    )
    p.add_argument("text", nargs="?", help="待合成文本(也可 --file / stdin)")
    p.add_argument("-f", "--file", help="从文件读文本(UTF-8)")
    p.add_argument("-v", "--voice", default=DEFAULT_VOICE,
                   help=f"声音名,默认 {DEFAULT_VOICE}。--list-voices 查看全部 zh- 声音")
    p.add_argument("-r", "--rate", default="+0%",
                   help="语速,如 +10%% / -20%%(默认 +0%%)")
    p.add_argument("--volume", default="+0%",
                   help="音量,如 +10%% / -10%%(默认 +0%%)")
    p.add_argument("-o", "--out", help="输出 mp3 路径(默认 out/<ns_ts>_<voice>.mp3)")
    p.add_argument("--retries", type=int, default=DEFAULT_RETRIES,
                   help=f"网络重试次数,指数退避(默认 {DEFAULT_RETRIES})")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                   help=f"单次合成超时秒数(默认 {DEFAULT_TIMEOUT})")
    p.add_argument("--list-voices", action="store_true", help="列出全部中文声音并退出")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args()

    if args.list_voices:
        asyncio.run(list_zh_voices())
        return 0

    text = resolve_text(args)
    if not text:
        print("ERROR: 需要文本输入(位置参数 / --file / stdin)", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else OUT_DIR / f"{time.time_ns()}_{args.voice}.mp3"

    try:
        asyncio.run(synth(text, args.voice, args.rate, args.volume,
                          out, args.timeout, args.retries))
    except Exception as e:
        print(f"ERROR: 合成失败 — {e}", file=sys.stderr)
        return 2

    size = out.stat().st_size if out.exists() else 0
    if size == 0:
        print(f"ERROR: 0 bytes 输出 — {out}", file=sys.stderr)
        return 3

    print(f"[v{__version__}] saved {out}  ({size} bytes, voice={args.voice}, len={len(text)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
