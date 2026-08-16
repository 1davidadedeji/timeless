#!/usr/bin/env python3
"""Forward ActivityWatch web/window URLs into Timeless."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

AW = os.environ.get("AW_URL", "http://127.0.0.1:5600")
TIMLESS = os.environ.get("TIMELESS_URL", "http://127.0.0.1:8787")


def get(url: str):
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.load(r)


def post(url: str, payload: dict) -> None:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        r.read()


def events_for(bucket: str, start: datetime) -> list:
    start_s = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_s = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        return get(f"{AW}/api/0/buckets/{bucket}/events?start={start_s}&end={end_s}&limit=80")
    except urllib.error.HTTPError:
        return []


def main() -> None:
    since = datetime.now(timezone.utc) - timedelta(minutes=20)
    try:
        bmap = get(f"{AW}/api/0/buckets")
    except Exception as exc:
        print(f"activitywatch unreachable: {exc}")
        return
    post(f"{TIMLESS}/api/heartbeat", {"sensor": "mac_aw", "detail": f"{len(bmap)} buckets"})
    forwarded = 0
    for bid, meta in bmap.items():
        btype = str((meta or {}).get("type") or "")
        name = bid.lower() + " " + btype.lower()
        if "android" in name:
            post(f"{TIMLESS}/api/heartbeat", {"sensor": "phone_aw", "detail": bid})
            continue
        if not any(k in name for k in ("web", "window", "currentwindow", "browser")):
            continue
        for ev in events_for(bid, since):
            data = ev.get("data") or {}
            url = data.get("url") or ""
            title = data.get("title") or data.get("app") or ""
            if not url:
                continue
            try:
                post(f"{TIMLESS}/api/ingest/url", {"url": url, "title": title})
                forwarded += 1
            except Exception as exc:
                print(f"ingest failed: {exc}")
    print(f"forwarded {forwarded} url events")


if __name__ == "__main__":
    main()
