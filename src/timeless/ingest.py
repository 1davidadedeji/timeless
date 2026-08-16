from __future__ import annotations

from urllib.parse import urlparse

JOB_HOST_MARKERS = (
    "greenhouse.io",
    "lever.co",
    "myworkdayjobs.com",
    "workday.com",
    "ashbyhq.com",
    "icims.com",
    "smartrecruiters.com",
    "jobvite.com",
    "taleo.net",
    "boards.eu.greenhouse.io",
    "linkedin.com/jobs",
    "indeed.com",
    "wellfound.com",
    "glassdoor.com",
    "careers.",
    "/careers",
    "/jobs/",
)

CONFIRMATION_PHRASES = (
    "thank you for applying",
    "application received",
    "application submitted",
    "we have received your application",
    "successfully applied",
)

REQUIREMENT_MISS_PHRASES = (
    "years of experience required",
    "must have",
    "you do not meet",
    "minimum qualifications",
    "not eligible",
)


def looks_like_job_url(url: str) -> bool:
    raw = (url or "").lower()
    if not raw.startswith("http"):
        return False
    return any(marker in raw for marker in JOB_HOST_MARKERS)


def host_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def classify_screen_text(text: str) -> str | None:
    blob = (text or "").lower()
    if any(p in blob for p in CONFIRMATION_PHRASES):
        return "confirmation"
    if any(p in blob for p in REQUIREMENT_MISS_PHRASES):
        return "requirement_miss"
    return None
