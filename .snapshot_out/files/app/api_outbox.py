from fastapi import APIRouter
from app.db_pg import init, get_conn
from app.utils.outbox import OutboxManager

router = APIRouter(prefix="/outbox", tags=["outbox"])


@router.get("/stats")
def outbox_stats():
    init()
    ob = OutboxManager(get_conn)
    stats = ob.get_stats()
    total = sum(stats.values()) if stats else 0
    return {"stats": stats, "total": total}


@router.post("/process")
def outbox_process(limit: int = 10):
    init()
    ob = OutboxManager(get_conn)
    batch = ob.pick_batch(limit=limit)
    processed = len(batch)
    # Note: this only reserves items. For real processing, run outbox_worker.py
    return {"picked": processed, "note": "Run outbox_worker.py to execute operations"}