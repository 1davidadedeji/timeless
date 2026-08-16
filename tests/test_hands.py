from timeless.hands import parse


def test_open_leetcode_on_mac():
    intent = parse("open leetcode")
    assert intent["action"] == "open_url"
    assert intent["url"] == "https://leetcode.com"
    assert intent["target"] == "mac"
    assert intent["risky"] is False


def test_open_on_phone():
    intent = parse("open coursera on my phone")
    assert intent["target"] == "phone"
    assert "coursera.org" in intent["url"]


def test_ritual_name():
    intent = parse("start LeetCode", rituals=[{"name": "LeetCode", "launch_url": "https://leetcode.com/problemset"}])
    assert intent["url"] == "https://leetcode.com/problemset"


def test_send_is_risky():
    intent = parse("send a text to mom that I'm late")
    assert intent["risky"] is True
    assert intent["action"] == "send"


def test_not_a_command():
    assert parse("what did I do today?") is None
