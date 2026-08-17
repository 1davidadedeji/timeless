#!/usr/bin/env python3
"""Unread Mail.app subjects → Timeless mail cards. Does not send."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from timeless.mailer import classify_subject

TIMLESS = os.environ.get("TIMELESS_URL", "http://127.0.0.1:8787")

SCRIPT = r'''
tell application "Mail"
  set out to ""
  try
    set theMsgs to (messages of inbox whose read status is false)
    set lim to 40
    if (count of theMsgs) < lim then set lim to (count of theMsgs)
    repeat with i from 1 to lim
      set m to item i of theMsgs
      set out to out & (id of m as text) & tab & (subject of m) & tab & (sender of m) & linefeed
    end repeat
  end try
  return out
end tell
'''


def main() -> None:
    try:
        raw = subprocess.check_output(["osascript", "-e", SCRIPT], timeout=30, stderr=subprocess.DEVNULL)
    except Exception as exc:
        with httpx.Client(timeout=10) as client:
            client.post(f"{TIMLESS}/api/heartbeat", json={"sensor": "mac_mail", "detail": f"mail.app: {exc}"})
        print(f"mail.app unavailable: {exc}")
        return
    lines = raw.decode("utf-8", "replace").strip().splitlines()
    added = 0
    ignored = 0
    with httpx.Client(timeout=10) as client:
        client.post(f"{TIMLESS}/api/heartbeat", json={"sensor": "mac_mail", "detail": f"{len(lines)} unread scanned"})
        for line in lines:
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            mid, subject = parts[0], parts[1]
            sender = parts[2] if len(parts) > 2 else ""
            kind = classify_subject(subject, sender)
            if kind == "ignore":
                ignored += 1
                continue
            client.post(
                f"{TIMLESS}/api/mail",
                json={
                    "message_id": f"mailapp:{mid}",
                    "account": "mail.app",
                    "subject": subject,
                    "classification": kind,
                    "card": subject,
                },
            )
            added += 1
    print(f"mail cards {added}, ignored {ignored}")


if __name__ == "__main__":
    main()
