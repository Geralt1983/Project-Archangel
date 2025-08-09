import os
from fastapi import FastAPI, Request, Header, HTTPException
from app.providers.clickup import ClickUpAdapter
from app.triage import triage
from app.db import save_task, upsert_event, seen_delivery
from app.audit import log_event

app = FastAPI()

adapter = ClickUpAdapter(
    token=os.getenv("CLICKUP_TOKEN",""),
    team_id=os.getenv("CLICKUP_TEAM_ID",""),
    list_id=os.getenv("CLICKUP_LIST_ID",""),
    webhook_secret=os.getenv("CLICKUP_WEBHOOK_SECRET",""),
)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/webhooks/clickup")
async def clickup_webhook(request: Request, x_signature: str = Header(None)):
    raw = await request.body()
    if not adapter.verify_webhook({"x-signature": x_signature or ""}, raw):
        raise HTTPException(401, "bad signature")
    event = await request.json()
    delivery_id = event.get("event_id") or event.get("delivery_id") or event.get("id") or ""
    if delivery_id and seen_delivery(delivery_id):
        return {"ok": True, "deduped": True}
    if delivery_id:
        upsert_event(delivery_id, event)
    log_event("webhook", {"provider": "clickup", "type": event.get("event")})
    return {"ok": True}

@app.post("/tasks/intake")
async def intake(task: dict):
    # triage and push to ClickUp
    t = triage(task)
    created = adapter.create_task(t)
    external_id = created.get("id")
    if t.get("subtasks"):
        adapter.create_subtasks(external_id, t["subtasks"])
    if t.get("checklist"):
        adapter.add_checklist(external_id, t["checklist"])
    t["external_id"] = external_id
    t["provider"] = adapter.name
    save_task(t)
    log_event("pushed", {"task_id": t["id"], "external_id": external_id})
    return {
        "id": t["id"], "provider": adapter.name, "external_id": external_id,
        "status": "triaged", "score": t["score"],
        "subtasks_created": len(t["subtasks"]), "checklist_items": len(t["checklist"])
    }

@app.post("/triage/run")
async def triage_run(task: dict):
    return triage(task)

@app.post("/rebalance/run")
async def rebalance_run():
    # simple placeholder: recompute scores daily or per call
    from app.scheduler import daily_reeval
    daily_reeval()
    return {"ok": True}