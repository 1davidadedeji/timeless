from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from timeless.clock import due_recap_day
from timeless.store import Store

ROOT = Path(__file__).resolve().parents[2]
PHONE_PULL = ROOT / "scripts" / "phone_aw_pull.sh"


def pull_phone(timeout: int = 25) -> bool:
    if not PHONE_PULL.exists():
        return False
    try:
        subprocess.run(
            ["/bin/bash", str(PHONE_PULL)],
            check=False,
            timeout=timeout,
            capture_output=True,
            env={**os.environ},
        )
        return True
    except Exception:
        return False


def build_cards(store: Store, day: str, phone_synced: bool) -> list[dict[str, str]]:
    events = store.events_on_day(day)
    plan = store.get_plan(day)
    mac = [e for e in events if e["source"] in {"url", "screen"}]
    phone = [e for e in events if e["source"] == "phone"]
    jobs = [e for e in mac if "http" in (e.get("summary") or "")]
    opps = [o for o in store.list_opportunities() if (o.get("updated_at") or o.get("created_at") or "").startswith(day)]
    top: dict[str, int] = {}
    for e in events:
        label = (e.get("summary") or e["source"])[:80]
        top[label] = top.get(label, 0) + 1
    ranked = sorted(top.items(), key=lambda kv: -kv[1])[:3]
    top_line = " · ".join(f"{n}× {name}" for name, n in ranked) or "Quiet machines."
    cards = [
        {"kicker": "Admit one", "title": day, "stat": "Chicago", "body": "Your day, closed."},
        {
            "kicker": "The work",
            "title": "Hours on the work",
            "stat": str(len(events)),
            "body": (plan or {}).get("outcomes") or "No plan was locked.",
        },
        {"kicker": "Mac", "title": "What held the screen", "stat": str(len(mac)), "body": top_line},
        {
            "kicker": "Phone",
            "title": "In the hand",
            "stat": str(len(phone)),
            "body": "Synced." if phone_synced else "Phone did not sync. Deck is Mac-only.",
        },
        {
            "kicker": "Jobs",
            "title": "Opened, not necessarily sent",
            "stat": str(len(opps) or len(jobs)),
            "body": ", ".join((o.get("role") or o.get("url") or "")[:40] for o in opps[:4]) or "No postings tagged.",
        },
        {
            "kicker": "Gaps",
            "title": "Misses",
            "stat": "—",
            "body": "Meetings and mail join this card once those ingest.",
        },
    ]
    return cards


def ensure_recap(store: Store, now=None, do_pull: bool = True) -> dict[str, Any]:
    day = due_recap_day(now)
    existing = store.get_recap(day)
    if existing and existing.get("acked_at"):
        return existing
    if existing and existing.get("cards"):
        return existing
    synced = pull_phone() if do_pull else False
    cards = build_cards(store, day, synced)
    return store.save_recap(day, cards, synced)
