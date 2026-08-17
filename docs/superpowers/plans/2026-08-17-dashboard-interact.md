# Dashboard interactivity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this session: inline; user asked implement/commit/push).

**Goal:** Editable tables, conference Join URLs, chat local commands including Calendar.app create, RGB theme FAB.

**Architecture:** `pick_join_url` at ingest; `join_locked` on meetings; PATCH APIs; `local_cmd.parse` before hands; EventKit create helper; dashboard tables + FAB + `theme.js`.

**Tech Stack:** Python 3.12, FastAPI, sqlite3, pytest, vanilla HTML/JS, EventKit Swift.

## Global Constraints

- $0, no send/submit, SQLite source of truth, no Chart.js, theme in localStorage only.

---

### Task 1: Join picker + join_locked + PATCH + chat local cmds + UI

See spec `docs/superpowers/specs/2026-08-17-dashboard-interact-design.md`. Tests in `tests/test_join_url.py`, `tests/test_store.py`, `tests/test_api.py`, `tests/test_local_cmd.py`.
