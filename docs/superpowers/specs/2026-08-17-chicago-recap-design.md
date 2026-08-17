# Timeless — Chicago day, nightly recap, dashboard, calendar, mail

**Date:** 2026-08-17  
**Status:** Approved  
**Owner:** personal use only

## Timezone

All calendar days use `America/Chicago` (`TIMELESS_TZ`, default). Timestamps on disk stay UTC ISO-8601 (`…Z`). “Today” must not roll at 19:00 CDT.

## Nightly recap

At 23:55 local, the overlay shows a tap-through **gallery ticket** deck (carbon, gold rule, condensed type). One fact per card. Last card: **I saw this**. No skip, no autoplay, no sound. No typing.

If the Mac is asleep at 23:55, the next wake shows **that day’s recap first**, then the morning plan gate. Priority: meeting halt → recap → gate.

Only the latest due day is required (not a backlog of missed nights).

**Phone first:** before generating the deck, run the existing phone ActivityWatch pull (USB or wireless ADB). Timeout; if the phone is unreachable, still show the recap with a ticket that says phone did not sync. Pull once per recap row, not on every overlay poll.

Cards from SQLite: date, hours/events on Mac, top apps, phone, jobs opened, misses/gaps, optional Ollama line if up. Empty mail/calendar omitted until those ingest.

Ack stores `acked_at`. Overlay then proceeds to gate if that Chicago day has no plan.

## Dashboard visuals

Home grows a GitHub-style contribution heatmap (events per Chicago day, last ~52 weeks) plus a simple bar of today’s top apps. Same ticket/gold language as the recap, not a new theme.

## Calendar

Ingest from **Calendar.app / EventKit** on this Mac (accounts already signed in). Upsert `meetings` so halt works. No Google Cloud OAuth app in this slice.

## Mail

Ingest unread **Mail.app** messages (local, already signed in). Classify cheaply into `mail_actions`. No send. Newsletters stay off Ollama.

## Cost

Still $0. No paid APIs.
