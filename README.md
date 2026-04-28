# audio-gen

Text-to-speech narration CLI for short videos. Wraps [edge-tts](https://github.com/rany2/edge-tts) (Microsoft Edge's read-aloud voices) with retry + size validation.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Usage

```bash
.venv/bin/python generate.py "Welcome to today's video." -v en-US-AriaNeural -o intro.mp3
.venv/bin/python generate.py "..." -v zh-CN-XiaoxiaoNeural    # Chinese voice
.venv/bin/python generate.py --list-voices                    # show available voices
```

Output is an MP3. Exit codes: `0` ok, `1` invalid args, `2` synthesis failed after retries.

## License

MIT — see [LICENSE](LICENSE).
