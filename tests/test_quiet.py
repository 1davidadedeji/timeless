from datetime import datetime, timedelta, timezone

import pytest

from timeless.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path / "quiet.db"))
    yield s
    s.close()


def test_active_halt_blocked_during_quiet(store):
    store.create_quiet(level="quiet", minutes=60)
    store.upsert_meeting(
        "m-quiet",
        "Standup",
        "2020-01-01T00:00:00Z",
        "2099-01-01T00:00:00Z",
        "https://meet.google.com/abc",
    )
    halt = store.active_halt()
    assert halt is None
    hearts = {h["sensor"]: h for h in store.heartbeats()}
    assert "quiet_mute" in hearts


def test_mild_halt_is_banner(store):
    store.create_quiet(level="mild", minutes=30)
    store.upsert_meeting(
        "m-mild",
        "Standup",
        "2020-01-01T00:00:00Z",
        "2099-01-01T00:00:00Z",
        None,
    )
    store.patch_meeting(
        store.conn.execute("SELECT id FROM meetings WHERE uid='m-mild'").fetchone()["id"],
        modality="physical",
    )
    halt = store.active_halt()
    assert halt is not None
    assert halt.get("presentation") == "banner"


def test_panic_creates_dormant(store):
    row = store.panic_quiet()
    assert row["level"] == "dormant"
    assert row["reason"] == "panic"
    assert store.is_dormant()


def test_auto_interview_quiet(store):
    store.upsert_meeting(
        "int-1",
        "Google Interview",
        "2099-06-01T14:00:00Z",
        "2099-06-01T15:00:00Z",
        "https://meet.google.com/x",
        kind="interview",
    )
    rows = store.list_quiet(datetime(2099, 1, 1, tzinfo=timezone.utc))
    assert any(r["source"] == "auto_interview" for r in rows)


def test_dormant_skips_screen_approval(store):
    store.create_quiet(level="dormant", minutes=30)
    out = store.ingest_screen_text("Application submitted successfully", "https://example.com/job")
    assert out.get("skipped") == "dormant"


def test_end_quiet(store):
    q = store.create_quiet(level="quiet", minutes=60)
    store.end_quiet(q["id"])
    assert store.active_quiet() is None
