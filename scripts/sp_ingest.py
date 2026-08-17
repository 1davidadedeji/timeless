#!/usr/bin/env python3
"""Forward recent screenpipe OCR via the local HTTP API (CLI search locks the DB)."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.parse
import urllib.request

SP = os.environ.get(
    "SCREENPIPE_BIN",
    os.path.expanduser("~/Library/Application Support/Timeless/bin/screenpipe"),
)
API = os.environ.get("SCREENPIPE_URL", "http://127.0.0.1:3030")
TIMLESS = os.environ.get("TIMELESS_URL", "http://127.0.0.1:8787")


def post(url: str, payload: dict) -> None:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        r.read()


def api_key() -> str:
    env = os.environ.get("SCREENPIPE_API_KEY", "").strip()
    if env:
        return env
    if not os.path.isfile(SP):
        return ""
    try:
        out = subprocess.check_output([SP, "auth", "token"], text=True, timeout=8)
    except Exception:
        return ""
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def search(content_type: str) -> list:
    key = api_key()
    q = urllib.parse.urlencode({"limit": 25, "content_type": content_type, "start": "12m ago"})
    req = urllib.request.Request(f"{API}/search?{q}")
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            body = json.loads(r.read().decode())
    except Exception as exc:
        print(f"screenpipe search failed: {exc}")
        return []
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for k in ("data", "items", "results"):
            if isinstance(body.get(k), list):
                return body[k]
    return []


def text_of(item: dict) -> tuple[str, str | None]:
    content = item.get("content") if isinstance(item.get("content"), dict) else item
    if not isinstance(content, dict):
        content = item
    for key in ("ocr", "accessibility", "content", "text"):
        block = content.get(key) if isinstance(content, dict) else None
        if isinstance(block, dict):
            text = str(block.get("text") or block.get("content") or "")
            url = block.get("browser_url") or block.get("url")
            if text:
                return text, url
        if isinstance(block, str) and block.strip():
            return block, content.get("browser_url") if isinstance(content, dict) else None
    text = str((content or {}).get("text") or item.get("text") or "")
    url = None
    if isinstance(content, dict):
        url = content.get("browser_url") or content.get("url")
    return text, url or item.get("browser_url") or item.get("url")


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
        if not isinstance(item, dict):
            continue
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
