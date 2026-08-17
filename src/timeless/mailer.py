from __future__ import annotations

import re


def classify_subject(subject: str, sender: str = "") -> str:
    blob = f"{subject} {sender}".lower()
    if any(w in blob for w in ("unsubscribe", "newsletter", "noreply+", "digest")):
        return "ignore"
    if "interview" in blob:
        return "interview"
    if any(w in blob for w in ("unfortunately", "not moving forward", "rejected")):
        return "rejection"
    if any(w in blob for w in ("application", "apply", "greenhouse", "lever.co", "workday")):
        return "job"
    if any(w in blob for w in ("action required", "verify your", "complete your")):
        return "reply-needed"
    if re.search(r"\bre:|\bfwd:", blob):
        return "reply-needed"
    return "other"
