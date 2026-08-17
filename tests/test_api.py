from fastapi.testclient import TestClient

from timeless.app import create_app


def client(tmp_path):
    app = create_app(str(tmp_path / "api.db"))
    return TestClient(app)


def test_today_uses_chicago_and_can_ack_recap(tmp_path):
    c = client(tmp_path)
    t = c.get("/api/today").json()
    assert t["tz"] == "America/Chicago"
    assert "heatmap" in t
    assert t["needs_recap"] is True
    assert t["needs_gate"] is True
    assert t["brain"] == "online"
    ack = c.post("/api/recap/ack")
    assert ack.status_code == 200
    later = c.get("/api/today").json()
    assert later["needs_recap"] is False
    assert later["needs_gate"] is True


def test_plan_and_gate(tmp_path):
    c = client(tmp_path)
    bad = c.post("/api/plan", json={"outcomes": "", "timeline": [{"task": "x"}]})
    assert bad.status_code in (400, 422)
    ok = c.post(
        "/api/plan",
        json={
            "outcomes": "Ship Timeless brain",
            "timeline": [
                {"start": "21:00", "end": "22:00", "task": "LeetCode", "ritual": "leetcode"}
            ],
        },
    )
    assert ok.status_code == 200
    assert c.get("/api/today").json()["needs_gate"] is False


def test_chat_offline_does_not_500(tmp_path):
    c = client(tmp_path)
    c.post("/api/plan", json={"outcomes": "work", "timeline": [{"task": "code", "start": "9", "end": "10"}]})
    r = c.post("/api/chat", json={"message": "what did I do"})
    assert r.status_code == 200
    assert "offline" in r.json()


def test_meeting_ack_api(tmp_path):
    c = client(tmp_path)
    m = c.post(
        "/api/meetings",
        json={
            "uid": "m1",
            "title": "Interview",
            "start_at": "2020-01-01T00:00:00Z",
            "end_at": "2099-01-01T00:00:00Z",
            "join_url": "https://meet.google.com/abc",
        },
    ).json()
    halt = c.get("/api/today").json()["halt"]
    assert halt["id"] == m["id"]
    c.post(f"/api/meetings/{m['id']}/ack", json={"action": "im_in"})
    assert c.get("/api/today").json()["halt"] is None


def test_heartbeat_api(tmp_path):
    c = client(tmp_path)
    r = c.post("/api/heartbeat", json={"sensor": "mac_aw", "detail": "ok"})
    assert r.status_code == 200
    sensors = [h["sensor"] for h in c.get("/api/today").json()["heartbeats"]]
    assert "mac_aw" in sensors


def test_do_open_does_not_send(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "timeless.app.run_hands",
        lambda intent: {"did": "open_url", "url": intent["url"], "target": intent["target"]},
    )
    c = client(tmp_path)
    r = c.post("/api/do", json={"message": "open leetcode"})
    assert r.status_code == 200
    body = r.json()
    assert body["did"]["url"] == "https://leetcode.com"
    assert "Opened leetcode" in body["reply"]


def test_chat_queues_send_instead_of_sending(tmp_path):
    c = client(tmp_path)
    r = c.post("/api/chat", json={"message": "send a text to mom"})
    assert r.status_code == 200
    body = r.json()
    assert body["did"] is None
    assert "will not send" in body["reply"].lower()
    kinds = [a["kind"] for a in c.get("/api/today").json()["approvals"]]
    assert "do_send" in kinds
