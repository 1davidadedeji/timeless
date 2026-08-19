#!/usr/bin/env python3
"""Escalate unacked halts to the phone on a timed ladder."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from timeless.access import ui_token  # noqa: E402
from timeless.phone_notify import clear_escalation_state, escalate_halt  # noqa: E402

TIMELESS_URL = os.environ.get("TIMELESS_URL", "http://127.0.0.1:8787").rstrip("/")


def fetch_today() -> dict:
    token = ui_token()
    req = urllib.request.Request(
        f"{TIMELESS_URL}/api/today",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    try:
        today = fetch_today()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"brain unreachable: {exc}")
        return 0
    halt = today.get("halt")
    if not halt:
        clear_escalation_state()
        print("no halt")
        return 0
    try:
        out = escalate_halt(halt, today.get("quiet"))
        print(json.dumps(out))
        return 0
    except Exception as exc:
        print(f"escalation skipped: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
