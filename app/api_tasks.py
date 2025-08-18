"""
FastAPI Task CRUD Operations
Comprehensive REST API for task management with Project Archangel
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Path, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from app.models import Task, TaskIntake, TaskStatus, Subtask
from app.db_pg import (
    save_task, fetch_open_tasks, get_conn, touch_task, 
    map_upsert, map_get_internal
)
from app.orchestrator import (
    create_orchestrator, TaskContext, TaskState, OrchestrationDecision
)
from app.scoring import compute_score
from app.triage_serena import triage_with_serena
from app.audit import log_event
from app.utils.outbox import OutboxManager
from app.providers.base import ProviderAdapter

# Configure logging
logger = logging.getLogger(__name__)

# Create router for task endpoints
router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

# Response models
class TaskResponse(BaseModel):
    """Standard task response model"""
    id: str
    title: str
    description: str = ""
    client: str
    project: Optional[str] = None
    task_type: Optional[str] = None
    deadline: Optional[datetime] = None
    importance: int = Field(ge=1, le=5)
    effort_hours: Optional[float] = Field(ge=0)
    labels: List[str] = Field(default_factory=list)
    source: str = "api"
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    score: Optional[float] = Field(ge=0.0, le=1.0)
    status: str = "pending"
    external_id: Optional[str] = None
    provider: Optional[str] = None
    checklist: List[str] = Field(default_factory=list)
    subtasks: List[Subtask] = Field(default_factory=list)
    orchestration_meta: Optional[Dict[str, Any]] = None

class TaskCreateRequest(BaseModel):
    """Task creation request model"""
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default="", max_length=2000)
    client: str = Field(min_length=1, max_length=100)
    project: Optional[str] = Field(default=None, max_length=100)
    task_type: Optional[str] = Field(default="general", max_length=50)
    deadline: Optional[datetime] = None
    importance: int = Field(default=3, ge=1, le=5)
    effort_hours: Optional[float] = Field(default=1.0, ge=0.1, le=100.0)
    labels: List[str] = Field(default_factory=list, max_items=10)
    meta: Dict[str, Any] = Field(default_factory=dict)
    checklist: List[str] = Field(default_factory=list, max_items=20)
    subtasks: List[Dict[str, Any]] = Field(default_factory=list, max_items=10)
    provider: Optional[str] = Field(default="internal", max_length=50)
    use_triage: bool = Field(default=True)
    use_orchestration: bool = Field(default=True)

class TaskUpdateRequest(BaseModel):
    """Task update request model"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    client: Optional[str] = Field(default=None, min_length=1, max_length=100)
    project: Optional[str] = Field(default=None, max_length=100)
    task_type: Optional[str] = Field(default=None, max_length=50)
    deadline: Optional[datetime] = None
    importance: Optional[int] = Field(default=None, ge=1, le=5)
    effort_hours: Optional[float] = Field(default=None, ge=0.1, le=100.0)
    labels: Optional[List[str]] = Field(default=None, max_items=10)
    meta: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(default=None, max_length=20)
    recent_progress: Optional[float] = Field(default=None, ge=0.0, le=1.0)

class TaskListResponse(BaseModel):
    """Task list response with pagination"""
    tasks: List[TaskResponse]
    total: int
    page: int
    size: int
    has_next: bool
    filters_applied: Dict[str, Any] = Field(default_factory=dict)

class TaskStatsResponse(BaseModel):
    """Task statistics response"""
    total_tasks: int
    by_status: Dict[str, int]
    by_client: Dict[str, int] 
    by_provider: Dict[str, int]
    score_distribution: Dict[str, int]
    average_score: float
    high_priority_count: int
    overdue_count: int

# Utility functions
def get_provider_adapter(provider_name: str) -> Optional[ProviderAdapter]:
    """Get provider adapter by name"""
    from app.api import ADAPTERS
    try:
        adapter_factory = ADAPTERS.get(provider_name)
        if adapter_factory:
            return adapter_factory()
        return None
    except Exception as e:
        logger.warning(f"Failed to get adapter for {provider_name}: {e}")
        return None

def apply_orchestration(task_data: Dict[str, Any], use_orchestration: bool = True) -> Dict[str, Any]:
    """Apply orchestration logic to task data"""
    if not use_orchestration:
        return task_data
    
    try:
        orchestrator = create_orchestrator()
        task_context = TaskContext(
            id=task_data["id"],
            title=task_data.get("title", ""),
            description=task_data.get("description", ""),
            client=task_data.get("client", ""),
            provider=task_data.get("provider", "internal"),
            state=TaskState.PENDING,
            importance=task_data.get("importance", 3.0),
            urgency=0.5,
            value=0.6,
            time_sensitivity=0.5,
            sla_breach=0.3,
            client_recent_allocation=0.0,
            assignee_current_wip=2,
            age_hours=0.0,
            last_activity_hours=0.0,
            effort_hours=task_data.get("effort_hours", 1.0),
            deadline=task_data.get("deadline"),
            created_at=datetime.now(timezone.utc)
        )
        
        decision = orchestrator.orchestrate_task(task_context)
        task_data["score"] = decision.score
        task_data["orchestration_meta"] = {
            "recommended_action": decision.recommended_action,
            "reasoning": decision.reasoning,
            "staleness_curve": decision.staleness_curve,
            "fairness_penalty": decision.fairness_penalty,
            "wip_enforcement": decision.wip_enforcement,
            "timestamp": decision.timestamp.isoformat()
        }
        
        logger.debug(f"Applied orchestration to task {task_data['id']}: score={decision.score}")
        
    except Exception as e:
        logger.error(f"Orchestration failed for task {task_data.get('id', 'unknown')}: {e}")
        # Fallback to basic scoring
        task_data["score"] = min(1.0, task_data.get("importance", 3.0) / 5.0)
        task_data["orchestration_meta"] = {"error": str(e)}
    
    return task_data

def convert_to_task_response(task_data: Dict[str, Any]) -> TaskResponse:
    """Convert internal task data to TaskResponse model"""
    try:
        # Parse datetime fields if they're strings
        created_at = task_data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.now(timezone.utc)
            
        updated_at = task_data.get("updated_at") 
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        elif updated_at is None:
            updated_at = created_at
            
        deadline = task_data.get("deadline")
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        
        # Parse subtasks
        subtasks = []
        for st in task_data.get("subtasks", []):
            if isinstance(st, dict):
                subtasks.append(Subtask(**st))
            elif isinstance(st, str):
                subtasks.append(Subtask(title=st))
        
        return TaskResponse(
            id=task_data["id"],
            title=task_data.get("title", ""),
            description=task_data.get("description", ""),
            client=task_data.get("client", "unknown"),
            project=task_data.get("project"),
            task_type=task_data.get("task_type"),
            deadline=deadline,
            importance=task_data.get("importance", 3),
            effort_hours=task_data.get("effort_hours", 1.0),
            labels=task_data.get("labels", []),
            source=task_data.get("source", "api"),
            meta=task_data.get("meta", {}),
            created_at=created_at,
            updated_at=updated_at,
            score=task_data.get("score"),
            status=task_data.get("status", "pending"),
            external_id=task_data.get("external_id"),
            provider=task_data.get("provider"),
            checklist=task_data.get("checklist", []),
            subtasks=subtasks,
            orchestration_meta=task_data.get("orchestration_meta")
        )
    except Exception as e:
        logger.error(f"Failed to convert task data to response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task data conversion error: {str(e)}"
        )

# CRUD Endpoints

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task_request: TaskCreateRequest) -> TaskResponse:
    """
    Create a new task with optional triage and orchestration
    
    - **title**: Task title (required)
    - **client**: Client identifier (required) 
    - **description**: Detailed description
    - **importance**: Priority level 1-5
    - **effort_hours**: Estimated effort
    - **deadline**: Due date
    - **use_triage**: Apply Serena triage logic
    - **use_orchestration**: Apply orchestration scoring
    """
    try:
        # Generate task ID and timestamps
        task_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        # Build base task data
        task_data = {
            "id": task_id,
            "title": task_request.title,
            "description": task_request.description or "",
            "client": task_request.client,
            "project": task_request.project,
            "task_type": task_request.task_type or "general",
            "deadline": task_request.deadline.isoformat() if task_request.deadline else None,
            "importance": task_request.importance,
            "effort_hours": task_request.effort_hours or 1.0,
            "labels": task_request.labels,
            "source": "api",
            "meta": task_request.meta,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "status": "pending",
            "provider": task_request.provider or "internal",
            "checklist": task_request.checklist,
            "subtasks": task_request.subtasks,
            "recent_progress": 0.0
        }
        
        # Apply triage if requested
        if task_request.use_triage:
            try:
                task_data = triage_with_serena(task_data, provider=task_data["provider"])
                logger.info(f"Applied triage to task {task_id}")
            except Exception as e:
                logger.warning(f"Triage failed for task {task_id}: {e}")
        
        # Apply orchestration if requested
        if task_request.use_orchestration:
            task_data = apply_orchestration(task_data, True)
        
        # Save to database
        save_task(task_data)
        
        # Handle provider integration if external provider specified
        external_id = None
        if task_request.provider and task_request.provider != "internal":
            adapter = get_provider_adapter(task_request.provider)
            if adapter:
                try:
                    # Use outbox pattern for reliable delivery
                    outbox = OutboxManager(get_conn)
                    outbox.enqueue(
                        operation_type="create_task",
                        endpoint="/tasks",
                        request={"task_data": task_data, "provider": task_request.provider}
                    )
                    
                    # Try immediate creation
                    created = adapter.create_task(task_data)
                    external_id = created.get("id")
                    
                    if external_id:
                        map_upsert(task_request.provider, external_id, task_id)
                        task_data["external_id"] = external_id
                        save_task(task_data)  # Update with external_id
                        
                except Exception as e:
                    logger.warning(f"Provider integration failed for task {task_id}: {e}")
                    # Task is saved locally, outbox will retry provider creation
        
        # Log creation event
        log_event("task_created", {
            "task_id": task_id,
            "client": task_data["client"],
            "provider": task_data["provider"],
            "external_id": external_id,
            "use_triage": task_request.use_triage,
            "use_orchestration": task_request.use_orchestration
        })
        
        return convert_to_task_response(task_data)
        
    except ValidationError as e:
        logger.error(f"Task creation validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Task creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task creation failed: {str(e)}"
        )

@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    client: Optional[str] = Query(None, description="Filter by client"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    status: Optional[str] = Query(None, description="Filter by status"),
    importance: Optional[int] = Query(None, ge=1, le=5, description="Filter by importance"),
    has_deadline: Optional[bool] = Query(None, description="Filter by deadline presence"),
    overdue_only: bool = Query(False, description="Show only overdue tasks"),
    sort_by: str = Query("score", regex="^(score|created_at|deadline|importance|updated_at)$"),
    sort_desc: bool = Query(True, description="Sort descending")
) -> TaskListResponse:
    """
    List tasks with filtering, sorting, and pagination
    
    - **page**: Page number (starts at 1)
    - **size**: Number of tasks per page (max 100)
    - **client**: Filter by client name
    - **provider**: Filter by provider
    - **status**: Filter by task status  
    - **importance**: Filter by importance level
    - **has_deadline**: Filter tasks with/without deadlines
    - **overdue_only**: Show only overdue tasks
    - **sort_by**: Sort field (score, created_at, deadline, importance, updated_at)
    - **sort_desc**: Sort in descending order
    """
    try:
        # Get all open tasks (this would be optimized with proper SQL queries in production)
        all_tasks = fetch_open_tasks()
        now = datetime.now(timezone.utc)
        
        # Apply filters
        filtered_tasks = []
        filters_applied = {}
        
        for task in all_tasks:
            # Client filter
            if client and task.get("client") != client:
                continue
            
            # Provider filter  
            if provider and task.get("provider") != provider:
                continue
                
            # Status filter
            if status and task.get("status") != status:
                continue
                
            # Importance filter
            if importance is not None and task.get("importance") != importance:
                continue
                
            # Deadline filter
            if has_deadline is not None:
                has_task_deadline = bool(task.get("deadline"))
                if has_deadline != has_task_deadline:
                    continue
            
            # Overdue filter
            if overdue_only:
                deadline_str = task.get("deadline")
                if not deadline_str:
                    continue
                try:
                    deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
                    if deadline > now:
                        continue
                except:
                    continue
                    
            filtered_tasks.append(task)
        
        # Build filters_applied dict
        if client:
            filters_applied["client"] = client
        if provider:
            filters_applied["provider"] = provider
        if status:
            filters_applied["status"] = status
        if importance is not None:
            filters_applied["importance"] = importance
        if has_deadline is not None:
            filters_applied["has_deadline"] = has_deadline
        if overdue_only:
            filters_applied["overdue_only"] = overdue_only
        
        # Sort tasks
        def get_sort_key(task):
            if sort_by == "score":
                return task.get("score", 0.0)
            elif sort_by == "importance":
                return task.get("importance", 3)
            elif sort_by == "created_at":
                created = task.get("created_at", "")
                try:
                    return datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
                except:
                    return 0
            elif sort_by == "deadline":
                deadline = task.get("deadline", "")
                if not deadline:
                    return 0 if sort_desc else float('inf')
                try:
                    return datetime.fromisoformat(deadline.replace("Z", "+00:00")).timestamp()
                except:
                    return 0 if sort_desc else float('inf')
            elif sort_by == "updated_at":
                updated = task.get("updated_at", "")
                try:
                    return datetime.fromisoformat(updated.replace("Z", "+00:00")).timestamp()
                except:
                    return 0
            return 0
            
        filtered_tasks.sort(key=get_sort_key, reverse=sort_desc)
        
        # Apply pagination
        total = len(filtered_tasks)
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        page_tasks = filtered_tasks[start_idx:end_idx]
        
        # Convert to response models
        task_responses = [convert_to_task_response(task) for task in page_tasks]
        
        return TaskListResponse(
            tasks=task_responses,
            total=total,
            page=page,
            size=size,
            has_next=end_idx < total,
            filters_applied=filters_applied
        )
        
    except Exception as e:
        logger.error(f"Task listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task listing failed: {str(e)}"
        )

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str = Path(description="Task ID")
) -> TaskResponse:
    """
    Get a specific task by ID
    
    - **task_id**: Unique task identifier
    """
    try:
        # Get all tasks and find the specific one
        # In production, this would be a direct database query
        all_tasks = fetch_open_tasks()
        task_data = None
        
        for task in all_tasks:
            if task.get("id") == task_id:
                task_data = task
                break
        
        if not task_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        return convert_to_task_response(task_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task retrieval failed for {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task retrieval failed: {str(e)}"
        )

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str = Path(description="Task ID"),
    task_update: TaskUpdateRequest = None,
    use_orchestration: bool = Query(True, description="Apply orchestration to updated task")
) -> TaskResponse:
    """
    Update a specific task
    
    - **task_id**: Unique task identifier
    - **task_update**: Fields to update
    - **use_orchestration**: Re-apply orchestration after update
    """
    try:
        # Find existing task
        all_tasks = fetch_open_tasks()
        existing_task = None
        
        for task in all_tasks:
            if task.get("id") == task_id:
                existing_task = task
                break
        
        if not existing_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        # Apply updates
        updated_task = existing_task.copy()
        updated_task["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        if task_update:
            update_data = task_update.model_dump(exclude_none=True)
            
            for field, value in update_data.items():
                if field == "deadline" and value:
                    updated_task[field] = value.isoformat()
                else:
                    updated_task[field] = value
        
        # Re-apply orchestration if requested and relevant fields changed
        orchestration_fields = {"importance", "effort_hours", "deadline", "client"}
        if use_orchestration and task_update:
            update_fields = set(task_update.model_dump(exclude_none=True).keys())
            if orchestration_fields.intersection(update_fields):
                updated_task = apply_orchestration(updated_task, True)
        
        # Save updated task
        save_task(updated_task)
        
        # Touch task to update timestamp
        touch_task(task_id)
        
        # Log update event
        log_event("task_updated", {
            "task_id": task_id,
            "updated_fields": list(task_update.model_dump(exclude_none=True).keys()) if task_update else [],
            "use_orchestration": use_orchestration
        })
        
        return convert_to_task_response(updated_task)
        
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"Task update validation error for {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Task update failed for {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task update failed: {str(e)}"
        )

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str = Path(description="Task ID"),
    hard_delete: bool = Query(False, description="Permanently delete (vs mark as cancelled)")
) -> None:
    """
    Delete or cancel a task
    
    - **task_id**: Unique task identifier  
    - **hard_delete**: Permanently delete vs mark as cancelled
    """
    try:
        # Find existing task
        all_tasks = fetch_open_tasks()
        existing_task = None
        
        for task in all_tasks:
            if task.get("id") == task_id:
                existing_task = task
                break
        
        if not existing_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        if hard_delete:
            # In a real implementation, this would be a DELETE SQL statement
            # For now, we'll mark it with a special status
            existing_task["status"] = "deleted"
            existing_task["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_task(existing_task)
            
            log_event("task_deleted", {"task_id": task_id, "hard_delete": True})
        else:
            # Soft delete - mark as cancelled
            existing_task["status"] = "cancelled" 
            existing_task["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_task(existing_task)
            
            log_event("task_cancelled", {"task_id": task_id, "hard_delete": False})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task deletion failed for {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task deletion failed: {str(e)}"
        )

@router.get("/stats/summary", response_model=TaskStatsResponse)
async def get_task_stats() -> TaskStatsResponse:
    """
    Get comprehensive task statistics
    
    Returns statistics about task distribution, scores, and status
    """
    try:
        all_tasks = fetch_open_tasks()
        now = datetime.now(timezone.utc)
        
        # Initialize counters
        total_tasks = len(all_tasks)
        by_status = {}
        by_client = {}
        by_provider = {}
        scores = []
        high_priority_count = 0
        overdue_count = 0
        
        # Process all tasks
        for task in all_tasks:
            # Status distribution
            status = task.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            
            # Client distribution
            client = task.get("client", "unknown")
            by_client[client] = by_client.get(client, 0) + 1
            
            # Provider distribution  
            provider = task.get("provider", "internal")
            by_provider[provider] = by_provider.get(provider, 0) + 1
            
            # Score analysis
            score = task.get("score", 0.0)
            if score is not None:
                scores.append(float(score))
                
            # High priority count (importance >= 4 or score >= 0.8)
            importance = task.get("importance", 3)
            if importance >= 4 or (score and score >= 0.8):
                high_priority_count += 1
                
            # Overdue count
            deadline_str = task.get("deadline")
            if deadline_str:
                try:
                    deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
                    if deadline < now:
                        overdue_count += 1
                except:
                    pass
        
        # Score distribution
        score_distribution = {
            "high": len([s for s in scores if s >= 0.8]),
            "medium": len([s for s in scores if 0.4 <= s < 0.8]), 
            "low": len([s for s in scores if s < 0.4])
        }
        
        # Average score
        average_score = sum(scores) / len(scores) if scores else 0.0
        
        return TaskStatsResponse(
            total_tasks=total_tasks,
            by_status=by_status,
            by_client=by_client,
            by_provider=by_provider,
            score_distribution=score_distribution,
            average_score=average_score,
            high_priority_count=high_priority_count,
            overdue_count=overdue_count
        )
        
    except Exception as e:
        logger.error(f"Task stats retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task stats retrieval failed: {str(e)}"
        )

@router.post("/{task_id}/score", response_model=Dict[str, Any])
async def rescore_task(
    task_id: str = Path(description="Task ID"),
    use_orchestration: bool = Query(True, description="Use orchestration for scoring")
) -> Dict[str, Any]:
    """
    Recalculate task score using current algorithms
    
    - **task_id**: Unique task identifier
    - **use_orchestration**: Use advanced orchestration scoring
    """
    try:
        # Find existing task
        all_tasks = fetch_open_tasks()
        existing_task = None
        
        for task in all_tasks:
            if task.get("id") == task_id:
                existing_task = task
                break
        
        if not existing_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        old_score = existing_task.get("score", 0.0)
        
        # Apply new scoring
        if use_orchestration:
            updated_task = apply_orchestration(existing_task, True)
        else:
            # Use basic scoring
            from app.config import load_rules
            rules = load_rules()
            new_score = compute_score(existing_task, rules)
            updated_task = existing_task.copy()
            updated_task["score"] = new_score
            updated_task["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Save updated task
        save_task(updated_task)
        touch_task(task_id)
        
        new_score = updated_task.get("score", 0.0)
        
        # Log rescoring event
        log_event("task_rescored", {
            "task_id": task_id,
            "old_score": old_score,
            "new_score": new_score,
            "score_change": new_score - old_score,
            "use_orchestration": use_orchestration
        })
        
        return {
            "task_id": task_id,
            "old_score": old_score,
            "new_score": new_score,
            "score_change": new_score - old_score,
            "rescoring_method": "orchestration" if use_orchestration else "basic",
            "orchestration_meta": updated_task.get("orchestration_meta", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task rescoring failed for {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task rescoring failed: {str(e)}"
        )

@router.post("/batch/rescore")
async def batch_rescore_tasks(
    client: Optional[str] = Query(None, description="Rescore tasks for specific client"),
    use_orchestration: bool = Query(True, description="Use orchestration scoring"),
    limit: int = Query(100, ge=1, le=500, description="Maximum tasks to rescore")
) -> Dict[str, Any]:
    """
    Batch rescore multiple tasks
    
    - **client**: Optional client filter
    - **use_orchestration**: Use advanced orchestration scoring
    - **limit**: Maximum number of tasks to process
    """
    try:
        all_tasks = fetch_open_tasks()
        
        # Filter tasks if client specified
        if client:
            all_tasks = [t for t in all_tasks if t.get("client") == client]
        
        # Limit tasks
        tasks_to_rescore = all_tasks[:limit]
        
        rescored_count = 0
        total_score_change = 0.0
        errors = []
        
        for task in tasks_to_rescore:
            try:
                task_id = task["id"]
                old_score = task.get("score", 0.0)
                
                # Apply new scoring
                if use_orchestration:
                    updated_task = apply_orchestration(task, True)
                else:
                    from app.config import load_rules
                    rules = load_rules()
                    new_score = compute_score(task, rules)
                    updated_task = task.copy()
                    updated_task["score"] = new_score
                    updated_task["updated_at"] = datetime.now(timezone.utc).isoformat()
                
                # Save updated task
                save_task(updated_task)
                touch_task(task_id)
                
                new_score = updated_task.get("score", 0.0)
                score_change = new_score - old_score
                total_score_change += score_change
                rescored_count += 1
                
            except Exception as e:
                errors.append({
                    "task_id": task.get("id", "unknown"),
                    "error": str(e)
                })
                continue
        
        # Log batch rescoring event
        log_event("batch_rescore", {
            "rescored_count": rescored_count,
            "total_tasks": len(tasks_to_rescore),
            "client_filter": client,
            "use_orchestration": use_orchestration,
            "error_count": len(errors)
        })
        
        return {
            "rescored_count": rescored_count,
            "total_tasks_processed": len(tasks_to_rescore),
            "average_score_change": total_score_change / rescored_count if rescored_count > 0 else 0.0,
            "client_filter": client,
            "rescoring_method": "orchestration" if use_orchestration else "basic",
            "errors": errors[:10]  # Return first 10 errors
        }
        
    except Exception as e:
        logger.error(f"Batch task rescoring failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch rescoring failed: {str(e)}"
        )