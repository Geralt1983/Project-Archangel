import os
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Header, HTTPException, Query
from app.providers.clickup import ClickUpAdapter
from app.providers.trello import TrelloAdapter
from app.providers.todoist import TodoistAdapter
from app.triage_serena import triage_with_serena
from app.db_pg import save_task, upsert_event, seen_delivery, touch_task, map_upsert, map_get_internal
from app.audit import log_event

app = FastAPI()

def clickup():
    return ClickUpAdapter(
        token=os.getenv("CLICKUP_TOKEN",""),
        team_id=os.getenv("CLICKUP_TEAM_ID",""),
        list_id=os.getenv("CLICKUP_LIST_ID",""),
        webhook_secret=os.getenv("CLICKUP_WEBHOOK_SECRET",""),
    )

def trello():
    return TrelloAdapter(
        key=os.getenv("TRELLO_KEY",""),
        token=os.getenv("TRELLO_TOKEN",""),
        webhook_secret=os.getenv("TRELLO_WEBHOOK_SECRET",""),
        list_id=os.getenv("TRELLO_LIST_ID",""),
    )

def todoist():
    return TodoistAdapter(
        token=os.getenv("TODOIST_TOKEN",""),
        webhook_secret=os.getenv("TODOIST_WEBHOOK_SECRET",""),
        project_id=os.getenv("TODOIST_PROJECT_ID",""),
    )

ADAPTERS = {"clickup": clickup, "trello": trello, "todoist": todoist}

def get_adapter(name: str):
    return ADAPTERS.get(name, clickup)()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/webhooks/clickup")
async def clickup_webhook(request: Request):
    adapter = clickup()
    raw = await request.body()
    headers = dict(request.headers)
    
    # ClickUp sends X-Signature header (FastAPI converts to lowercase)
    signature = headers.get("x-signature", "")
    
    if not adapter.verify_webhook({"x-signature": signature}, raw):
        raise HTTPException(401, "bad signature")
    event = await request.json()
    delivery_id = event.get("event_id") or event.get("delivery_id") or event.get("id") or ""
    if delivery_id and seen_delivery(delivery_id):
        return {"ok": True, "deduped": True}
    if delivery_id:
        upsert_event(delivery_id, event)

    # find external task id in ClickUp payloads
    ext = (
        event.get("task_id")
        or event.get("task", {}).get("id")
        or (event.get("history_items", [{}])[0] or {}).get("task_id")
    )
    if ext:
        internal = map_get_internal("clickup", str(ext))
        if internal:
            touch_task(internal, datetime.now(timezone.utc).isoformat())
    log_event("webhook", {"provider": "clickup", "type": event.get("event")})
    return {"ok": True}

@app.post("/webhooks/trello")
async def trello_webhook(request: Request, x_trello_webhook: str = Header(None)):
    adapter = trello()
    raw = await request.body()
    if not adapter.verify_webhook({"x-trello-webhook": x_trello_webhook or ""}, raw):
        raise HTTPException(401, "bad signature")
    event = await request.json()
    delivery_id = event.get("id") or ""
    if delivery_id and seen_delivery(delivery_id):
        return {"ok": True, "deduped": True}
    if delivery_id:
        upsert_event(delivery_id, event)
    log_event("webhook", {"provider": "trello", "type": event.get("type")})
    return {"ok": True}

@app.post("/webhooks/todoist")
async def todoist_webhook(request: Request, x_todoist_hmac_sha256: str = Header(None)):
    adapter = todoist()
    raw = await request.body()
    if not adapter.verify_webhook({"x-todoist-hmac-sha256": x_todoist_hmac_sha256 or ""}, raw):
        raise HTTPException(401, "bad signature")
    event = await request.json()
    delivery_id = event.get("event_id") or ""
    if delivery_id and seen_delivery(delivery_id):
        return {"ok": True, "deduped": True}
    if delivery_id:
        upsert_event(delivery_id, event)
    log_event("webhook", {"provider": "todoist", "type": event.get("event_name")})
    return {"ok": True}

@app.post("/tasks/intake")
async def intake(task: dict, provider: str = Query("clickup")):
    adapter = get_adapter(provider)
    t = triage_with_serena(task, provider=adapter.name)
    created = adapter.create_task(t)
    external_id = created.get("id")
    if t.get("subtasks"):
        adapter.create_subtasks(external_id, t["subtasks"])
    if t.get("checklist"):
        adapter.add_checklist(external_id, t["checklist"])
    t["external_id"] = external_id
    t["provider"] = adapter.name
    save_task(t)
    if external_id:
        map_upsert(adapter.name, external_id, t["id"])
    log_event("pushed", {"task_id": t["id"], "external_id": external_id, "provider": adapter.name})
    return {
        "id": t["id"], "provider": adapter.name, "external_id": external_id,
        "status": "triaged", "score": t["score"],
        "subtasks_created": len(t["subtasks"]), "checklist_items": len(t["checklist"]),
        "serena_policy": t.get("serena_meta", {}).get("policy", {})
    }

@app.post("/triage/run")
async def triage_run(task: dict):
    return triage_with_serena(task, provider="clickup")

@app.post("/rebalance/run")
async def rebalance_run(available_hours_today: float = 5.0):
    from app.mcp_client import rebalance_call
    from app.db_pg import fetch_open_tasks
    from app.config import load_rules
    from app.balancer import plan_today
    
    tasks = fetch_open_tasks()
    rules = load_rules()
    payload = {
        "tasks": [
            {"id": t["id"], "client": t.get("client",""), "score": t.get("score",0.0),
             "effort_hours": t.get("effort_hours",1.0), "deadline": t.get("deadline")}
            for t in tasks
        ],
        "constraints": {
            "available_hours_today": available_hours_today,
            "client_caps": {c: cfg.get("daily_cap_hours", 2) for c, cfg in rules.get("clients",{}).items()},
            "override_urgent_within_hours": 24
        }
    }
    if _serena_enabled():
        res = rebalance_call(payload)
        if res and "plan" in res:
            return res
    # fallback to local planner
    return {"plan": plan_today(tasks, available_hours_today)}

def _serena_enabled():
    import os
    return os.getenv("SERENA_ENABLED","true").lower() == "true"

@app.get("/weekly")
async def weekly_summary():
    from app.scheduler import weekly_checkins
    return weekly_checkins()

@app.post("/providers/clickup/webhooks/create")
def clickup_webhook_create():
    base = os.getenv("PUBLIC_BASE_URL","").rstrip("/")
    if not base:
        raise HTTPException(400, "set PUBLIC_BASE_URL")
    cb = f"{base}/webhooks/clickup"
    cu = clickup()
    res = cu.create_webhook(cb)
    return {"ok": True, "webhook": res, "callback": cb}

@app.post("/checkins/weekly/run")
def run_weekly_checkin():
    from app.scheduler import weekly_checkins
    return weekly_checkins()

@app.post("/nudges/stale/run")
def run_stale_nudges():
    from app.scheduler import hourly_stale_nudge
    return hourly_stale_nudge()

@app.get("/tasks/map/{provider}/{external_id}")
def get_map(provider: str, external_id: str):
    internal = map_get_internal(provider, external_id)
    return {"provider": provider, "external_id": external_id, "internal_id": internal}

@app.get("/audit/export")
def audit_export(limit: int = 500):
    # return recent task decisions for Serena learning
    from app.db_pg import fetch_open_tasks
    # you can extend to include closed tasks and outcomes
    data = fetch_open_tasks()[:limit]
    return {"tasks": data}

@app.post("/audit/outcomes")
def record_outcomes(items: list[dict]):
    # items: [{task_id, result, time_spent_hours, satisfaction, reopened}]
    # store to a new table if you want model feedback
    return {"ok": True}