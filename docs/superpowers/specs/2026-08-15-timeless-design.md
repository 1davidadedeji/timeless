# Timeless — Personal Assistant Design

**Date:** 2026-08-15  
**Status:** Approved for v1 implementation  
**Owner:** personal use only (David). Not a product for friends.

Timeless is a local personal assistant that watches the Mac and Samsung phone (with OS-level limits), measures what actually happened, gates the day and meetings, tracks applications, and reads every inbox for actionable items. Cost must stay **$0**. No paid APIs, no screenpipe subscription. Data lives on the Mac.

## Goal

When the Mac is on, Timeless is on. The phone feeds it whenever it can. The user cannot start the day without typing a plan, cannot ignore a meeting without acknowledging it, can see a dashboard and chat from both devices, and has a single tracker for internships and other submissions.

## Non-goals (v1)

- Siri, Bixby, or Google Assistant as a front door
- Dedicated Mac Mini / large local models (later; laptop uses 8B–12B Ollama)
- Silent 24/7 Samsung framebuffer recording (no MediaProjection-as-screenpipe)
- Auto-clicking Apply, sending email, or acting in other apps
- Shipping to other people / commercial use of screenpipe source

## Hardware and cost

- MacBook Pro M5 Pro, 24 GB unified memory
- Samsung phone (Android)
- Free stack only: ActivityWatch, screenpipe **built from source** (personal non-commercial license), Ollama, Tailscale, Gmail API / Microsoft Graph / IMAP (user-owned apps, no paid SKUs)

Watchers stay running. Ollama loads only for chat, daily digest rewrite, and praise lines.

## Architecture

One Mac-side brain. Sensors write; Timeless reads and proposes. SQLite on the Mac is the source of truth. Excel/CSV is export only.

```
Samsung                               MacBook Pro
ActivityWatch Android                 ActivityWatch server
Accessibility observer (UI text,      screenpipe engine (from source)
  notifications)                      Ollama (on demand)
optional scrcpy when on LAN           Timeless brain (HTTP + SQLite)
        -- Wi-Fi / Tailscale -->      launchd keeps watchers + brain alive
```

Dashboard and chat are the same local web app. Phone and Mac open it via LAN or Tailscale. If the Mac is asleep, the brain is offline. The UI must show `brain offline` rather than inventing a quiet day.

### Clone vs leave alone

| Piece | Policy |
|---|---|
| ActivityWatch | Install and configure. Fork only to fix Android export/sync. |
| screenpipe | Clone, build, run locally, point at Ollama, no account. Tweak interval, retention, ignored apps. |
| Phone observer | Small Android app (or gutted accessibility sample): periodic visible UI text + notifications. Not a tap-the-phone cloud agent. |
| Brain + UI | Original Timeless code. |

## What Timeless can see

| Device | Signal | Use |
|---|---|---|
| Mac | ActivityWatch: app, window title, browser URL, AFK | Productivity, ritual time, job URLs |
| Mac | screenpipe: screenshot + OCR + accessibility tree | Confirmations, deadlines on page, “what was I looking at” |
| Phone | ActivityWatch: foreground app | Phone vs Mac time |
| Phone | Accessibility: visible text, notifications | Job text, meeting nags, mail alerts |
| Phone | scrcpy pixels | Only when phone is on the same network; optional |

Keyboard contents are not stored. AFK uses activity, not key logs.

## Data model (SQLite on the Mac)

Core tables:

- `events` — normalized sensor events (source, timestamp, app/url/text summary)
- `opportunities` — applications and postings
- `pending_approvals` — proposed writes the user must accept/edit/reject
- `daily_plans` — one plan per calendar day (outcomes + timeline JSON)
- `rituals` — reusable daily launches (LeetCode, Coursera, …)
- `meetings` — calendar-derived; ack state
- `mail_accounts` — Gmail / Graph / IMAP config pointers (secrets in Keychain, not SQLite)
- `mail_actions` — daily actionable cards
- `heartbeats` — last seen per sensor (mac_aw, mac_screenpipe, phone_aw, phone_a11y, mail)

### Opportunity states

`seen` | `applied` | `skipped` | `waiting` | `deadline` (deadline is a field on the row, not a mutually exclusive life-state). Life-state is one of: `seen`, `applied`, `skipped`, `waiting`, `ignored`.

- `seen` — opened a posting / clicked a link, not applied
- `applied` — submitted (confirmation page, confirmation email, or user confirm)
- `skipped` — passed (not qualified or not interested); do not nag to reapply
- `waiting` — applied, waiting on them
- `ignored` — user dismissed or approval expired

Deadline is `deadline_at` on the row. Weekend view: all `seen` with links to reopen.

### Approvals

Automation never writes opportunity life-state except through `pending_approvals`, unless the user later enables an explicit preference such as “auto-mark Greenhouse thank-you as applied” (default **off**).

If an approval is unanswered for **7 days**, it becomes `ignored`, never `applied`.

Ambiguous “didn’t qualify” must ask: skip (don’t remind), keep as `seen` (reapply later), or ignore. Default suggestion when on-screen text is a hard requirement miss: `skipped`. Never auto-write.

## Data flow

Producers: phone AW + UI text + notifications; Mac AW; screenpipe; all mail accounts.

Ingest upserts events, may create `pending_approvals`, never blocks on Ollama.

Chat queries SQLite (and ActivityWatch/screenpipe APIs when present). Ollama sees extracted summaries, not raw video.

Phone pushes on Wi-Fi to the Mac HTTP ingest endpoint (Tailscale when away). No public ports.

### Mail

All accounts. Types: Gmail API, Microsoft Graph, generic IMAP (Samsung Email, iCloud, school). Morning job + optional evening job. Fetch new/unread since last cursor. Dedupe by `Message-ID`. Cheap local classify first (job, interview, rejection, deadline, reply-needed, ignore). Ollama rewrites only the actionable pile into cards. Newsletters do not go to the model. Same card UI: accept (touch opportunity), snooze, dismiss. Dismissed senders can be muted.

### Screen → tracker

1. Job-like URL → upsert `seen` (link, title if known).
2. Confirmation language in OCR/a11y or matching confirmation email → approval “mark applied?”
3. Hard reject of the candidate on screen + close → approval skip/keep/ignore
4. “Apply by / closes” dates → `deadline_at`

Android URL capture is weaker; mail + Mac browsing catch most internships.

## Daily gate

First unlock of the calendar day on the Mac (and on the phone if the observer is alive): full-screen overlay. Other apps do not receive clicks until submit.

User must type:

- Today’s outcomes (what “done” means)
- A timeline (blocks: start, end, task, optional ritual id)

Empty submit is rejected. No Skip today in the UI. Emergency unlock is **off** by default (if ever added: long hold + typed phrase, logged as a miss).

Second submit the same day updates the plan; it does not create a second day row.

## Rituals (daily work)

Reusable items: name, launch URL or Mac app bundle, weekday mask, optional minimum minutes on matching host for a *suggested* Done.

When a block starts or the user taps Start: Mac opens URL/app; phone opens URL if that is the target. Overlay **releases** after launch (not a halt).

Done when the user taps Done. ActivityWatch time on the matching site may **suggest** Done; user still confirms.

On confirm: short local praise (phrase bank + one Ollama sentence). Specific to what finished. No public streaks. Misses are dashboard facts, not guilt copy.

If Timeless sees a repeated morning site, it may *propose* pinning a ritual (approval card).

## Meeting halt

All calendars the user adds (Mac Calendar / Google / Microsoft).

At start (optional 60s warning, then hard):

1. Overlay covers Mac and phone if reachable. Apps underneath may keep running; the user cannot use them.
2. Card: title, time, join URL. Actions: **Join** (opens Zoom/Meet/Teams) or **I’m in**.
3. No close, no later, until one action.
4. After acknowledge, overlay releases. Multitask allowed for the rest of the meeting.
5. If never acked: overlay stays until event end, then drops, `meeting_missed` logged.

If there is no URL, **I’m in** is the only path.

Timeless does not inject taps into Zoom/Samsung apps in v1.

Meetings are the only hard interrupt. Rituals nudge-open. Daily gate is a once-per-day halt until a plan exists.

## Dual-device UI

Local web app hosted by the Mac brain.

- Home: dashboard (today’s plan vs ActivityWatch, opportunities due this week, mail cards, sensor heartbeats, phone gaps)
- Chat: questions like “what did I actually do today?” and “jobs I opened but didn’t apply”
- Gate and halt routes: fullscreen overlays (Mac can also open these as a borderless window via a tiny wrapper later)

Access: `http://<lan-host>:<port>` at home; Tailscale when away.

## Failure model

| Failure | Behavior |
|---|---|
| Mac asleep | Phone UI unreachable; last data kept; `brain offline`; no fake empty day |
| Samsung kills observer | Persistent notification + battery exemption; dashboard shows `phone gap HH:MM–HH:MM` |
| scrcpy down | App + UI text + notifications only |
| AW or screenpipe crash | launchd restart; last heartbeat on dashboard; chat refuses “today” if newest event is >15 minutes old while user is not AFK |
| Mail auth expired | That inbox greyed; others continue; reconnect card |
| Ollama down | Dashboard and tracker work; digest queued; chat errors cleanly |
| Disk filling | screenpipe retention 14–30 days of frames; text/AW kept longer; warn at 80% disk |
| Duplicate confirmation emails | Dedupe Message-ID; merge opportunity by company + role + week |
| Tailscale down | Phone queues events, flushes on next path to Mac |

Ingest never sends mail, never clicks Apply, never deletes mail.

Rotating logs: heartbeats, fetch counts, error types. No mail bodies or screenshots in logs.

## Security and privacy

- Personal machine only. Secrets in macOS Keychain.
- Bind HTTP to Tailscale/LAN interfaces, not `0.0.0.0` on a public network.
- screenpipe source: personal non-commercial use; do not rebrand or ship as a product.
- No keylogger. No clipboard vacuum.

## v1 module order

1. Brain: SQLite, HTTP, dashboard + chat shell, dual-device access
2. Sensors: document install of ActivityWatch + screenpipe-from-source + Ollama; ingest adapters; phone observer stub that can POST events
3. Daily gate + rituals + praise
4. Meeting halt + calendar accounts
5. Opportunity tracker + screen/URL ingest rules
6. All-inbox mail digest

## Verification

### Automated (Timeless code)

- Opportunity life-state from automation only via pending approvals (default)
- Duplicate `Message-ID` does not create a second mail action
- Approval older than 7 days → ignored, not applied
- Empty daily plan rejected; second submit updates same day
- Meeting requires `join` or `im_in`; event end without ack → `meeting_missed`

### Manual

1. Gate blocks until a real timeline; rituals open the right URLs
2. Done on a ritual → praise; AW shows time on that site (if AW installed)
3. Calendar event 2 minutes ahead → overlay → Join opens link → other apps usable
4. Ignore a fake meeting until end → `meeting_missed`
5. Job URL → `seen`; fake thank-you → applied card; requirements miss → skip/keep/ignore card
6. Two mail accounts: newsletter ignored, “complete your application” becomes a card
7. Phone on LAN/Tailscale sees the same UI; kill observer → phone gap
8. Ollama quit → dashboard lives, chat fails cleanly
9. $0: no screenpipe login, no paid keys

## Later

Timetable scoring against the plan in more detail, Mac Mini local models, voice assistants, optional MediaProjection on Samsung, auto-mark confirmation preferences, Excel export button.
