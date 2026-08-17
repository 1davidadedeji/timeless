from timeless.access import is_loopback, token_ok


def test_loopback_skips_token():
    assert is_loopback("127.0.0.1")
    assert token_ok(None, "127.0.0.1") is True


def test_lan_requires_matching_token(monkeypatch):
    monkeypatch.setenv("TIMELESS_TOKEN", "secret-token")
    assert token_ok(None, "10.0.0.2") is False
    assert token_ok("nope", "10.0.0.2") is False
    assert token_ok("secret-token", "10.0.0.2") is True
