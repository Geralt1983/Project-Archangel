import os
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Header, HTTPException, Query
from app.providers.clickup import ClickUpAdapter
from app.providers.trello import TrelloAdapter
from app.providers.todoist import TodoistAdapter
from app.triage_serena import triage_with_serena
from app.db_pg import save_task, upsert_event, seen_delivery, touch_task, map_upsert, map_get_internal, get_conn
from app.audit import log_event
from app.api_outbox import router as outbox_router
from app.api_memory import router as memory_router
from app.api_usage import router as usage_router

app = FastAPI()
app.include_router(outbox_router)
app.include_router(memory_router)
app.include_router(usage_router)

# Observability endpoints
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    # Use default global registry
    data = generate_latest()
    from fastapi.responses import Response
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

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
    from app.orchestrator import create_orchestrator, TaskContext, TaskState
    from app.utils.outbox import OutboxManager
    
    adapter = get_adapter(provider)
    t = triage_with_serena(task, provider=adapter.name)
    
    # Use new orchestrator for enhanced scoring and decision making
    orchestrator = create_orchestrator()
    task_context = TaskContext(
        id=t["id"],
        title=t.get("title", ""),
        description=t.get("description", ""),
        client=t.get("client", ""),
        provider=adapter.name,
        state=TaskState.PENDING,
        importance=t.get("importance", 3.0),
        urgency=0.5,
        value=0.6,
        time_sensitivity=0.5,
        sla_breach=0.3,
        client_recent_allocation=0.0,
        assignee_current_wip=2,
        age_hours=0.0,
        last_activity_hours=0.0,
        effort_hours=t.get("effort_hours", 1.0),
        deadline=datetime.fromisoformat(t["deadline"].replace("Z", "+00:00")) if t.get("deadline") else None,
        created_at=datetime.now(timezone.utc)
    )
    
    # Get orchestration decision
    decision = orchestrator.orchestrate_task(task_context)
    t["score"] = decision.score
    t["orchestration_meta"] = {
        "recommended_action": decision.recommended_action,
        "reasoning": decision.reasoning,
        "staleness_curve": decision.staleness_curve,
        "fairness_penalty": decision.fairness_penalty,
        "wip_enforcement": {
            "can_assign": decision.wip_enforcement.get("can_assign", True),
            "current_wip": decision.wip_enforcement.get("current_wip", 0),
            "limit": decision.wip_enforcement.get("limit", 3),
            "utilization": decision.wip_enforcement.get("utilization", 0.0)
        }
    }
    
    # Use outbox pattern for reliable task creation
    outbox = OutboxManager(get_conn)
    
    # Always enqueue first for exactly-once semantics
    idem_key = outbox.enqueue(
        operation_type="create_task",
        endpoint="/tasks",
        request={
            "task_data": t,
            "provider": adapter.name
        },
        provider=adapter.name
    )
    
    try:
        # Try immediate creation with fallback to worker
        created = adapter.create_task(t)
        external_id = created.get("id")
        
        # Enqueue follow-up operations
        if t.get("subtasks") and external_id:
            outbox.enqueue(
                operation_type="create_subtasks",
                endpoint=f"/tasks/{external_id}/subtasks",
                request={"parent_id": external_id, "subtasks": t["subtasks"]},
                provider=adapter.name
            )
        
        if t.get("checklist") and external_id:
            outbox.enqueue(
                operation_type="add_checklist",
                endpoint=f"/tasks/{external_id}/checklist",
                request={"task_id": external_id, "items": t["checklist"]},
                provider=adapter.name
            )
        
        t["external_id"] = external_id
        t["provider"] = adapter.name
        save_task(t)
        if external_id:
            map_upsert(adapter.name, external_id, t["id"])
        log_event("pushed", {"task_id": t["id"], "external_id": external_id, "provider": adapter.name})
        
    except Exception as e:
        # If immediate creation fails, outbox worker will retry
        log_event("outbox_fallback", {"task_id": t["id"], "error": str(e), "provider": adapter.name})
        
        t["external_id"] = None
        t["provider"] = adapter.name
        t["outbox_idempotency_key"] = idem_key
        save_task(t)
        
        external_id = None
    return {
        "id": t["id"], "provider": adapter.name, "external_id": external_id,
        "status": "triaged", "score": t["score"],
        "subtasks_created": len(t["subtasks"]), "checklist_items": len(t["checklist"]),
        "serena_policy": t.get("serena_meta", {}).get("policy", {}),
        "orchestration": decision.recommended_action,
        "reasoning": decision.reasoning[:3]  # Top 3 reasons
    }

@app.post("/triage/run")
async def triage_run(task: dict):
    return triage_with_serena(task, provider="clickup")

@app.post("/rebalance/run")
async def rebalance_run(available_hours_today: float = 5.0):
    from app.orchestrator import create_orchestrator, TaskContext, TaskState
    from app.db_pg import fetch_open_tasks
    from app.config import load_rules
    from app.scheduler import compute_fairness_deficits
    
    tasks = fetch_open_tasks()
    rules = load_rules()
    orchestrator = create_orchestrator()
    
    # Convert tasks to TaskContext objects
    task_contexts = []
    for t in tasks:
        task_context = TaskContext(
            id=t["id"],
            title=t.get("title", ""),
            description=t.get("description", ""),
            client=t.get("client", ""),
            provider=t.get("provider", "internal"),
            state=TaskState.PENDING,
            importance=t.get("importance", 3.0),
            urgency=0.5,
            value=0.6,
            time_sensitivity=0.5,
            sla_breach=0.3,
            client_recent_allocation=0.0,
            assignee_current_wip=2,
            age_hours=0.0,
            last_activity_hours=0.0,
            effort_hours=t.get("effort_hours", 1.0),
            deadline=datetime.fromisoformat(t["deadline"].replace("Z", "+00:00")) if t.get("deadline") else None,
            created_at=datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) if t.get("created_at") else datetime.now(timezone.utc)
        )
        task_contexts.append(task_context)
    
    # Use orchestrator for intelligent rebalancing
    rebalance_result = orchestrator.rebalance_workload(task_contexts)
    
    # FIX: Also compute fairness deficits for traditional planner
    fairness_deficits = compute_fairness_deficits(tasks, rules)
    from app.balancer import plan_today
    traditional_plan = plan_today(tasks, available_hours_today, fairness_deficits)
    
    return {
        "orchestration_mode": True,
        "available_hours": available_hours_today,
        "total_tasks": rebalance_result["total_tasks"],
        "prioritized_tasks": rebalance_result["prioritized_tasks"],
        "workload_distribution": rebalance_result["workload_distribution"],
        "rebalancing_suggestions": rebalance_result["rebalancing_suggestions"],
        "average_score": rebalance_result["average_score"],
        "fairness_deficits": fairness_deficits,
        "traditional_plan": traditional_plan,
        "plan": {
            client: [task["task_id"] for task in rebalance_result["prioritized_tasks"][:5] if task["task_id"]]
            for client in set(t.get("client", "internal") for t in tasks)
        }
    }

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

# Orchestrator Management Endpoints
@app.get("/orchestrator/config")
async def get_orchestrator_config():
    """Get current orchestrator configuration"""
    from app.orchestrator import create_orchestrator
    orchestrator = create_orchestrator()
    return {
        "scoring_weights": orchestrator.scoring_engine.weights,
        "staleness_config": {
            "threshold_hours": orchestrator.scoring_engine.staleness_threshold,
            "max_penalty": orchestrator.scoring_engine.staleness_max_penalty
        },
        "wip_limits": orchestrator.wip_enforcer.wip_limits,
        "load_balance_threshold": orchestrator.wip_enforcer.load_balance_threshold
    }

@app.post("/orchestrator/config")
async def update_orchestrator_config(config: dict):
    """Update orchestrator configuration"""
    # In a real implementation, this would update persistent configuration
    return {"ok": True, "updated_config": config}

@app.get("/orchestrator/stats")
async def orchestrator_stats():
    """Get orchestrator statistics"""
    from app.orchestrator import create_orchestrator
    from app.db_pg import fetch_open_tasks
    
    orchestrator = create_orchestrator()
    tasks = fetch_open_tasks()
    
    # Get score distribution
    scores = []
    for task in tasks[:100]:  # Sample for performance
        score = task.get("score", 0.0)
        scores.append(score)
    
    return {
        "total_scored_tasks": len(scores),
        "average_score": sum(scores) / len(scores) if scores else 0,
        "score_distribution": {
            "high_priority": len([s for s in scores if s >= 0.8]),
            "medium_priority": len([s for s in scores if 0.4 <= s < 0.8]),
            "low_priority": len([s for s in scores if s < 0.4])
        },
        "database_stats": {
            "db_path": str(orchestrator.state_manager.db_path),
            "tables_initialized": True
        }
    }

@app.post("/orchestrator/simulate")
async def simulate_orchestration(simulation_config: dict):
    """Simulate orchestration with different configurations"""
    from app.orchestrator import create_orchestrator, TaskContext, TaskState
    
    base_config = simulation_config.get("config", {})
    test_tasks = simulation_config.get("tasks", [])
    
    orchestrator = create_orchestrator(base_config)
    results = []
    
    for task_data in test_tasks[:50]:  # Limit for performance
        task_context = TaskContext(
            id=task_data.get("id", "test"),
            title=task_data.get("title", "Test Task"),
            description=task_data.get("description", ""),
            client=task_data.get("client", "test-client"),
            provider="simulation",
            state=TaskState.PENDING,
            importance=task_data.get("importance", 3.0),
            urgency=task_data.get("urgency", 0.5),
            value=task_data.get("value", 0.6),
            time_sensitivity=task_data.get("time_sensitivity", 0.5),
            sla_breach=task_data.get("sla_breach", 0.3),
            client_recent_allocation=0.0,
            assignee_current_wip=2,
            age_hours=task_data.get("age_hours", 0.0),
            last_activity_hours=0.0,
            effort_hours=task_data.get("effort_hours", 1.0)
        )
        
        decision = orchestrator.orchestrate_task(task_context)
        results.append({
            "task_id": task_context.id,
            "score": decision.score,
            "action": decision.recommended_action,
            "reasoning": decision.reasoning[:2]  # Top 2 reasons
        })
    
    return {
        "simulation_results": results,
        "average_score": sum(r["score"] for r in results) / len(results) if results else 0,
        "action_distribution": {
            action: len([r for r in results if r["action"] == action])
            for action in set(r["action"] for r in results)
        }
    }

@app.post("/providers/health")
async def provider_health_check():
    """Check health of all provider adapters"""
    from app.providers.adapter_framework import ProviderManager, create_provider_adapter
    import os
    
    manager = ProviderManager()
    
    # Register providers based on environment configuration
    providers_config = {
        "clickup": {
            "token": os.getenv("CLICKUP_TOKEN", ""),
            "team_id": os.getenv("CLICKUP_TEAM_ID", ""),
            "list_id": os.getenv("CLICKUP_LIST_ID", ""),
            "webhook_secret": os.getenv("CLICKUP_WEBHOOK_SECRET", "")
        }
    }
    
    for name, config in providers_config.items():
        if config.get("token"):  # Only register if configured
            adapter = create_provider_adapter(name, config)
            if adapter:
                manager.register_provider(adapter)
    
    health_results = await manager.health_check()
    provider_stats = await manager.get_provider_stats()
    
    return {
        "health_check": health_results,
        "provider_stats": provider_stats,
        "registered_providers": list(manager.providers.keys())
    }

# Outbox Management Endpoints are now in app/api_outbox.py router