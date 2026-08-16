# Timeless

Local personal assistant for a MacBook and a Samsung phone. Personal use. **$0** — no paid APIs.

Spec: [`docs/superpowers/specs/2026-08-15-timeless-design.md`](docs/superpowers/specs/2026-08-15-timeless-design.md)

## What this repo is today

The **brain**: SQLite + a local web UI (dashboard, chat, daily gate, meeting halt), opportunity approvals, ritual Done + praise, ingest endpoints for URLs / screen text / phone events / mail cards.

Not yet wired: ActivityWatch, screenpipe-from-source, real IMAP/Gmail, Android observer APK, launchd login item, Tailscale recipe. Those attach to the same APIs.

## Run

```bash
cd timeless
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
TIMELESS_HOST=127.0.0.1 TIMELESS_PORT=8787 timeless
```

Open http://127.0.0.1:8787 — you will hit the **daily gate** until you type outcomes and a timeline.

For phone access on the LAN or Tailscale:

```bash
TIMELESS_HOST=0.0.0.0 TIMELESS_PORT=8787 timeless
```

Prefer binding to the Tailscale IP rather than a public interface.

Chat uses Ollama at `OLLAMA_HOST` (default `http://127.0.0.1:11434`) and `OLLAMA_MODEL` (default `qwen2.5:7b`). If Ollama is down, chat still answers from the SQLite snapshot.

## Useful calls

```bash
# job URL → seen
curl -s -X POST http://127.0.0.1:8787/api/ingest/url \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://boards.greenhouse.io/acme/jobs/1","title":"SWE intern"}'

# confirmation on screen → approval card
curl -s -X POST http://127.0.0.1:8787/api/ingest/screen \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://boards.greenhouse.io/acme/jobs/1","text":"Thank you for applying"}'

# phone observer
curl -s -X POST http://127.0.0.1:8787/api/ingest/phone \
  -H 'Content-Type: application/json' \
  -d '{"summary":"Instagram 12m","payload":{"app":"instagram"}}'
```

Database default: `~/Library/Application Support/Timeless/timeless.db` (override with `TIMELESS_DB`).

## Next installs (free)

1. [ActivityWatch](https://github.com/ActivityWatch/activitywatch) on Mac + Android
2. Clone [screenpipe](https://github.com/screenpipe/screenpipe), build from source for personal use, point at Ollama — do not use the paid signed app
3. `ollama pull qwen2.5:7b`
4. Tailscale on Mac and phone
