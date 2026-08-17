from __future__ import annotations

import re

JOIN_RE = re.compile(r"zoom\.us|meet\.google|teams\.microsoft|webex\.com|gotomeeting", re.I)
HACK_RE = re.compile(r"hackathon|\bctf\b|devfest|hack night", re.I)
CONF_RE = re.compile(r"conference|summit|symposium|\bmeetup\b", re.I)
SUBMIT_RE = re.compile(r"deadline|submit by|applications? close|submission", re.I)
PRESENT_RE = re.compile(r"\bdemo\b|\bpitch\b|presentation|judging", re.I)


def classify_event(title: str, join_url: str | None, location: str | None, notes: str | None = None) -> tuple[str, str]:
    blob = " ".join(x for x in (title, notes, location, join_url) if x)
    kind = "meeting"
    if HACK_RE.search(blob):
        kind = "hackathon"
    elif CONF_RE.search(blob):
        kind = "conference"
    if join_url or JOIN_RE.search(blob):
        modality = "virtual"
    elif (location or "").strip():
        modality = "physical"
    else:
        modality = "virtual"
    return kind, modality


def looks_like_submission(title: str, notes: str | None = None) -> bool:
    return bool(SUBMIT_RE.search(" ".join(x for x in (title, notes) if x)))


def looks_like_presentation(title: str, notes: str | None = None) -> bool:
    return bool(PRESENT_RE.search(" ".join(x for x in (title, notes) if x)))
