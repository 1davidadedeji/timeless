from datetime import datetime, timezone

from timeless.classify_event import classify_event
from timeless.reminders import reminder_fires


def test_zoom_is_virtual_meeting():
    kind, modality = classify_event("Standup", "https://zoom.us/j/1", None)
    assert kind == "meeting"
    assert modality == "virtual"


def test_hackathon_physical_from_title_and_room():
    kind, modality = classify_event("UAPB Hackathon", None, "Campus Union Room 2")
    assert kind == "hackathon"
    assert modality == "physical"


def test_virtual_meeting_only_30m():
    start = datetime(2026, 8, 20, 18, 0, tzinfo=timezone.utc)
    fires = reminder_fires("meeting", "virtual", start)
    assert fires == [("start_30m", datetime(2026, 8, 20, 17, 30, tzinfo=timezone.utc))]


def test_hackathon_physical_includes_submit():
    start = datetime(2026, 8, 21, 16, 0, tzinfo=timezone.utc)
    submit = datetime(2026, 8, 22, 4, 0, tzinfo=timezone.utc)
    purposes = [p for p, _ in reminder_fires("hackathon", "physical", start, submit=submit)]
    assert purposes == ["start_1d", "start_2h", "submit_4h"]
