import os
import uuid
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models import TaskIntake, TriageResponse, Task
from .triage import triage_and_push, retriage_task
from .db import upsert_event, seen_delivery, get_task, fetch_open_tasks, log_audit_event
from .providers.clickup import ClickUpAdapter
from .providers.base import ProviderAdapter
from .scheduler import rebalance_tasks

# Initialize FastAPI app
app = FastAPI(
    title="Project Archangel",
    description="Intelligent Task Orchestrator",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize provider adapter
def get_provider_adapter() -> ProviderAdapter:
    """Get the configured provider adapter."""
    # For now, only ClickUp is supported
    return ClickUpAdapter(
        token=os.getenv("CLICKUP_TOKEN", ""),
        team_id=os.getenv("CLICKUP_TEAM_ID", ""),
        list_id=os.getenv("CLICKUP_LIST_ID", ""),
        webhook_secret=os.getenv("CLICKUP_WEBHOOK_SECRET", "")
    )

# Request models
class RebalanceRequest(BaseModel):
    dry_run: bool = False
    client_filter: Optional[str] = None

class TriageRequest(BaseModel):
    task_id: Optional[str] = None
    retriage_all: bool = False

# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "project-archangel"}

# Task intake endpoint
@app.post("/tasks/intake", response_model=TriageResponse)
async def intake_task(task_input: TaskIntake, request: Request):
    """Accept and process a new task through the triage pipeline."""
    request_id = str(uuid.uuid4())
    
    try:
        # Get provider adapter
        adapter = get_provider_adapter()
        
        # Run triage pipeline
        result = triage_and_push(task_input, adapter, request_id)
        
        return result
        
    except Exception as e:
        # Log the error
        log_audit_event(
            event_type="intake_failed",
            data={"error": str(e), "task_title": task_input.title},
            request_id=request_id
        )
        raise HTTPException(status_code=500, detail=f"Triage failed: {str(e)}")

# Webhook endpoints
@app.post("/webhooks/clickup")
async def clickup_webhook(request: Request, x_signature: Optional[str] = Header(None)):
    """Handle ClickUp webhook events."""
    adapter = get_provider_adapter()
    
    # Get raw body for signature verification
    raw_body = await request.body()
    
    # Verify webhook signature
    headers = dict(request.headers)
    if not adapter.verify_webhook(headers, raw_body):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Parse the event
    try:
        event_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Check for duplicate delivery
    delivery_id = event_data.get("event_id") or event_data.get("delivery_id")
    if delivery_id and seen_delivery(delivery_id):
        return {"status": "duplicate", "delivery_id": delivery_id}
    
    # Store the webhook event
    webhook_event = upsert_event(delivery_id, event_data)
    
    # Process specific event types
    event_type = event_data.get("event", "")
    
    if event_type in ["taskCreated", "taskUpdated", "taskStatusUpdated"]:
        # Handle task updates
        task_data = event_data.get("task", {})
        external_id = task_data.get("id")
        
        if external_id:
            # Find our task by external ID and update if needed
            task = get_task_by_external_id(external_id)
            if task:
                # Log the webhook event
                log_audit_event(
                    event_type="webhook_received",
                    task_id=task.id,
                    external_id=external_id,
                    provider="clickup",
                    data={"event_type": event_type, "webhook_id": str(webhook_event.id)}
                )
    
    return {"status": "processed", "event_id": delivery_id}

# Triage management endpoints
@app.post("/triage/run")
async def run_triage(triage_request: TriageRequest):
    """Re-run triage for specific tasks or all new tasks."""
    adapter = get_provider_adapter()
    results = []
    
    if triage_request.task_id:
        # Retriage specific task
        try:
            result = retriage_task(triage_request.task_id, adapter)
            results.append(result)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    elif triage_request.retriage_all:
        # Retriage all open tasks
        tasks = fetch_open_tasks()
        for task in tasks:
            try:
                result = retriage_task(task.id, adapter)
                results.append(result)
            except Exception as e:
                # Log error but continue with other tasks
                log_audit_event(
                    event_type="retriage_failed",
                    task_id=task.id,
                    data={"error": str(e)}
                )
    
    return {"processed": len(results), "results": results}

# Rebalancing endpoint
@app.post("/rebalance/run")
async def run_rebalance(rebalance_request: RebalanceRequest):
    """Execute load balancing across clients and tasks."""
    try:
        result = rebalance_tasks(
            dry_run=rebalance_request.dry_run,
            client_filter=rebalance_request.client_filter
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rebalancing failed: {str(e)}")

# Task query endpoints
@app.get("/tasks/{task_id}")
async def get_task_endpoint(task_id: str):
    """Get a specific task by ID."""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/tasks")
async def list_tasks(
    client: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """List tasks with optional filtering."""
    from .db import fetch_tasks_by_client
    
    if client:
        tasks = fetch_tasks_by_client(client)
    else:
        tasks = fetch_open_tasks()
    
    # Apply status filter if provided
    if status:
        tasks = [t for t in tasks if t.status.value == status]
    
    # Apply limit
    tasks = tasks[:limit]
    
    return {"tasks": tasks, "count": len(tasks)}

# Configuration endpoints
@app.get("/config/rules")
async def get_rules():
    """Get current rules configuration."""
    from .config import load_rules
    return load_rules()

@app.post("/config/reload")
async def reload_config():
    """Reload configuration from files."""
    from .config import reload_rules
    reload_rules()
    return {"status": "reloaded"}

# Stats endpoint
@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    from .db import SessionLocal, TaskDB, AuditEventDB
    
    db = SessionLocal()
    try:
        total_tasks = db.query(TaskDB).count()
        open_tasks = db.query(TaskDB).filter(TaskDB.status != "done").count()
        total_events = db.query(AuditEventDB).count()
        
        # Tasks by status
        status_counts = {}
        for status in ["new", "triaged", "in_progress", "blocked", "done"]:
            count = db.query(TaskDB).filter(TaskDB.status == status).count()
            status_counts[status] = count
        
        # Tasks by client
        from sqlalchemy import func
        client_counts = dict(
            db.query(TaskDB.client, func.count(TaskDB.id))
            .group_by(TaskDB.client)
            .all()
        )
        
        return {
            "total_tasks": total_tasks,
            "open_tasks": open_tasks,
            "total_audit_events": total_events,
            "tasks_by_status": status_counts,
            "tasks_by_client": client_counts
        }
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)