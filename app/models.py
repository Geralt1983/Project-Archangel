from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Enumeration of high-level task states."""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class Subtask(BaseModel):
    """Representation of a simple subtask item."""
    title: str
    status: TaskStatus = TaskStatus.NEW
    effort_hours: Optional[float] = None


class TaskIntake(BaseModel):
    """Incoming task information provided by external sources."""
    title: str
    description: Optional[str] = None
    client: str = "unknown"
    project: Optional[str] = None
    deadline: Optional[datetime] = None
    importance: int = 3
    effort_hours: Optional[float] = None
    labels: List[str] = Field(default_factory=list)
    source: str = "api"
    meta: dict[str, Any] = Field(default_factory=dict)

class Task(BaseModel):
    """Normalized task model used internally by the orchestrator."""
    id: str
    title: str
    description: str = ""
    client: str
    project: Optional[str] = None
    task_type: Optional[str] = None
    deadline: Optional[datetime] = None
    importance: int = 3
    effort_hours: Optional[float] = None
    labels: List[str] = Field(default_factory=list)
    source: str = "api"
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    idempotency_key: str
    recent_progress: float = 0.0
    client_sla_hours: Optional[float] = None
    score: Optional[float] = None
    checklist: List[str] = Field(default_factory=list)
    subtasks: List[Subtask] = Field(default_factory=list)

