# Events, reminders, and program pipeline

**Date:** 2026-08-17  
**Status:** Approved  
**Owner:** personal use only

## Overlay

All reminder fires use the existing full-screen overlay. The user must tap: **Join** (opens URL if present), **I’m headed** (physical), **That’s right** / **Change type** on first classification, or **Dismiss** (this fire only). Virtual 30-minute and physical 2-hour fires do not cancel the existing start-time meeting halt.

## Classification

Calendar ingest guesses `kind` (`meeting`, `hackathon`, `conference`, `other`) and `modality` (`virtual`, `physical`):

- Join URL (Zoom/Meet/Teams/Webex) → virtual  
- Location/address without join URL → physical  
- Keywords: hackathon/ctf/devfest → hackathon; conference/summit/symposium → conference  

First overlay confirms. Choice is stored on that calendar `uid`.

## Reminder schedule

One SQLite row per fire (`event_uid`, `purpose`, `due_at`, `acked_at`). Overlay shows the next unacked row with `due_at <= now`.

| Type | Fires |
|---|---|
| Virtual meeting | 30 min before start |
| Physical meeting/conference | 1 day before start; 2 h before start |
| Hackathon virtual | 1 day before start; 30 min before start; 4 h before submission if known; 30 min before presentation |
| Hackathon physical | 1 day before start; 2 h before start; 4 h before submission; 30 min before presentation |

Deadlines from notes (`deadline`, `submit by`, `applications close`) or `deadline_at` on the program. Presentation from `demo` / `pitch` / `presentation` / `judging` timed events. No guessed 4 h fire without a timestamp.

Mail.app subjects (and Calendar) both feed programs: hackathon/conference/job language upserts `opportunities` and, if a date is in the subject, a `mail:` calendar row so reminders fire even when it was never on Calendar.app.

## Programs

`opportunities` stays one list. Add `kind`: `internship`, `hackathon`, `conference`, `other`. States: `seen`, `applied`, `shortlisted`, `interview`, `waiting`, `offer`, `rejected`, `skipped`, `ignored`. Automation still writes states only via `pending_approvals`. Overlay does not change program status.

## Cost

$0. Local SQLite. Calendar.app ingest already running.
