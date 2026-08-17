from datetime import datetime, timezone

from timeless.clock import day_key, due_recap_day, recap_window_open


def test_evening_utc_is_still_chicago_afternoon():
    # 00:00 UTC 18 Aug = 19:00 CDT 17 Aug
    now = datetime(2026, 8, 18, 0, 0, tzinfo=timezone.utc)
    assert day_key(now) == "2026-08-17"
    assert recap_window_open(now) is False


def test_recap_opens_at_2355_chicago():
    before = datetime(2026, 8, 18, 4, 54, tzinfo=timezone.utc)
    after = datetime(2026, 8, 18, 4, 55, tzinfo=timezone.utc)
    assert recap_window_open(before) is False
    assert recap_window_open(after) is True
    assert due_recap_day(after) == "2026-08-17"


def test_morning_owes_yesterday():
    morning = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)  # 07:00 CDT 18 Aug
    assert day_key(morning) == "2026-08-18"
    assert recap_window_open(morning) is False
    assert due_recap_day(morning) == "2026-08-17"
