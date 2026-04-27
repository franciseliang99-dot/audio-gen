#!/usr/bin/env python3
"""TTS CLI: text -> mp3 via edge-tts (Microsoft Edge backend, free, no API key)."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

__version__ = "1.0.2"

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_RETRIES = 3
DEFAULT_TIMEOUT = 30.0
ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


def _health_dict() -> dict:
    deps, checks, reasons = [], [], []
    try:
        import edge_tts as _et
        ver = getattr(_et, "__version__", "unknown")
        deps.append({"name": "edge-tts", "kind": "python", "ok": True,
                     "found": ver, "required": ">=6.1.9"})
    except ImportError as e:
        deps.append({"name": "edge-tts", "kind": "python", "ok": False, "error": str(e)})
        reasons.append("edge-tts not installed (critical)")

    crit = [d for d in deps if not d["ok"]]
    healthy = not crit and not [c for c in checks if not c["ok"]]
    severity = "ok" if healthy else ("broken" if crit else "degraded")
    return {
        "name": "audio-gen", "version": __version__,
        "healthy": healthy,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "deps": deps, "env": [], "checks": checks, "reasons": reasons,
        "extra": {
            "runtime": f"python{sys.version_info.major}.{sys.version_info.minor}",
            "venv": str(Path(sys.executable).parent.parent),
            "severity": severity,
        },
    }


def _emit_health_or_version() -> None:
    """Pre-arg-parse: --version --json -> health JSON + exit; --version alone -> argparse handles."""
    if "--version" in sys.argv and "--json" in sys.argv:
        h = _health_dict()
        print(json.dumps(h, indent=2, ensure_ascii=False))
        sys.exit(0 if h["healthy"] else (1 if h["extra"]["severity"] == "degraded" else 2))


async def synth(text: str, voice: str, rate: str, volume: str,
                out: Path, timeout: float, retries: int) -> None:
    import edge_tts  # imported here so --version --json works without edge_tts installed
    out.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            tts = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
            await asyncio.wait_for(tts.save(str(out)), timeout=timeout)
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
    import edge_tts
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
    _emit_health_or_version()
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
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}",
                   help="打印版本(配 --json 输出健康自检 JSON)")
    p.add_argument("--json", action="store_true", help="与 --version 联用,输出健康自检 JSON")
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

    size = out.stat().st_size
    print(f"[v{__version__}] saved {out}  ({size} bytes, voice={args.voice}, len={len(text)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
