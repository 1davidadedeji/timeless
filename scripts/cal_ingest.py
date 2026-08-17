#!/usr/bin/env python3
"""Push Calendar.app events into Timeless meetings."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import httpx

BIN = Path.home() / "Library/Application Support/Timeless/bin/TimelessCal"
TIMLESS = os.environ.get("TIMELESS_URL", "http://127.0.0.1:8787")


def to_z(value: str) -> str:
    raw = (value or "").replace("Z", "+00:00")
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    if not BIN.exists():
        print("TimelessCal missing; run scripts/build-cal.sh")
        return
    raw = subprocess.check_output([str(BIN)], timeout=20)
    rows = json.loads(raw.decode() or "[]")
    n = 0
    with httpx.Client(timeout=10) as client:
        client.post(f"{TIMLESS}/api/heartbeat", json={"sensor": "mac_cal", "detail": f"{len(rows)} events"})
        for row in rows:
            row["start_at"] = to_z(row["start_at"])
            row["end_at"] = to_z(row["end_at"])
            for key in ("join_url", "location", "notes"):
                if not row.get(key):
                    row[key] = None
            client.post(f"{TIMLESS}/api/meetings", json=row)
            n += 1
    print(f"upserted {n} meetings")


if __name__ == "__main__":
    main()
