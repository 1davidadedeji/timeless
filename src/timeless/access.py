from __future__ import annotations

import os
import secrets
import socket
import subprocess
from pathlib import Path

TOKEN_FILE = Path.home() / "Library" / "Application Support" / "Timeless" / "ui.token"


def ui_token() -> str:
    env = os.environ.get("TIMELESS_TOKEN", "").strip()
    if env:
        return env
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return "pytest-token"
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(16)
    TOKEN_FILE.write_text(token, encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    return token


def is_loopback(host: str | None) -> bool:
    h = (host or "").split("%")[0]
    return h in {"127.0.0.1", "::1", "localhost", "testclient"}


def token_ok(provided: str | None, host: str | None) -> bool:
    if is_loopback(host):
        return True
    expected = ui_token()
    return bool(provided) and provided == expected


def advertised_hosts() -> list[str]:
    hosts = ["127.0.0.1"]
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        hosts.append(sock.getsockname()[0])
        sock.close()
    except OSError:
        pass
    try:
        out = subprocess.check_output(["tailscale", "ip", "-4"], text=True, timeout=2)
        for line in out.split():
            if line.count(".") == 3:
                hosts.append(line.strip())
    except Exception:
        pass
    seen: set[str] = set()
    ordered = []
    for h in hosts:
        if h not in seen:
            seen.add(h)
            ordered.append(h)
    return ordered
