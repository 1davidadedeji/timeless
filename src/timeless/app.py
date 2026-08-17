from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from timeless.access import advertised_hosts, is_loopback, token_ok, ui_token
from timeless.calendar_write import create_calendar_event
from timeless.clock import day_key, due_recap_day, zone
from timeless.hands import parse, run as run_hands
from timeless.local_cmd import apply_local, parse_local
from timeless.recap import ensure_recap
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
    location: str | None = None
    notes: str | None = None


class ReminderAckIn(BaseModel):
    action: str
    kind: str | None = None
    modality: str | None = None


class MeetingPatchIn(BaseModel):
    join_url: str | None = None
    modality: str | None = None
    kind: str | None = None
    title: str | None = None


class OppPatchIn(BaseModel):
    role: str | None = None
    kind: str | None = None
    url: str | None = None


class OppStateIn(BaseModel):
    state: str
    kind: str | None = None


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

    @app.middleware("http")
    async def require_token(request: Request, call_next):
        host = request.client.host if request.client else ""
        provided = request.headers.get("authorization") or ""
        if provided.lower().startswith("bearer "):
            provided = provided[7:].strip()
        else:
            provided = request.query_params.get("token")
        if not token_ok(provided, host):
            return JSONResponse({"detail": "token required"}, status_code=401)
        return await call_next(request)

    @app.get("/api/access")
    def access(request: Request):
        host = request.client.host if request.client else ""
        port = int(os.environ.get("TIMELESS_PORT", "8787"))
        token = ui_token() if is_loopback(host) else None
        urls = []
        if token:
            for h in advertised_hosts():
                urls.append(f"http://{h}:{port}/?token={token}")
        return {"loopback": is_loopback(host), "urls": urls, "tz": str(zone())}

    @app.get("/api/today")
    def today():
        store.close_elapsed_meetings()
        store.expire_approvals()
        now_day = day_key()
        recap = None
        if store.needs_recap():
            recap = ensure_recap(store, do_pull=os.environ.get("PYTEST_CURRENT_TEST") is None)
        plan = store.get_plan(now_day)
        return {
            "plan": plan,
            "day": now_day,
            "tz": str(zone()),
            "needs_gate": plan is None,
            "needs_recap": store.needs_recap(),
            "recap": recap or store.get_recap(due_recap_day()),
            "halt": store.active_halt(),
            "opportunities": store.list_opportunities(),
            "approvals": store.list_approvals(),
            "rituals": store.list_rituals(),
            "meetings": store.list_meetings(),
            "mail": store.list_mail_actions(),
            "heartbeats": store.heartbeats(),
            "heatmap": store.heatmap(),
            "brain": "online",
        }

    @app.post("/api/recap/ack")
    def recap_ack():
        try:
            return store.ack_recap()
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

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

    @app.patch("/api/meetings/{meeting_id}")
    def patch_meeting(meeting_id: int, body: MeetingPatchIn):
        try:
            return store.patch_meeting(meeting_id, **body.model_dump())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.patch("/api/opportunities/{opp_id}")
    def patch_opp(opp_id: int, body: OppPatchIn):
        try:
            return store.patch_opportunity(opp_id, **body.model_dump())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/reminders/{reminder_id}/ack")
    def reminder_ack(reminder_id: int, body: ReminderAckIn):
        try:
            return store.ack_reminder(reminder_id, body.action, body.kind, body.modality)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/opportunities/{opp_id}/state")
    def opp_state(opp_id: int, body: OppStateIn):
        try:
            return store.set_opportunity_state(opp_id, body.state, body.kind)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

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

    @app.post("/api/do")
    def do_command(body: ChatIn):
        out = _maybe_do(store, body.message)
        if not out:
            raise HTTPException(400, "not an action I can run yet")
        return out

    @app.post("/api/chat")
    def chat(body: ChatIn):
        acted = _maybe_do(store, body.message)
        if acted:
            return {**acted, "offline": False}
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
            "If the user asks you to open a site or app, say they can type: open leetcode "
            "or open coursera on my phone. You cannot send messages yourself.\n"
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

        @app.get("/recap")
        def recap_page():
            return FileResponse(WEB / "recap.html")

        app.mount("/static", StaticFiles(directory=WEB), name="static")

    return app


def _maybe_do(store: Store, message: str) -> dict | None:
    halt = store.active_halt()
    if halt and re.search(r"\bjoin\b", message, re.I) and halt.get("join_url"):
        intent = {"action": "open_url", "target": "mac", "url": halt["join_url"], "label": halt["title"], "risky": False}
        did = run_hands(intent)
        store.ack_meeting(halt["id"], "join")
        return {"reply": f"Joining {halt['title']}.", "did": did}
    local = parse_local(message)
    if local:
        try:
            return apply_local(store, local, create_calendar_event)
        except ValueError as exc:
            return {"reply": str(exc), "did": None}
    intent = parse(message, store.list_rituals())
    if not intent:
        return None
    if intent.get("risky"):
        approval = store.propose("do_send", intent)
        return {
            "reply": f"I will not send or submit until you accept approval #{approval['id']}.",
            "did": None,
            "approval": approval,
        }
    try:
        did = run_hands(intent)
    except Exception as exc:
        return {"reply": f"Could not do that: {exc}", "did": None}
    where = intent.get("target") or "mac"
    return {"reply": f"Opened {intent.get('label')} on {where}.", "did": did}


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

    host = os.environ.get("TIMELESS_HOST", "0.0.0.0")
    port = int(os.environ.get("TIMELESS_PORT", "8787"))
    uvicorn.run("timeless.app:create_app", factory=True, host=host, port=port)
