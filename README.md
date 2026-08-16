# Timeless

Local personal assistant for a MacBook and a Samsung phone. Personal use. **$0**.

Spec: [`docs/superpowers/specs/2026-08-15-timeless-design.md`](docs/superpowers/specs/2026-08-15-timeless-design.md)

## On this Mac (already set up)

| Piece | Status |
|---|---|
| Timeless brain | LaunchAgent `com.timeless.brain` → http://127.0.0.1:8787 |
| Full-screen gate/halt overlay | LaunchAgent `com.timeless.overlay` |
| ActivityWatch | `/Applications/ActivityWatch.app` + login item, API `:5600` |
| AW → Timeless ingest | LaunchAgent `com.timeless.aw-ingest` every 2 minutes |
| Ollama | `brew services` + model `qwen2.5:7b` |
| Android APK | `~/Library/Application Support/Timeless/installers/aw-android.apk` |

Reinstall login services after a pull:

```bash
./scripts/install-launchd.sh
```

## You still have to click (macOS will not allow this unattended)

1. **ActivityWatch** → System Settings → Privacy & Security → **Accessibility** (and Screen Recording if asked). Without this, window titles stay empty.
2. Chrome extension [ActivityWatch Web Watcher](https://chromewebstore.google.com/detail/activitywatch-web-watcher) so job URLs reach Timeless.
3. Samsung: enable **Install unknown apps**, sideload `aw-android.apk`, grant Usage Access, disable battery optimization. USB was not plugged in during setup, so the phone app is not installed yet.
4. Overlay: first launch may ask to allow network / Accessibility. Keep it.

## Screenpipe (pixels on the Mac)

Do **not** buy the signed app. Personal build:

```bash
./scripts/build-screenpipe.sh
```

Needs Homebrew `rust`. First compile is long. Then point it at Ollama; Timeless will grow an ingest adapter next.

## Mail / Tailscale / calendar

Not installed yet. Brain APIs for mail cards and meetings exist; connect accounts in a later pass.

## Dev

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
