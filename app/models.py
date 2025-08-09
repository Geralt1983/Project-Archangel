from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class TaskStatus(str, Enum):
    NEW = "new"
    TRIAGED = "triaged"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"

class SubtaskStatus(str, Enum):
    NEW = "new"
    DONE = "done"

class Provider(str, Enum):
    CLICKUP = "clickup"
    TRELLO = "trello"
    TODOIST = "todoist"
    NONE = "none"

class Subtask(BaseModel):
    title: str
    status: SubtaskStatus = SubtaskStatus.NEW
    effort_hours: Optional[float] = None
    deadline: Optional[datetime] = None
    assignee: Optional[str] = None

class Task(BaseModel):
    id: str
    external_id: Optional[str] = None
    provider: Provider = Provider.NONE
    title: str
    description: Optional[str] = ""
    client: str
    project: Optional[str] = None
    task_type: Optional[str] = "general"
    labels: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.NEW
    deadline: Optional[datetime] = None
    effort_hours: Optional[float] = None
    importance: int = Field(default=3, ge=1, le=5)
    client_sla_hours: Optional[float] = None
    freshness_score: Optional[float] = None
    recent_progress: float = Field(default=0.0, ge=0.0, le=1.0)
    score: Optional[float] = None
    checklist: List[str] = Field(default_factory=list)
    subtasks: List[Subtask] = Field(default_factory=list)
    source: str = "api"
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    idempotency_key: Optional[str] = None

class TaskIntake(BaseModel):
    """Model for incoming task creation requests."""
    title: str
    description: Optional[str] = ""
    client: str = "unknown"
    project: Optional[str] = None
    deadline: Optional[datetime] = None
    importance: Optional[int] = Field(default=3, ge=1, le=5)
    effort_hours: Optional[float] = None
    labels: List[str] = Field(default_factory=list)
    source: str = "api"
    meta: Dict[str, Any] = Field(default_factory=dict)

class TriageResponse(BaseModel):
    """Response from the triage process."""
    id: str
    provider: str
    external_id: str
    status: str
    task_type: str
    score: float
    subtasks_created: int
    checklist_items: int

class WebhookEvent(BaseModel):
    """Generic webhook event structure."""
    event_type: str
    event_id: Optional[str] = None
    delivery_id: Optional[str] = None
    task_id: Optional[str] = None
    external_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AuditEvent(BaseModel):
    """Audit log entry."""
    event_type: str
    task_id: Optional[str] = None
    external_id: Optional[str] = None
    provider: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None