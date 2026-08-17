from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def zone() -> ZoneInfo:
    return ZoneInfo(os.environ.get("TIMELESS_TZ", "America/Chicago"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_now(now: datetime | None = None) -> datetime:
    return (now or utc_now()).astimezone(zone())


def day_key(now: datetime | None = None) -> str:
    return local_now(now).strftime("%Y-%m-%d")


def recap_window_open(now: datetime | None = None) -> bool:
    loc = local_now(now)
    return loc.hour > 23 or (loc.hour == 23 and loc.minute >= 55)


def due_recap_day(now: datetime | None = None) -> str:
    loc = local_now(now)
    if recap_window_open(now):
        return loc.strftime("%Y-%m-%d")
    return (loc - timedelta(days=1)).strftime("%Y-%m-%d")
