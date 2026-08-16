from __future__ import annotations

import os
import re
import subprocess
from typing import Any

ALIASES: dict[str, dict[str, str]] = {
    "leetcode": {"url": "https://leetcode.com"},
    "coursera": {"url": "https://www.coursera.org"},
    "gmail": {"url": "https://mail.google.com"},
    "calendar": {"url": "https://calendar.google.com"},
    "github": {"url": "https://github.com"},
    "linkedin": {"url": "https://www.linkedin.com"},
    "whatsapp": {"app": "WhatsApp"},
    "cursor": {"app": "Cursor"},
    "chrome": {"app": "Google Chrome"},
    "zoom": {"app": "zoom.us"},
    "slack": {"app": "Slack"},
}

RISKY = re.compile(
    r"\b(send|text|message|email|submit|tweet|post|whatsapp\s+.+|mail)\b",
    re.I,
)
OPEN = re.compile(
    r"^\s*(open|launch|start|go to|join)\b(?:\s+(?:on\s+)?(my\s+)?(phone|mac|pc|computer))?\s*(.*)$",
    re.I,
)


def parse(message: str, rituals: list[dict] | None = None) -> dict[str, Any] | None:
    raw = (message or "").strip()
    if not raw:
        return None
    risky = bool(RISKY.search(raw))
    target = "phone" if re.search(r"\bon (my )?phone\b", raw, re.I) else "mac"
    m = OPEN.match(raw)
    rest = m.group(4).strip() if m else raw
    rest = re.sub(r"\s+on (my )?(phone|mac|pc|computer)\s*$", "", rest, flags=re.I).strip()
    if not m and not risky:
        return None
    key = rest.lower().strip(" .!?")
    for ritual in rituals or []:
        name = str(ritual.get("name") or "").lower()
        if name and name in key and ritual.get("launch_url"):
            return {
                "action": "open_url",
                "target": target,
                "url": ritual["launch_url"],
                "label": ritual["name"],
                "risky": risky,
            }
    for name, spec in ALIASES.items():
        if name in key:
            out = {"action": "open_app" if spec.get("app") else "open_url", "target": target, "label": name, "risky": risky}
            out.update(spec)
            return out
    if rest.startswith("http://") or rest.startswith("https://"):
        return {"action": "open_url", "target": target, "url": rest.split()[0], "label": rest.split()[0], "risky": risky}
    if m and rest:
        return {"action": "open_url", "target": target, "url": "https://www.google.com/search?q=" + rest.replace(" ", "+"), "label": rest, "risky": risky}
    if risky:
        return {"action": "send", "target": target, "label": raw, "risky": True, "text": raw}
    return None


def run(intent: dict[str, Any]) -> dict[str, Any]:
    if intent.get("risky") or intent.get("action") == "send":
        raise ValueError("refusing to send or submit without an explicit later hands layer")
    target = intent.get("target") or "mac"
    if intent.get("url"):
        return _open_url(intent["url"], target)
    if intent.get("app"):
        return _open_app(intent["app"], target)
    raise ValueError("nothing to open")


def _open_url(url: str, target: str) -> dict[str, Any]:
    if target == "phone":
        _adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url])
        return {"did": "open_url", "target": "phone", "url": url}
    subprocess.run(["open", url], check=True)
    return {"did": "open_url", "target": "mac", "url": url}


def _open_app(app: str, target: str) -> dict[str, Any]:
    if target == "phone":
        raise ValueError("opening named phone apps is not wired yet; pass a URL")
    subprocess.run(["open", "-a", app], check=True)
    return {"did": "open_app", "target": "mac", "app": app}


def _adb(args: list[str]) -> None:
    serial = os.environ.get("TIMELESS_ADB_SERIAL", "")
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    else:
        listing = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=False)
        serials: list[str] = []
        for ln in listing.stdout.splitlines()[1:]:
            parts = ln.split()
            if len(parts) >= 2 and parts[1] == "device":
                serials.append(parts[0])
        if serials:
            wireless = [s for s in serials if ":" in s]
            cmd += ["-s", (wireless or serials)[0]]
    subprocess.run(cmd + args, check=True, timeout=15)
