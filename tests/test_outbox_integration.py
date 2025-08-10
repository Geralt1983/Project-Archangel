import os
import time
from datetime import datetime, timezone
from app.db_pg import init, get_conn
from app.utils.outbox import OutboxManager, make_idempotency_key

def _flush():
    conn = get_conn()
    with conn.cursor() as c:
        c.execute("delete from outbox")

def test_outbox_happy_path(monkeypatch):
    os.environ.setdefault("DATABASE_URL", "postgresql://archangel:archangel@localhost:5432/archangel")
    init()
    _flush()
    ob = OutboxManager(get_conn)

    # enqueue one op
    req = {"task_id": "t1", "comment": "hello"}
    idem = make_idempotency_key("add_comment", "/providers/clickup/comment", req)
    ob.enqueue("add_comment", "/providers/clickup/comment", req, headers={"Idempotency-Key": idem}, idempotency_key=idem)
    stats = ob.get_stats()
    assert stats.get("pending", 0) == 1

    # monkeypatch a dispatcher through a simple local function
    called = {"n": 0}
    def fake_dispatch(op_type, endpoint, payload, headers):
        assert headers.get("Idempotency-Key") == idem
        called["n"] += 1
        return None

    # inline worker loop
    batch = ob.pick_batch(limit=5)
    assert len(batch) == 1
    for op in batch:
        ob.mark_inflight(op.id)
        fake_dispatch(op.operation_type, op.endpoint, op.request, op.headers)
        ob.mark_delivered(op.id)

    stats2 = ob.get_stats()
    assert stats2.get("delivered", 0) == 1
    assert called["n"] == 1

def test_outbox_retry_then_dead(monkeypatch):
    os.environ.setdefault("DATABASE_URL", "postgresql://archangel:archangel@localhost:5432/archangel")
    init()
    _flush()
    ob = OutboxManager(get_conn)

    req = {"task_id": "t2"}
    ob.enqueue("create_task", "/providers/trello/create", req)

    # fail 3 times then dead letter
    batch = ob.pick_batch(limit=1)
    assert batch, "expected one item"
    op = batch[0]
    ob.mark_inflight(op.id)
    ob.mark_failed(op.id, retry_in_seconds=0, error="boom1")
    # pick again (eligible now)
    batch = ob.pick_batch(limit=1)
    op = batch[0]
    ob.mark_inflight(op.id)
    ob.mark_failed(op.id, retry_in_seconds=0, error="boom2")
    # third attempt exceeds max in this test, dead
    batch = ob.pick_batch(limit=1)
    op = batch[0]
    ob.dead_letter(op.id, "permanent")

    stats = ob.get_stats()
    assert stats.get("dead", 0) == 1