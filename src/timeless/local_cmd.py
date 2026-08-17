from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from timeless.clock import local_now

WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

PLAN_OUT = re.compile(r"^plan\s+outcomes?:\s*(.+)$", re.I)
ADD_BLOCK = re.compile(r"^add\s+block\s+(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s+(.+)$", re.I)
ADD_EVENT = re.compile(
    r"^add\s+event\s+(.+?)\s+(\d{4}-\d{2}-\d{2}|today|tomorrow|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"\s+(\d{1,2}:\d{2})(?:\s*-\s*(\d{1,2}:\d{2}))?(?:\s+(https://\S+))?\s*$",
    re.I,
)
MARK = re.compile(
    r"^mark\s+(.+?)\s+(applied|shortlisted|interview|waiting|offer|rejected|skipped|seen|ignored)\s*$",
    re.I,
)
EVENT_MOD = re.compile(r"^event\s+(.+?)\s+is\s+(virtual|physical)\s*$", re.I)
EVENT_JOIN = re.compile(r"^event\s+(.+?)\s+(https://\S+)\s*$", re.I)


def parse_local(message: str) -> dict[str, Any] | None:
    raw = (message or "").strip()
    if not raw:
        return None
    m = PLAN_OUT.match(raw)
    if m:
        return {"action": "plan_outcomes", "outcomes": m.group(1).strip()}
    m = ADD_BLOCK.match(raw)
    if m:
        return {"action": "add_block", "start": m.group(1), "end": m.group(2), "task": m.group(3).strip()}
    m = ADD_EVENT.match(raw)
    if m:
        end_hm = m.group(4) or _plus_hour(m.group(3))
        start_at, end_at = _range(m.group(2), m.group(3), end_hm)
        return {
            "action": "add_event",
            "title": m.group(1).strip(),
            "start_at": start_at,
            "end_at": end_at,
            "join_url": (m.group(5) or "").rstrip(").,") or None,
        }
    m = MARK.match(raw)
    if m:
        return {"action": "mark_program", "query": m.group(1).strip(), "state": m.group(2).lower()}
    m = EVENT_MOD.match(raw)
    if m:
        return {"action": "event_modality", "query": m.group(1).strip(), "modality": m.group(2).lower()}
    m = EVENT_JOIN.match(raw)
    if m:
        return {"action": "event_join", "query": m.group(1).strip(), "join_url": m.group(2).rstrip(").,")}
    return None


def _plus_hour(hm: str) -> str:
    h, mi = hm.split(":")
    t = (int(h) * 60 + int(mi) + 60) % (24 * 60)
    return f"{t // 60:02d}:{t % 60:02d}"


def _hm(token: str) -> tuple[int, int]:
    h, m = token.split(":")
    return int(h), int(m)


def _range(day_token: str, start_hm: str, end_hm: str) -> tuple[str, str]:
    loc = local_now()
    key = day_token.lower()
    sh, sm = _hm(start_hm)
    eh, em = _hm(end_hm)
    if re.match(r"\d{4}-\d{2}-\d{2}", key):
        base = datetime.strptime(key, "%Y-%m-%d").replace(tzinfo=loc.tzinfo)
        day = base.date()
    elif key == "today":
        day = loc.date()
    elif key == "tomorrow":
        day = (loc + timedelta(days=1)).date()
    else:
        wd = WEEKDAYS[key]
        delta = (wd - loc.weekday()) % 7
        day = (loc + timedelta(days=delta)).date()
    start = datetime(day.year, day.month, day.day, sh, sm, tzinfo=loc.tzinfo)
    end = datetime(day.year, day.month, day.day, eh, em, tzinfo=loc.tzinfo)
    if end <= start:
        end = end + timedelta(hours=1)
    return (
        start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def apply_local(store: Any, intent: dict[str, Any], create_cal) -> dict[str, Any]:
    action = intent["action"]
    if action == "plan_outcomes":
        plan = store.get_plan()
        if not plan:
            raise ValueError("no plan locked for today")
        store.save_plan(intent["outcomes"], plan["timeline"])
        return {"reply": f"Outcomes set: {intent['outcomes']}.", "did": {"action": action}}
    if action == "add_block":
        plan = store.get_plan()
        if not plan:
            raise ValueError("no plan locked for today")
        tl = list(plan["timeline"])
        tl.append({"start": intent["start"], "end": intent["end"], "task": intent["task"]})
        store.save_plan(plan["outcomes"], tl)
        return {"reply": f"Added {intent['start']}–{intent['end']} {intent['task']}.", "did": {"action": action}}
    if action == "add_event":
        uid = f"chat:{intent['title']}:{intent['start_at']}"
        row = store.upsert_meeting(
            uid,
            intent["title"],
            intent["start_at"],
            intent["end_at"],
            intent.get("join_url"),
        )
        cal = create_cal(
            title=intent["title"],
            start_at=intent["start_at"],
            end_at=intent["end_at"],
            join_url=intent.get("join_url"),
        )
        extra = "" if cal.get("ok") else f" Calendar.app: {cal.get('error')}."
        return {"reply": f"Added event {intent['title']}.{extra}".strip(), "did": {"action": action, "meeting": row, "calendar": cal}}
    if action == "mark_program":
        opp = _find_opp(store, intent["query"])
        if not opp:
            raise ValueError(f"no program matching {intent['query']}")
        store.set_opportunity_state(opp["id"], intent["state"])
        return {"reply": f"Marked {opp.get('role') or opp['url']} {intent['state']}.", "did": {"action": action}}
    if action == "event_modality":
        meeting = _find_meeting(store, intent["query"])
        if not meeting:
            raise ValueError(f"no event matching {intent['query']}")
        store.patch_meeting(meeting["id"], modality=intent["modality"])
        return {"reply": f"{meeting['title']} is {intent['modality']}.", "did": {"action": action}}
    if action == "event_join":
        meeting = _find_meeting(store, intent["query"])
        if not meeting:
            raise ValueError(f"no event matching {intent['query']}")
        store.patch_meeting(meeting["id"], join_url=intent["join_url"])
        return {"reply": f"Join link saved for {meeting['title']}.", "did": {"action": action}}
    raise ValueError("unknown local action")


def _find_opp(store, query: str):
    q = query.lower()
    for o in store.list_opportunities():
        if q in (o.get("role") or "").lower() or q in (o.get("url") or "").lower():
            return o
    return None


def _find_meeting(store, query: str):
    q = query.lower()
    for m in store.list_meetings():
        if q in (m.get("title") or "").lower():
            return m
    return None
