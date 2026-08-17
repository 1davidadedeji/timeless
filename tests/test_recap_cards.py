from timeless.recap import build_cards
from timeless.store import Store


def test_build_cards_notes_phone_miss(tmp_path):
    store = Store(str(tmp_path / "c.db"))
    store.save_plan("Ship", [{"task": "code", "start": "9", "end": "10"}], day="2026-08-17")
    cards = build_cards(store, "2026-08-17", phone_synced=False)
    bodies = " ".join(c["body"] for c in cards)
    assert "did not sync" in bodies
    store.close()
