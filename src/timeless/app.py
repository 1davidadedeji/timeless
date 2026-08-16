from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from timeless.store import Store

WEB = Path(__file__).resolve().parents[2] / "web"
DEFAULT_DB = Path.home() / "Library" / "Application Support" / "Timeless" / "timeless.db"


class PlanIn(BaseModel):
    outcomes: str
    timeline: list[dict] = Field(min_length=1)


class RitualIn(BaseModel):
    name: str
    launch_url: str | None = None
    app_bundle: str | None = None
    weekdays: str = "1,2,3,4,5"
    match_host: str | None = None
    min_minutes: int | None = None


class MeetingIn(BaseModel):
    uid: str
    title: str
    start_at: str
    end_at: str
    join_url: str | None = None


class AckIn(BaseModel):
    action: str


class UrlIn(BaseModel):
    url: str
    title: str | None = None


class ScreenIn(BaseModel):
    text: str
    url: str | None = None


class PhoneIn(BaseModel):
    summary: str
    payload: dict | None = None


class MailIn(BaseModel):
    message_id: str
    account: str
    subject: str
    classification: str
    card: str


class ChatIn(BaseModel):
    message: str


class HeartbeatIn(BaseModel):
    sensor: str
    detail: str | None = None


def create_app(db_path: str | None = None) -> FastAPI:
    db_path = db_path or os.environ.get("TIMELESS_DB", str(DEFAULT_DB))
    store = Store(db_path)
    app = FastAPI(title="Timeless")
    app.state.store = store

    @app.get("/api/today")
    def today():
        store.close_elapsed_meetings()
        store.expire_approvals()
        plan = store.get_plan()
        return {
            "plan": plan,
            "needs_gate": plan is None,
            "halt": store.active_halt(),
            "opportunities": store.list_opportunities(),
            "approvals": store.list_approvals(),
            "rituals": store.list_rituals(),
            "meetings": store.list_meetings(),
            "mail": store.list_mail_actions(),
            "heartbeats": store.heartbeats(),
            "brain": "online",
        }

    @app.post("/api/plan")
    def save_plan(body: PlanIn):
        try:
            return store.save_plan(body.outcomes, body.timeline)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/rituals")
    def add_ritual(body: RitualIn):
        rid = store.add_ritual(**body.model_dump())
        return {"id": rid}

    @app.post("/api/rituals/{ritual_id}/done")
    def ritual_done(ritual_id: int):
        try:
            return store.complete_ritual(ritual_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/meetings")
    def add_meeting(body: MeetingIn):
        return store.upsert_meeting(**body.model_dump())

    @app.post("/api/meetings/{meeting_id}/ack")
    def ack(meeting_id: int, body: AckIn):
        try:
            return store.ack_meeting(meeting_id, body.action)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/ingest/url")
    def ingest_url(body: UrlIn):
        return store.ingest_url(body.url, body.title)

    @app.post("/api/ingest/screen")
    def ingest_screen(body: ScreenIn):
        return store.ingest_screen_text(body.text, body.url)

    @app.post("/api/ingest/phone")
    def ingest_phone(body: PhoneIn):
        eid = store.ingest_phone(body.summary, body.payload)
        return {"id": eid}

    @app.post("/api/heartbeat")
    def heartbeat(body: HeartbeatIn):
        store.heartbeat(body.sensor, body.detail)
        return {"ok": True}

    @app.post("/api/mail")
    def mail(body: MailIn):
        return store.add_mail_action(**body.model_dump())

    @app.post("/api/approvals/{approval_id}/accept")
    def accept(approval_id: int):
        try:
            return store.decide_approval(approval_id, True)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/approvals/{approval_id}/reject")
    def reject(approval_id: int):
        try:
            return store.decide_approval(approval_id, False)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/approvals/{approval_id}/keep")
    def keep(approval_id: int):
        try:
            approval = store.get_approval(approval_id)
            payload = approval["payload"]
            if payload.get("opportunity_id"):
                store.set_opportunity_state(int(payload["opportunity_id"]), "seen")
            return store.decide_approval(approval_id, False)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/chat")
    def chat(body: ChatIn):
        snapshot = today()
        ollama = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
        context = json.dumps(
            {
                "plan": snapshot["plan"],
                "opportunities": snapshot["opportunities"][:20],
                "mail": snapshot["mail"][:20],
                "approvals": snapshot["approvals"],
                "meetings": snapshot["meetings"][:10],
            },
            default=str,
        )[:8000]
        prompt = (
            "You are Timeless, a local personal assistant. Answer from this JSON snapshot. "
            "If you lack data, say so. Be direct.\n"
            f"{context}\nUser: {body.message}"
        )
        try:
            r = httpx.post(
                f"{ollama}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            r.raise_for_status()
            return {"reply": r.json().get("response", "").strip(), "offline": False}
        except Exception:
            return {
                "reply": _offline_chat(body.message, snapshot),
                "offline": True,
            }

    if WEB.exists():
        @app.get("/")
        def index():
            return FileResponse(WEB / "index.html")

        @app.get("/gate")
        def gate():
            return FileResponse(WEB / "gate.html")

        @app.get("/halt")
        def halt():
            return FileResponse(WEB / "halt.html")

        app.mount("/static", StaticFiles(directory=WEB), name="static")

    return app


def _offline_chat(message: str, snapshot: dict) -> str:
    msg = message.lower()
    if "didn" in msg and "apply" in msg or "opened" in msg:
        seen = [o for o in snapshot["opportunities"] if o["state"] == "seen"]
        if not seen:
            return "No seen-but-unapplied postings in the tracker yet."
        lines = "\n".join(f"- {o.get('role') or o['url']} ({o['url']})" for o in seen)
        return f"Opened, not applied:\n{lines}"
    if snapshot["needs_gate"]:
        return "No plan for today. The gate is still waiting."
    plan = snapshot["plan"]
    n = len(snapshot["opportunities"])
    return (
        f"Ollama is off, so this is a raw snapshot. Outcomes: {plan['outcomes']}. "
        f"{n} opportunities tracked. {len(snapshot['approvals'])} pending approvals. "
        f"{len(snapshot['mail'])} open mail cards."
    )


def main() -> None:
    import uvicorn

    host = os.environ.get("TIMELESS_HOST", "127.0.0.1")
    port = int(os.environ.get("TIMELESS_PORT", "8787"))
    uvicorn.run("timeless.app:create_app", factory=True, host=host, port=port)
