from __future__ import annotations

import random

LINES = (
    "That's a real check off the list. Keep the streak honest.",
    "Done is done. Timeless saw it.",
    "You said you would. You did.",
    "One block finished. The rest of the day is still yours to keep.",
    "Logged. That's the kind of follow-through the morning gate is for.",
)


def praise_for(name: str) -> str:
    line = random.choice(LINES)
    label = (name or "that block").strip()
    return f"{label}: {line}"
