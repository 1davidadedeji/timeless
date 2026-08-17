from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY,
    company TEXT,
    role TEXT,
    url TEXT,
    state TEXT NOT NULL CHECK (state IN ('seen','applied','skipped','waiting','ignored')),
    deadline_at TEXT,
    source TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pending_approvals (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','accepted','rejected','expired')),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_plans (
    id INTEGER PRIMARY KEY,
    day TEXT NOT NULL UNIQUE,
    outcomes TEXT NOT NULL,
    timeline TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rituals (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    launch_url TEXT,
    app_bundle TEXT,
    weekdays TEXT,
    match_host TEXT,
    min_minutes INTEGER
);

CREATE TABLE IF NOT EXISTS ritual_completions (
    id INTEGER PRIMARY KEY,
    ritual_id INTEGER NOT NULL,
    day TEXT NOT NULL,
    praise TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (ritual_id, day),
    FOREIGN KEY (ritual_id) REFERENCES rituals(id)
);

CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY,
    uid TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    join_url TEXT,
    ack TEXT CHECK (ack IN ('join','im_in','missed') OR ack IS NULL),
    acked_at TEXT
);

CREATE TABLE IF NOT EXISTS mail_actions (
    id INTEGER PRIMARY KEY,
    message_id TEXT NOT NULL UNIQUE,
    account TEXT NOT NULL,
    subject TEXT,
    classification TEXT NOT NULL,
    card TEXT,
    status TEXT NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    ts TEXT NOT NULL,
    summary TEXT,
    payload TEXT
);

CREATE TABLE IF NOT EXISTS heartbeats (
    sensor TEXT PRIMARY KEY,
    last_seen TEXT NOT NULL,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS daily_recaps (
    day TEXT PRIMARY KEY,
    cards TEXT NOT NULL,
    phone_synced INTEGER NOT NULL DEFAULT 0,
    generated_at TEXT NOT NULL,
    acked_at TEXT
);
"""

def connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
