from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from timeless.db import connect
from timeless.ingest import classify_screen_text, looks_like_job_url
from timeless.praise import praise_for

VALID_STATES = frozenset({"seen", "applied", "skipped", "waiting", "ignored"})
MEETING_ACKS = frozenset({"join", "im_in"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def _day(dt: datetime | None = None) -> str:
    return (dt or _now()).strftime("%Y-%m-%d")


def row_to_dict(row) -> dict[str, Any]:
    return dict(row) if row is not None else {}


class Store:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = connect(db_path)

    def close(self) -> None:
        self.conn.close()

    def heartbeat(self, sensor: str, detail: str | None = None) -> None:
        self.conn.execute(
            """
            INSERT INTO heartbeats(sensor, last_seen, detail) VALUES (?, ?, ?)
            ON CONFLICT(sensor) DO UPDATE SET last_seen=excluded.last_seen, detail=excluded.detail
            """,
            (sensor, _iso(), detail),
        )
        self.conn.commit()

    def heartbeats(self) -> list[dict[str, Any]]:
        return [row_to_dict(r) for r in self.conn.execute("SELECT * FROM heartbeats ORDER BY sensor")]

    def add_event(self, source: str, summary: str, payload: dict | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO events(source, ts, summary, payload) VALUES (?, ?, ?, ?)",
            (source, _iso(), summary, json.dumps(payload or {})),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def latest_event_age_seconds(self) -> float | None:
        row = self.conn.execute("SELECT ts FROM events ORDER BY ts DESC LIMIT 1").fetchone()
        if not row:
            return None
        ts = datetime.strptime(row["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return (_now() - ts).total_seconds()

    def save_plan(self, outcomes: str, timeline: list[dict], day: str | None = None) -> dict[str, Any]:
        outcomes = (outcomes or "").strip()
        if not outcomes:
            raise ValueError("outcomes required")
        if not timeline:
            raise ValueError("timeline required")
        for block in timeline:
            if not str(block.get("task") or "").strip():
                raise ValueError("each block needs a task")
        day = day or _day()
        now = _iso()
        payload = json.dumps(timeline)
        existing = self.conn.execute("SELECT id FROM daily_plans WHERE day=?", (day,)).fetchone()
        if existing:
            self.conn.execute(
                "UPDATE daily_plans SET outcomes=?, timeline=?, updated_at=? WHERE day=?",
                (outcomes, payload, now, day),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO daily_plans(day, outcomes, timeline, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (day, outcomes, payload, now, now),
            )
        self.conn.commit()
        return self.get_plan(day)

    def get_plan(self, day: str | None = None) -> dict[str, Any] | None:
        day = day or _day()
        row = self.conn.execute("SELECT * FROM daily_plans WHERE day=?", (day,)).fetchone()
        if not row:
            return None
        data = row_to_dict(row)
        data["timeline"] = json.loads(data["timeline"])
        return data

    def add_ritual(
        self,
        name: str,
        launch_url: str | None = None,
        app_bundle: str | None = None,
        weekdays: str = "1,2,3,4,5",
        match_host: str | None = None,
        min_minutes: int | None = None,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO rituals(name, launch_url, app_bundle, weekdays, match_host, min_minutes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, launch_url, app_bundle, weekdays, match_host, min_minutes),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_rituals(self) -> list[dict[str, Any]]:
        return [row_to_dict(r) for r in self.conn.execute("SELECT * FROM rituals ORDER BY id")]

    def complete_ritual(self, ritual_id: int, day: str | None = None) -> dict[str, Any]:
        day = day or _day()
        ritual = self.conn.execute("SELECT * FROM rituals WHERE id=?", (ritual_id,)).fetchone()
        if not ritual:
            raise ValueError("unknown ritual")
        praise = praise_for(ritual["name"])
        try:
            self.conn.execute(
                "INSERT INTO ritual_completions(ritual_id, day, praise, created_at) VALUES (?, ?, ?, ?)",
                (ritual_id, day, praise, _iso()),
            )
        except Exception as exc:
            raise ValueError("already completed today") from exc
        self.conn.commit()
        return {"ritual_id": ritual_id, "day": day, "praise": praise}

    def upsert_opportunity(
        self,
        *,
        url: str,
        company: str | None = None,
        role: str | None = None,
        state: str = "seen",
        deadline_at: str | None = None,
        source: str = "url",
    ) -> dict[str, Any]:
        if state not in VALID_STATES:
            raise ValueError("bad state")
        now = _iso()
        row = self.conn.execute("SELECT * FROM opportunities WHERE url=?", (url,)).fetchone()
        if row:
            self.conn.execute(
                """
                UPDATE opportunities SET company=COALESCE(?, company), role=COALESCE(?, role),
                    deadline_at=COALESCE(?, deadline_at), updated_at=?
                WHERE id=?
                """,
                (company, role, deadline_at, now, row["id"]),
            )
            self.conn.commit()
            return row_to_dict(self.conn.execute("SELECT * FROM opportunities WHERE id=?", (row["id"],)).fetchone())
        cur = self.conn.execute(
            """
            INSERT INTO opportunities(company, role, url, state, deadline_at, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (company, role, url, state, deadline_at, source, now, now),
        )
        self.conn.commit()
        return row_to_dict(self.conn.execute("SELECT * FROM opportunities WHERE id=?", (cur.lastrowid,)).fetchone())

    def set_opportunity_state(self, opportunity_id: int, state: str) -> dict[str, Any]:
        if state not in VALID_STATES:
            raise ValueError("bad state")
        self.conn.execute(
            "UPDATE opportunities SET state=?, updated_at=? WHERE id=?",
            (state, _iso(), opportunity_id),
        )
        self.conn.commit()
        row = self.conn.execute("SELECT * FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()
        if not row:
            raise ValueError("unknown opportunity")
        return row_to_dict(row)

    def list_opportunities(self) -> list[dict[str, Any]]:
        return [row_to_dict(r) for r in self.conn.execute("SELECT * FROM opportunities ORDER BY updated_at DESC")]

    def propose(self, kind: str, payload: dict, ttl_days: int = 7) -> dict[str, Any]:
        now = _now()
        cur = self.conn.execute(
            """
            INSERT INTO pending_approvals(kind, payload, status, created_at, expires_at)
            VALUES (?, ?, 'pending', ?, ?)
            """,
            (kind, json.dumps(payload), _iso(now), _iso(now + timedelta(days=ttl_days))),
        )
        self.conn.commit()
        return self.get_approval(int(cur.lastrowid))

    def get_approval(self, approval_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM pending_approvals WHERE id=?", (approval_id,)).fetchone()
        if not row:
            raise ValueError("unknown approval")
        data = row_to_dict(row)
        data["payload"] = json.loads(data["payload"])
        return data

    def list_approvals(self, status: str = "pending") -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM pending_approvals WHERE status=? ORDER BY id",
            (status,),
        )
        out = []
        for row in rows:
            data = row_to_dict(row)
            data["payload"] = json.loads(data["payload"])
            out.append(data)
        return out

    def expire_approvals(self, now: datetime | None = None) -> int:
        now = now or _now()
        cur = self.conn.execute(
            """
            UPDATE pending_approvals SET status='expired'
            WHERE status='pending' AND expires_at <= ?
            """,
            (_iso(now),),
        )
        self.conn.commit()
        return cur.rowcount

    def decide_approval(self, approval_id: int, accept: bool, extra: dict | None = None) -> dict[str, Any]:
        self.expire_approvals()
        row = self.conn.execute("SELECT * FROM pending_approvals WHERE id=?", (approval_id,)).fetchone()
        if not row:
            raise ValueError("unknown approval")
        if row["status"] != "pending":
            raise ValueError("approval not pending")
        payload = json.loads(row["payload"])
        if extra:
            payload.update(extra)
        if accept:
            self._apply_approval(row["kind"], payload)
            status = "accepted"
        else:
            status = "rejected"
        self.conn.execute(
            "UPDATE pending_approvals SET status=?, payload=? WHERE id=?",
            (status, json.dumps(payload), approval_id),
        )
        self.conn.commit()
        return self.get_approval(approval_id)

    def _apply_approval(self, kind: str, payload: dict) -> None:
        if kind in {"mark_applied", "opportunity_applied"}:
            oid = payload.get("opportunity_id")
            if not oid and payload.get("url"):
                opp = self.upsert_opportunity(url=payload["url"], company=payload.get("company"), role=payload.get("role"))
                oid = opp["id"]
            self.set_opportunity_state(int(oid), "applied")
        elif kind in {"mark_skipped", "opportunity_skip"}:
            oid = payload["opportunity_id"]
            self.set_opportunity_state(int(oid), "skipped")
        elif kind == "keep_seen":
            oid = payload["opportunity_id"]
            self.set_opportunity_state(int(oid), "seen")
        elif kind == "pin_ritual":
            self.add_ritual(
                name=payload["name"],
                launch_url=payload.get("launch_url"),
                match_host=payload.get("match_host"),
            )

    def ingest_url(self, url: str, title: str | None = None) -> dict[str, Any]:
        self.add_event("url", title or url, {"url": url, "title": title})
        self.heartbeat("mac_browser", url)
        if not looks_like_job_url(url):
            return {"job": False, "url": url}
        company = title or url
        opp = self.upsert_opportunity(url=url, role=title, company=None, source="url")
        return {"job": True, "opportunity": opp, "company": company}

    def ingest_screen_text(self, text: str, url: str | None = None) -> dict[str, Any]:
        kind = classify_screen_text(text)
        self.add_event("screen", (text or "")[:200], {"url": url, "kind": kind})
        if not kind:
            return {"kind": None}
        if url:
            opp = self.upsert_opportunity(url=url, source="screen")
        else:
            opp = None
        if kind == "confirmation":
            approval = self.propose(
                "mark_applied",
                {"opportunity_id": opp["id"] if opp else None, "url": url, "snippet": text[:280]},
            )
            return {"kind": kind, "approval": approval}
        if kind == "requirement_miss":
            approval = self.propose(
                "opportunity_skip",
                {
                    "opportunity_id": opp["id"] if opp else None,
                    "url": url,
                    "snippet": text[:280],
                    "prompt": "skip (don't remind), keep as seen (reapply later), or reject to ignore",
                },
            )
            return {"kind": kind, "approval": approval}
        return {"kind": kind}

    def ingest_phone(self, summary: str, payload: dict | None = None) -> int:
        self.heartbeat("phone_a11y", summary)
        return self.add_event("phone", summary, payload)

    def add_mail_action(self, message_id: str, account: str, subject: str, classification: str, card: str) -> dict[str, Any]:
        existing = self.conn.execute("SELECT * FROM mail_actions WHERE message_id=?", (message_id,)).fetchone()
        if existing:
            return row_to_dict(existing)
        cur = self.conn.execute(
            """
            INSERT INTO mail_actions(message_id, account, subject, classification, card, status)
            VALUES (?, ?, ?, ?, ?, 'open')
            """,
            (message_id, account, subject, classification, card),
        )
        self.conn.commit()
        return row_to_dict(self.conn.execute("SELECT * FROM mail_actions WHERE id=?", (cur.lastrowid,)).fetchone())

    def list_mail_actions(self, status: str = "open") -> list[dict[str, Any]]:
        return [
            row_to_dict(r)
            for r in self.conn.execute("SELECT * FROM mail_actions WHERE status=? ORDER BY id DESC", (status,))
        ]

    def upsert_meeting(
        self,
        uid: str,
        title: str,
        start_at: str,
        end_at: str,
        join_url: str | None = None,
    ) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT INTO meetings(uid, title, start_at, end_at, join_url, ack, acked_at)
            VALUES (?, ?, ?, ?, ?, NULL, NULL)
            ON CONFLICT(uid) DO UPDATE SET
                title=excluded.title, start_at=excluded.start_at, end_at=excluded.end_at,
                join_url=excluded.join_url
            """,
            (uid, title, start_at, end_at, join_url),
        )
        self.conn.commit()
        return row_to_dict(self.conn.execute("SELECT * FROM meetings WHERE uid=?", (uid,)).fetchone())

    def ack_meeting(self, meeting_id: int, action: str) -> dict[str, Any]:
        if action not in MEETING_ACKS:
            raise ValueError("action must be join or im_in")
        row = self.conn.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone()
        if not row:
            raise ValueError("unknown meeting")
        self.conn.execute(
            "UPDATE meetings SET ack=?, acked_at=? WHERE id=?",
            (action, _iso(), meeting_id),
        )
        self.conn.commit()
        return row_to_dict(self.conn.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone())

    def close_elapsed_meetings(self, now: datetime | None = None) -> int:
        now_s = _iso(now or _now())
        cur = self.conn.execute(
            """
            UPDATE meetings SET ack='missed'
            WHERE ack IS NULL AND end_at <= ?
            """,
            (now_s,),
        )
        self.conn.commit()
        return cur.rowcount

    def active_halt(self, now: datetime | None = None) -> dict[str, Any] | None:
        self.close_elapsed_meetings(now)
        now_s = _iso(now or _now())
        row = self.conn.execute(
            """
            SELECT * FROM meetings
            WHERE ack IS NULL AND start_at <= ? AND end_at > ?
            ORDER BY start_at LIMIT 1
            """,
            (now_s, now_s),
        ).fetchone()
        return row_to_dict(row) if row else None

    def list_meetings(self) -> list[dict[str, Any]]:
        return [row_to_dict(r) for r in self.conn.execute("SELECT * FROM meetings ORDER BY start_at")]

    def needs_gate(self, day: str | None = None) -> bool:
        return self.get_plan(day) is None
