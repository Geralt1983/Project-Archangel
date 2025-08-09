from app.db import seen_delivery, upsert_event

def test_idempotent_delivery(tmp_path, monkeypatch):
    did = "evt_123"
    assert not seen_delivery(did)
    upsert_event(did, {"x": 1})
    assert seen_delivery(did)