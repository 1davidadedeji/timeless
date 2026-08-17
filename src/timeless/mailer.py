from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from timeless.classify_event import CONF_RE, HACK_RE

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
ISO = re.compile(r"\b(20\d{2}-\d{2}-\d{2})(?:[ T](\d{1,2}):(\d{2}))?")
NAMED = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+(\d{1,2})(?:,?\s*(20\d{2}))?",
    re.I,
)
URL_RE = re.compile(r"https?://[^\s>]+", re.I)


def classify_subject(subject: str, sender: str = "") -> str:
    blob = f"{subject} {sender}"
    low = blob.lower()
    if any(w in low for w in ("unsubscribe", "newsletter", "noreply+", "digest")):
        return "ignore"
    if HACK_RE.search(blob):
        return "hackathon"
    if CONF_RE.search(blob):
        return "conference"
    if "interview" in low:
        return "interview"
    if any(w in low for w in ("unfortunately", "not moving forward", "rejected")):
        return "rejection"
    if any(w in low for w in ("application", "apply", "greenhouse", "lever.co", "workday")):
        return "job"
    if any(w in low for w in ("action required", "verify your", "complete your")):
        return "reply-needed"
    if re.search(r"\bre:|\bfwd:", low):
        return "reply-needed"
    return "other"


def program_kind(classification: str) -> str | None:
    return {
        "hackathon": "hackathon",
        "conference": "conference",
        "job": "internship",
        "interview": "internship",
        "rejection": "internship",
    }.get(classification)


def first_url(text: str) -> str | None:
    m = URL_RE.search(text or "")
    return m.group(0).rstrip(").,") if m else None


def parse_when(text: str, now: datetime | None = None) -> datetime | None:
    now = now or datetime.now(timezone.utc)
    blob = text or ""
    m = ISO.search(blob)
    if m:
        day = datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if m.group(2):
            day = day.replace(hour=int(m.group(2)), minute=int(m.group(3)))
        else:
            day = day.replace(hour=9)
        return day
    m = NAMED.search(blob)
    if not m:
        return None
    key = m.group(1).lower()
    month = MONTHS.get(key) or MONTHS.get(key[:3])
    if not month:
        return None
    year = int(m.group(3) or now.year)
    day = datetime(year, month, int(m.group(2)), 9, 0, tzinfo=timezone.utc)
    if day < now - timedelta(days=30) and not m.group(3):
        day = day.replace(year=now.year + 1)
    return day
