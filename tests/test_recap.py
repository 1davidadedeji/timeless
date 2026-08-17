from datetime import datetime, timezone

from timeless.store import Store


def test_recap_due_until_acked(tmp_path):
    store = Store(str(tmp_path / "r.db"))
    now = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)  # 07:00 CDT 18 Aug → owes 17th
    assert store.needs_recap(now) is True
    store.save_recap("2026-08-17", [{"kicker": "Admit one", "title": "Hours", "stat": "0"}], phone_synced=False)
    assert store.needs_recap(now) is True
    store.ack_recap("2026-08-17", now)
    assert store.needs_recap(now) is False
    store.close()


def test_evening_utc_event_counts_on_chicago_day(tmp_path):
    store = Store(str(tmp_path / "h.db"))
    store.conn.execute(
        "INSERT INTO events(source, ts, summary, payload) VALUES (?,?,?,?)",
        ("url", "2026-08-18T00:30:00Z", "night", "{}"),
    )
    store.conn.commit()
    assert len(store.events_on_day("2026-08-17")) == 1
    assert store.events_on_day("2026-08-18") == []
    store.close()
