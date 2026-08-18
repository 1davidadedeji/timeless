from timeless.recap import build_cards
from timeless.store import Store


def test_build_cards_notes_phone_miss(tmp_path):
    store = Store(str(tmp_path / "c.db"))
    store.save_plan("Ship", [{"task": "code", "start": "9", "end": "10"}], day="2026-08-17")
    cards = build_cards(store, "2026-08-17", phone_synced=False)
    bodies = " ".join(c["body"] for c in cards)
    assert "did not sync" in bodies
    store.close()


def test_build_cards_are_plain_and_compare(tmp_path):
    store = Store(str(tmp_path / "d.db"))
    store.save_plan(
        "Finish the essay",
        [{"task": "Write", "start": "09:00", "end": "11:00"}],
        day="2026-08-17",
    )
    store.conn.execute(
        "INSERT INTO events(source, ts, summary, payload) VALUES (?,?,?,?)",
        ("phone", "2026-08-17T18:00:00Z", "DLS26 com.firsttouchgames.dls7", '{"app":"com.firsttouchgames.dls7"}'),
    )
    store.conn.commit()
    cards = build_cards(store, "2026-08-17", phone_synced=True)
    blob = " ".join(str(c) for c in cards)
    assert "com.firsttouchgames" not in blob
    assert any(c.get("kind") == "compare" for c in cards)
    assert any(c.get("lines") for c in cards)
    store.close()
