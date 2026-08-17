from timeless.mailer import classify_subject


def test_newsletter_ignored():
    assert classify_subject("Weekly digest", "news@example.com") == "ignore"


def test_application_is_job():
    assert classify_subject("Complete your application") == "job"
