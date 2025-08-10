from app.db_pg import seen_delivery, upsert_event, map_upsert, map_get_internal

def test_idempotent_delivery(tmp_path, monkeypatch):
    did = "evt_123"
    assert not seen_delivery(did)
    upsert_event(did, {"x": 1})
    assert seen_delivery(did)

def test_map_roundtrip(monkeypatch):
    map_upsert("clickup", "ext_1", "tsk_abc")
    assert map_get_internal("clickup", "ext_1") == "tsk_abc"