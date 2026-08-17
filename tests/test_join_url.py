from timeless.classify_event import mail_matches_event, pick_join_url


def test_pick_join_prefers_meet_over_maps():
    notes = "Map: https://maps.google.com/?q=1+Main Directions https://meet.google.com/abc-defg-hij"
    assert pick_join_url(notes) == "https://meet.google.com/abc-defg-hij"


def test_pick_join_uses_preferred_if_conference():
    assert (
        pick_join_url("https://example.com/x", preferred="https://zoom.us/j/1")
        == "https://zoom.us/j/1"
    )


def test_pick_join_ignores_preferred_maps():
    assert pick_join_url("https://teams.microsoft.com/l/meetup/1", preferred="https://maps.apple.com/?q=x") == (
        "https://teams.microsoft.com/l/meetup/1"
    )


def test_pick_join_empty():
    assert pick_join_url("see you in the lobby https://example.com/agenda") is None


def test_mail_matches_shared_substring():
    assert mail_matches_event("Acme Interview Loop", "Acme Interview Loop — Zoom")
    assert mail_matches_event("Weekly Standup", "FW: Weekly Standup notes")


def test_mail_does_not_match_unrelated():
    assert not mail_matches_event("Dentist", "Your package has shipped")
