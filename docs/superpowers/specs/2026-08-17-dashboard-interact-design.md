# Dashboard interactivity, Join links, chat Calendar, RGB theme

**Date:** 2026-08-17  
**Status:** Approved (conversation); awaiting file review before implementation plan  
**Owner:** personal use only

Extends the live dashboard at `http://127.0.0.1:8787`. Cost stays **$0**. SQLite on the Mac remains source of truth. No send/submit.

## Goal

The dashboard is the place to **see and edit** the day: plan, events, programs. Lists read as tables, not JSON. Chat is a sticky FAB and can change Timeless-owned data and create Calendar.app events. Overlay **Join** opens the conference URL from Calendar or mail cards, not a random first `https://`. One RGB control tints the whole web UI.

## Non-goals

- LLM tool-calling over every store method
- Mail.app send, IMAP send, or any submit-to-third-party
- Scraping the full mailbox at Join click time
- Chart.js / extra npm; heatmap stays CSS
- Persisting theme in SQLite (localStorage only)
- Changing overlay Swift layout beyond pages that already load `style.css` / recap inline vars

## Shell

One page, existing card stack, two columns from 720px up.

| Order | Card | View | Edit |
|---|---|---|---|
| 1 | Year | Heatmap | None |
| 2 | Today | Outcomes + timeline | Inline; POST `/api/plan` |
| 3 | Events | Table: when, title, modality, Join | Modality + join URL; POST meeting update |
| 4 | Programs | Table: role, kind, state, URL | Fields + state; existing state API plus field PATCH |
| 5 | Approvals | Title, one-line snippet, three buttons | Accept / Keep / Ignore only |
| 6 | Mail | Subject, classification, relative time | None this pass |
| 7 | Rituals | Name, Open, Done | Done as now |
| 8 | Sensors | Name, relative last seen, ok/stale chip | None |

Chat is **removed from the main grid**. A circular button is `position: fixed; right/bottom`. Collapsed: icon. Expanded: panel with log + input. Does not change gate/recap/halt routing.

Long lists: `max-height` inside the card, overlay scrollbar, `overflow-wrap` on cells. No `auto-fit` + `grid-column: 1 / -1` (that overlap bug stays fixed).

Motion: ~200ms hover, FAB open/close, row save. No infinite animation.

## Join URL

Stored on `meetings.join_url`. Overlay Join, dashboard Join, and chat `join` all open that field then ack.

**Resolution order at ingest** (Calendar Swift + Python upsert):

1. `EKEvent.url` if host matches Zoom / Google Meet / Teams / Webex (same family as `JOIN_RE`).
2. EventKit conference URL if the SDK exposes it and host matches.
3. All `https://` in notes + location; **first matching host**, not first URL.
4. If still empty: mail cards where the event title and subject share a case-insensitive substring of at least 8 characters, or every word of length ≥ 4 from the title appears in the subject; URL from that card’s text with the same host filter.
5. Else `join_url` stays empty; Join hidden; events table accepts a paste.

Modality: matching conference URL → `virtual`. Non-empty location and no conference URL → `physical`. Unconfirmed overlay classification unchanged.

Mail ingest still does not send. This pass does not add a live Mail.app body fetch on Join. If invite bodies are needed later, that is a separate ingest change.

`meetings.join_locked` is 0 by default. Dashboard/chat PATCH of `join_url` sets it to 1. Calendar ingest may write `join_url` only when the column is empty **or** `join_locked` is 0. A locked URL is never replaced by ingest.

## Chat local commands

`/api/chat` runs `_maybe_do` first. New parsers **before** open/launch:

| Intent | Effect |
|---|---|
| Plan outcomes / add timeline block | `save_plan` for Chicago `day_key()` |
| Add event with title + time (+ optional join URL) | EventKit create on the default calendar **and** `upsert_meeting` |
| Update named event modality or join URL | Update SQLite meeting; write Calendar URL/notes when EventKit allows |
| Mark program state | `set_opportunity_state` |
| `join` during halt | Existing: open `join_url`, ack |
| `open` / `launch` | Existing hands |
| send / email / submit | Existing: pending approval, never send |

If EventKit write is denied: still `upsert_meeting`, reply names the permission failure.

Chat does not create Mail, touch other calendars, or run shell.

EventKit write is a small helper next to `TimelessCal.swift` (create event: title, start, end, notes, url). Calendar ingest remains the read path.

## APIs

Reuse `/api/plan`, `/api/opportunities/{id}/state`, `/api/meetings` POST, `/api/chat`.

Add:

- `PATCH /api/meetings/{id}` — `join_url`, `modality`, `kind`, `title` (optional). Setting `join_url` sets `join_locked=1`.
- `PATCH /api/opportunities/{id}` — `role`, `kind`, `url` (state stays the state endpoint).

`GET /api/today` already returns `meetings`; dashboard Events table uses that. Approvals payload shown as a one-line snippet (kind + truncated fields), never pretty-printed JSON.

## Theme

Header chip opens RGB sliders (0–255) + live hex + Reset. Default **accent only** (buttons, headings, FAB, heatmap high cells, recap ticket border). **Full tint** derives card/background from the same RGB but keeps background dark enough to read.

CSS variables on `:root` (`--accent` and derived `--bg`, `--card`, `--line`, `--muted`). Persist `localStorage` keys `timeless_rgb` (`"r,g,b"`) and `timeless_tint` (`accent` | `full`). `web/theme.js` runs on dashboard, gate, halt, and recap so the recap ticket border follows without depending on `style.css`. Header chip includes an accent/full toggle.

No server round-trip. Overlay picks up theme after the webview reloads the page.

## Schema

`meetings.join_locked INTEGER NOT NULL DEFAULT 0`. Existing DBs get `ALTER TABLE` in `db.py` init (same pattern as other additive columns).

## Tests

- Join picker prefers `meet.google.com` over a maps URL in the same notes blob.
- Empty join → Join control absent; PATCH join_url → Join present.
- Ingest does not overwrite a patched join_url.
- Chat “add event …” upserts a meeting; risky send still proposes approval.
- Plan save from dashboard same-day overwrite (existing test still passes).
- Theme is CSS/localStorage only (no API test required).

## Out of this plan

Graph library, mail body ingest, Tailscale overlay bind, Excel export.
