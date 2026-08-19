from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from timeless.access import advertised_hosts, ui_token
from timeless.quiet import blocks_phone

STATE_FILE = Path.home() / "Library/Application Support/Timeless" / "last-halt-alert.json"
ESCALATION_FILE = Path.home() / "Library/Application Support/Timeless/halt-escalations.json"

# Escalation timing (seconds after first seen)
LEVEL_AT = {1: 120, 2: 300, 3: 600}


def _adb(args: list[str]) -> None:
    serial = os.environ.get("TIMELESS_ADB_SERIAL", "")
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    else:
        listing = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=False)
        serials: list[str] = []
        for ln in listing.stdout.splitlines()[1:]:
            parts = ln.split()
            if len(parts) >= 2 and parts[1] == "device":
                serials.append(parts[0])
        if not serials:
            raise RuntimeError("no adb phone")
        wireless = [s for s in serials if ":" in s]
        cmd += ["-s", (wireless or serials)[0]]
    subprocess.run(cmd + args, check=True, timeout=20)


def phone_halt_url() -> str:
    token = ui_token()
    port = int(os.environ.get("TIMELESS_PORT", "8787"))
    host = next((h for h in advertised_hosts() if h != "127.0.0.1"), "127.0.0.1")
    return f"http://{host}:{port}/halt?token={token}"


def halt_alert_key(halt: dict[str, Any]) -> str:
    mid = halt.get("meeting_id") or halt.get("id")
    return f"{halt.get('halt_kind') or 'meeting'}:{halt.get('id')}:{mid}"


def _load_escalations() -> dict[str, Any]:
    if not ESCALATION_FILE.exists():
        return {}
    try:
        return json.loads(ESCALATION_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_escalations(data: dict[str, Any]) -> None:
    ESCALATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    ESCALATION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clear_escalation_state() -> None:
    if ESCALATION_FILE.exists():
        ESCALATION_FILE.unlink(missing_ok=True)
    clear_halt_alert_state()


def clear_halt_alert_state() -> None:
    if STATE_FILE.exists():
        STATE_FILE.unlink(missing_ok=True)


def notify_halt(halt: dict[str, Any], *, level: int = 2, force: bool = False) -> dict[str, Any]:
    """Push halt alert to phone. level 1=silent ping, 2=open page, 3=alarm."""
    key = halt_alert_key(halt)
    title = str(halt.get("title") or "Timeless")
    url = phone_halt_url()
    body = "Tap to join or check in."
    if level >= 3:
        title = f"URGENT: {title}"
        body = "Timeless needs you on this meeting. Tap to respond."

    if not force and level <= 2 and STATE_FILE.exists():
        try:
            last = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if last.get("key") == key and last.get("level", 0) >= level:
                return {"ok": True, "skipped": True, "reason": "already_sent", "key": key, "level": level}
        except (json.JSONDecodeError, OSError):
            pass

    notified = False
    try:
        _adb(["shell", "cmd", "notification", "post", "-t", "timeless_halt", title, body])
        notified = True
    except Exception:
        pass

    if level >= 2:
        try:
            _adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url])
            notified = True
        except Exception:
            pass

    if level >= 3:
        try:
            _adb(["shell", "input", "keyevent", "224"])
        except Exception:
            pass
        try:
            _adb(["shell", "service", "call", "audio", "3", "i32", "3", "i32", "15", "i32", "1"])
        except Exception:
            pass
        try:
            _adb(["shell", "cmd", "notification", "post", "-t", "timeless_halt_alarm", title, body])
            notified = True
        except Exception:
            pass

    if not notified:
        raise RuntimeError("could not reach phone")

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(
            {
                "key": key,
                "level": level,
                "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "url": url,
            }
        ),
        encoding="utf-8",
    )
    return {"ok": True, "url": url, "key": key, "level": level}


def escalate_halt(halt: dict[str, Any], quiet: dict[str, Any] | None) -> dict[str, Any]:
    if quiet and blocks_phone(quiet.get("level", "")):
        return {"ok": True, "skipped": True, "reason": "quiet"}

    key = halt_alert_key(halt)
    now = datetime.now(timezone.utc)
    now_s = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    state = _load_escalations()
    entry = state.get(key)
    if not entry:
        entry = {"level": 0, "first_seen": now_s, "last_fired": None}
        state[key] = entry

    first = datetime.fromisoformat(entry["first_seen"].replace("Z", "+00:00"))
    if first.tzinfo is None:
        first = first.replace(tzinfo=timezone.utc)
    elapsed = (now - first.astimezone(timezone.utc)).total_seconds()
    fired = int(entry.get("level") or 0)
    target = 0
    for lvl, at in sorted(LEVEL_AT.items()):
        if elapsed >= at and fired < lvl:
            target = lvl
            break

    if target == 0:
        _save_escalations(state)
        return {"ok": True, "skipped": True, "reason": "not_due", "elapsed": int(elapsed), "fired": fired}

    out = notify_halt(halt, level=target, force=target >= 3)
    entry["level"] = target
    entry["last_fired"] = now_s
    state[key] = entry
    _save_escalations(state)
    out["escalation"] = target
    return out
