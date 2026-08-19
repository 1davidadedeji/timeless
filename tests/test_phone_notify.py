from timeless.phone_notify import escalate_halt, halt_alert_key
from timeless.quiet import blocks_phone


def test_halt_alert_key_reminder():
    key = halt_alert_key({"halt_kind": "reminder", "id": 3, "meeting_id": 9})
    assert key == "reminder:3:9"


def test_halt_alert_key_meeting():
    key = halt_alert_key({"id": 5})
    assert key == "meeting:5:5"


def test_escalate_skipped_when_quiet():
    halt = {"id": 1, "title": "Call", "halt_kind": "meeting"}
    quiet = {"level": "quiet", "active": True}
    out = escalate_halt(halt, quiet)
    assert out["skipped"] is True
    assert out["reason"] == "quiet"


def test_blocks_phone_quiet():
    assert blocks_phone("quiet")
    assert not blocks_phone("mild")
