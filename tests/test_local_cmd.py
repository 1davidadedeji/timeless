from timeless.local_cmd import parse_local


def test_plan_outcomes():
    intent = parse_local("plan outcomes: ship the gate")
    assert intent["action"] == "plan_outcomes"
    assert intent["outcomes"] == "ship the gate"


def test_add_block():
    intent = parse_local("add block 14:00-16:00 applications")
    assert intent["action"] == "add_block"
    assert intent["start"] == "14:00"
    assert intent["end"] == "16:00"
    assert intent["task"] == "applications"


def test_add_event_with_join():
    intent = parse_local("add event Interview 2026-08-20 14:00-15:00 https://meet.google.com/abc")
    assert intent["action"] == "add_event"
    assert intent["title"] == "Interview"
    assert intent["join_url"] == "https://meet.google.com/abc"
    assert intent["start_at"].startswith("2026-08-20T")


def test_mark_program():
    intent = parse_local("mark Intern applied")
    assert intent["action"] == "mark_program"
    assert intent["query"] == "Intern"
    assert intent["state"] == "applied"


def test_event_virtual():
    intent = parse_local("event Zoom standup is virtual")
    assert intent["action"] == "event_modality"
    assert intent["query"] == "Zoom standup"
    assert intent["modality"] == "virtual"


def test_not_local():
    assert parse_local("what did I do today?") is None
    assert parse_local("open leetcode") is None
