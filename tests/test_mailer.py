from timeless.mailer import classify_subject


def test_newsletter_ignored():
    assert classify_subject("Weekly digest", "news@example.com") == "ignore"


def test_application_is_job():
    assert classify_subject("Complete your application") == "job"


def test_hackathon_from_email():
    assert classify_subject("You're invited: UAPB Hackathon Aug 22") == "hackathon"


def test_parse_named_date():
    from datetime import datetime, timezone

    from timeless.mailer import parse_when

    when = parse_when("Hackathon on August 22, 2026", datetime(2026, 8, 17, tzinfo=timezone.utc))
    assert when.day == 22
    assert when.month == 8
    assert when.year == 2026
