#!/usr/bin/env python3
"""Forward recent screenpipe OCR/accessibility text into Timeless."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request

SP = os.environ.get(
    "SCREENPIPE_BIN",
    os.path.expanduser("~/Library/Application Support/Timeless/bin/screenpipe"),
)
TIMLESS = os.environ.get("TIMELESS_URL", "http://127.0.0.1:8787")


def post(url: str, payload: dict) -> None:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        r.read()


def search(content_type: str) -> list:
    if not os.path.isfile(SP):
        print(f"screenpipe binary missing: {SP}")
        return []
    proc = subprocess.run(
        [
            SP,
            "search",
            "--json",
            "--content-type",
            content_type,
            "--start",
            "12m ago",
            "--limit",
            "25",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        print((proc.stderr or proc.stdout or "search failed").strip()[:400])
        return []
    rows = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def text_of(item: dict) -> tuple[str, str | None]:
    for key in ("ocr", "accessibility", "content", "text"):
        block = item.get(key)
        if isinstance(block, dict):
            text = str(block.get("text") or block.get("content") or "")
            url = block.get("browser_url") or block.get("url")
            if text:
                return text, url
        if isinstance(block, str) and block.strip():
            return block, item.get("browser_url")
    text = str(item.get("text") or "")
    return text, item.get("browser_url") or item.get("url")


def main() -> None:
    rows = search("ocr") + search("accessibility")
    if not rows:
        try:
            post(f"{TIMLESS}/api/heartbeat", {"sensor": "mac_screenpipe", "detail": "no rows yet"})
        except Exception as exc:
            print(f"heartbeat failed: {exc}")
        return
    forwarded = 0
    for item in rows:
        text, url = text_of(item)
        if len(text.strip()) < 8:
            continue
        try:
            post(f"{TIMLESS}/api/ingest/screen", {"text": text[:4000], "url": url})
            forwarded += 1
        except Exception as exc:
            print(f"ingest failed: {exc}")
            break
    try:
        post(f"{TIMLESS}/api/heartbeat", {"sensor": "mac_screenpipe", "detail": f"forwarded {forwarded}"})
    except Exception as exc:
        print(f"heartbeat failed: {exc}")
    print(f"forwarded {forwarded} screenpipe rows")


if __name__ == "__main__":
    main()
