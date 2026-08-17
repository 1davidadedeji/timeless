# Chicago recap, visuals, calendar, mail

> **For agentic workers:** implement task-by-task. TDD for Python. One file per git commit.

**Goal:** Chicago calendar days, forced nightly recap (phone pull first), heatmap dashboard, Calendar.app meetings, Mail.app cards.

**Architecture:** `clock.py` owns TZ. Recap rows in SQLite. Overlay adds `/recap`. LaunchAgents pull Calendar and Mail like AW ingest.

**Tech Stack:** Python 3.12, FastAPI, Swift overlay, EventKit, Mail.app.

## Global Constraints

- Default TZ `America/Chicago`
- Recap visual: gallery ticket
- Overlay order: halt → recap → gate
- Phone pull once per recap generation
- $0, no send mail
- Commit each file separately; push
