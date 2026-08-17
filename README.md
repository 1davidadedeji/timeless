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
| Screenpipe (personal binary) | LaunchAgent `com.timeless.screenpipe` — screen OCR, no mic |
| Screenpipe → Timeless | LaunchAgent `com.timeless.sp-ingest` every 3 minutes |
| Android APK | `~/Library/Application Support/Timeless/installers/aw-android.apk` |

Phone install when USB is connected:

```bash
./scripts/install-phone.sh
```

Reinstall login services after a pull:

```bash
./scripts/install-launchd.sh
```

## You still have to click (macOS will not allow this unattended)

1. **ActivityWatch** → System Settings → Privacy & Security → **Accessibility** (and Screen Recording if asked). Without this, window titles stay empty.
2. Chrome extension [ActivityWatch Web Watcher](https://chromewebstore.google.com/detail/activitywatch-web-watcher) so job URLs reach Timeless.
3. **Now (USB):** Developer options + USB debugging on the Samsung, plug into this Mac, allow the RSA prompt, then run `./scripts/install-phone.sh`. Then Usage Access ON and battery optimization OFF for ActivityWatch.
4. Overlay: first launch may ask to allow network / Accessibility. Keep it.

## Screenpipe (pixels on the Mac)

Personal build is already at `~/Library/Application Support/Timeless/bin/screenpipe` (not the paid app). `install-launchd.sh` starts `screenpipe record --disable-audio`. Approve Screen Recording if macOS asks again.

Rebuild later with `./scripts/build-screenpipe.sh`.

## Mail / Tailscale / calendar

Calendar.app (EventKit) and Mail.app ingest on a timer. Allow Calendar and Automation when macOS asks. Dashboard: http://127.0.0.1:8787 — Chicago timezone, nightly recap overlay at 23:55.

Phone: brain binds `0.0.0.0:8787` with a token (loopback is open). Copy the LAN/Tailscale URL from Sensors. Overlay stays on localhost and **does not use the Dock** (agent policy).

Wireless ADB after reboot: in `~/Library/Application Support/Timeless/phone-adb.conf` set `ADB_PAIR_HOST`, `ADB_PAIR_PORT`, `ADB_PAIR_CODE` from Wireless debugging → Pair with pairing code. The pull job retries connect + mDNS.

Chrome URLs: `./scripts/install-chrome-aw.sh` then click Add.

## Dev

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
