import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .models import Task, TaskIntake, TaskStatus, TriageResponse
from .scoring import compute_score
from .subtasks import build_checklist_and_subtasks
from .db import save_task, log_audit_event
from .config import load_rules, get_task_type_config, get_client_config
from .providers.base import ProviderAdapter

def triage_and_push(task_input: TaskIntake, adapter: ProviderAdapter, 
                   request_id: Optional[str] = None) -> TriageResponse:
    """
    Main triage pipeline: normalize → classify → score → generate → push → audit.
    """
    # Step 1: Normalize input into full Task model
    task = normalize_task_input(task_input)
    
    # Step 2: Classify task type and client
    classify_task(task)
    
    # Step 3: Fill in defaults based on rules
    fill_task_defaults(task)
    
    # Step 4: Compute priority score
    rules = load_rules()
    task.score = compute_score(task, rules)
    
    # Step 5: Generate checklist and subtasks
    checklist, subtasks = build_checklist_and_subtasks(task, rules)
    task.checklist = checklist
    task.subtasks = subtasks
    
    # Step 6: Push to provider
    try:
        # Create main task
        created_task = adapter.create_task(task)
        external_id = created_task.get("id")
        
        if not external_id:
            raise ValueError("Provider did not return task ID")
        
        task.external_id = external_id
        task.provider = adapter.name
        task.status = TaskStatus.TRIAGED
        
        # Create subtasks
        subtasks_created = []
        if subtasks and adapter.supports_subtasks():
            subtasks_created = adapter.create_subtasks(external_id, subtasks)
        
        # Add checklist
        if checklist and adapter.supports_checklists():
            adapter.add_checklist(external_id, checklist)
        
        # Step 7: Save to database
        save_task(task)
        
        # Step 8: Audit logging
        log_audit_event(
            event_type="task_created",
            task_id=task.id,
            external_id=external_id,
            provider=adapter.name,
            data={
                "task_type": task.task_type,
                "score": task.score,
                "subtasks_count": len(subtasks_created),
                "checklist_count": len(checklist)
            },
            request_id=request_id
        )
        
        return TriageResponse(
            id=task.id,
            provider=adapter.name,
            external_id=external_id,
            status=task.status.value,
            task_type=task.task_type,
            score=task.score,
            subtasks_created=len(subtasks_created),
            checklist_items=len(checklist)
        )
        
    except Exception as e:
        # Log failure
        log_audit_event(
            event_type="task_creation_failed",
            task_id=task.id,
            provider=adapter.name,
            data={"error": str(e), "task_title": task.title},
            request_id=request_id
        )
        raise

def normalize_task_input(task_input: TaskIntake) -> Task:
    """Convert TaskIntake to full Task model with generated ID."""
    # Generate unique task ID
    task_id = f"tsk_{uuid.uuid4().hex[:8]}"
    
    # Generate idempotency key
    idempotency_key = f"{task_input.source}_{hash(task_input.title)}_{task_input.client}"
    
    now = datetime.now(timezone.utc)
    
    return Task(
        id=task_id,
        title=task_input.title.strip(),
        description=task_input.description.strip() if task_input.description else "",
        client=task_input.client.lower().strip(),
        project=task_input.project,
        deadline=task_input.deadline,
        importance=task_input.importance,
        effort_hours=task_input.effort_hours,
        labels=task_input.labels.copy(),
        source=task_input.source,
        meta=task_input.meta.copy(),
        created_at=now,
        updated_at=now,
        idempotency_key=idempotency_key,
        recent_progress=0.0  # New tasks have no progress
    )

def classify_task(task: Task) -> None:
    """
    Classify task type based on title and description content.
    Uses simple keyword matching - could be enhanced with ML.
    """
    title_lower = task.title.lower()
    description_lower = (task.description or "").lower()
    combined_text = f"{title_lower} {description_lower}"
    
    # Check for explicit client prefix in title like [ACME]
    if task.client == "unknown":
        import re
        client_match = re.search(r'\[(\w+)\]', task.title)
        if client_match:
            task.client = client_match.group(1).lower()
            # Remove client prefix from title
            task.title = re.sub(r'\[\w+\]\s*', '', task.title).strip()
    
    # Classify task type
    if any(keyword in combined_text for keyword in ["fix", "error", "fail", "bug", "500", "broken", "crash"]):
        task.task_type = "bugfix"
    elif any(keyword in combined_text for keyword in ["report", "analysis", "dashboard", "metrics", "data"]):
        task.task_type = "report"
    elif any(keyword in combined_text for keyword in ["setup", "onboard", "access", "provision", "install", "configure"]):
        task.task_type = "onboarding"
    else:
        task.task_type = "general"

def fill_task_defaults(task: Task) -> None:
    """Fill in default values based on task type and client configuration."""
    # Get configuration for task type
    task_type_config = get_task_type_config(task.task_type)
    client_config = get_client_config(task.client)
    
    # Set default effort hours if not provided
    if not task.effort_hours:
        task.effort_hours = task_type_config.get("default_effort_hours", 2.0)
    
    # Set default importance if not provided or invalid
    if not task.importance or task.importance < 1 or task.importance > 5:
        task.importance = task_type_config.get("importance", 3)
    
    # Add task type labels
    task_type_labels = task_type_config.get("labels", [])
    task.labels.extend([label for label in task_type_labels if label not in task.labels])
    
    # Set client SLA hours
    if not task.client_sla_hours:
        task.client_sla_hours = client_config.get("sla_hours", 72)

def retriage_task(task_id: str, adapter: ProviderAdapter) -> TriageResponse:
    """Re-run triage for an existing task."""
    from .db import get_task
    
    task = get_task(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")
    
    # Re-classify and re-score
    classify_task(task)
    fill_task_defaults(task)
    task.score = compute_score(task)
    
    # Update in provider if it exists
    if task.external_id and adapter.name == task.provider:
        try:
            # Update status if needed
            adapter.update_status(task.external_id, task.status.value)
        except Exception as e:
            log_audit_event(
                event_type="retriage_failed",
                task_id=task.id,
                external_id=task.external_id,
                provider=adapter.name,
                data={"error": str(e)}
            )
            raise
    
    # Save updated task
    save_task(task)
    
    log_audit_event(
        event_type="task_retriaged",
        task_id=task.id,
        external_id=task.external_id,
        provider=task.provider,
        data={"new_score": task.score, "task_type": task.task_type}
    )
    
    return TriageResponse(
        id=task.id,
        provider=task.provider,
        external_id=task.external_id or "",
        status=task.status.value,
        task_type=task.task_type,
        score=task.score,
        subtasks_created=len(task.subtasks),
        checklist_items=len(task.checklist)
    )