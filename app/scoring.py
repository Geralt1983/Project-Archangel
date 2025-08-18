from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    """
    Parse ISO datetime string with timezone handling
    
    Args:
        s: ISO datetime string or None
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except Exception as e:
        logger.warning(f"Failed to parse datetime string '{s}': {e}")
        return None


@dataclass
class ClientConfig:
    """
    Client-specific configuration for task scoring
    
    Attributes:
        importance_bias: Multiplier for task importance (default: 1.0)
        sla_hours: SLA deadline in hours for client tasks (default: 72)
    """
    importance_bias: float = 1.0
    sla_hours: int = 72
    
    def __post_init__(self) -> None:
        """Validate configuration parameters"""
        if self.importance_bias < 0:
            raise ValueError(f"importance_bias must be non-negative, got {self.importance_bias}")
        if self.sla_hours <= 0:
            raise ValueError(f"sla_hours must be positive, got {self.sla_hours}")


@dataclass
class Task:
    """
    Task data model for scoring calculations
    
    Attributes:
        client: Client identifier
        importance: Task importance score (1-5 scale)
        effort_hours: Estimated effort in hours
        due_at: ISO datetime string for due date
        deadline: Alternative deadline field (ISO datetime)
        recent_progress: Progress indicator (0.0-1.0)
        created_at: ISO datetime for task creation
        ingested_at: ISO datetime for task ingestion
    """
    client: str = ""
    importance: float = 3.0
    effort_hours: float = 1.0
    due_at: Optional[str] = None
    deadline: Optional[str] = None
    recent_progress: float = 0.0
    created_at: Optional[str] = None
    ingested_at: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate task parameters"""
        if not 1.0 <= self.importance <= 5.0:
            logger.warning(f"Importance {self.importance} outside recommended range [1.0, 5.0]")
        if self.effort_hours < 0:
            raise ValueError(f"effort_hours must be non-negative, got {self.effort_hours}")
        if not 0.0 <= self.recent_progress <= 1.0:
            raise ValueError(f"recent_progress must be between 0.0 and 1.0, got {self.recent_progress}")

    @property
    def deadline_iso(self) -> Optional[str]:
        return self.due_at or self.deadline


def compute_score(task: Dict[str, Any], rules: Dict[str, Any]) -> float:
    """
    Compute a priority score for a task based on urgency and client rules.
    
    Args:
        task: Task dictionary with scoring attributes
        rules: Rules dictionary containing client configurations
        
    Returns:
        Priority score between 0.0 and 1.0 (higher is more important)
        
    Raises:
        TypeError: If task or rules are not dictionaries
        ValueError: If required task fields are missing or invalid
    """
    if not isinstance(task, dict):
        raise TypeError(f"task must be a dictionary, got {type(task)}")
    if not isinstance(rules, dict):
        raise TypeError(f"rules must be a dictionary, got {type(rules)}")
        
    logger.debug(f"Computing score for task: {task.get('id', 'unknown')}")
    now = datetime.now(timezone.utc)

    try:
        # Map incoming dictionary to the Task dataclass, ignoring extra keys
        task_fields = {k: task.get(k) for k in Task.__dataclass_fields__}
        t = Task(**task_fields)
        
        # Get client configuration with defaults
        client_rules = rules.get("clients", {}).get(t.client, {})
        client_cfg = ClientConfig(**client_rules)
        
        logger.debug(f"Processing task for client '{t.client}' with SLA {client_cfg.sla_hours}h")
        
    except Exception as e:
        logger.error(f"Error creating task/client objects: {e}")
        raise ValueError(f"Invalid task or client configuration: {e}") from e

    due_dt = _parse_iso(t.deadline_iso)
    hrs_to_deadline = None if not due_dt else (due_dt - now).total_seconds() / 3600.0
    
    logger.debug(f"Deadline analysis: due_dt={due_dt}, hrs_to_deadline={hrs_to_deadline}")

    if hrs_to_deadline is None:
        urgency = 0.0
    elif hrs_to_deadline <= 0:
        urgency = 1.0
    else:
        horizon = 336.0
        urgency = max(0.0, min(1.0, 1.0 - (float(hrs_to_deadline) / horizon)))

    importance = (t.importance / 5.0) * client_cfg.importance_bias
    effort_factor = max(0.0, min(1.0, 1 - (t.effort_hours / 8.0)))

    created_dt = _parse_iso(t.created_at or t.ingested_at)
    hours_since_created = None if not created_dt else (now - created_dt).total_seconds() / 3600.0
    freshness = 0.0 if hours_since_created is None else max(0.0, min(1.0, 1 - (hours_since_created / 168.0)))

    sla_hours = client_cfg.sla_hours
    hours_left_in_sla = 0.0 if hours_since_created is None else max(0.0, sla_hours - hours_since_created)
    sla_pressure = max(0.0, min(1.0, 1 - (hours_left_in_sla / sla_hours)))

    recent_progress_inv = max(0.0, min(1.0, 1 - t.recent_progress))

    # Add metadata to task for downstream processing
    try:
        task["deadline_within_24h"] = bool(hrs_to_deadline is not None and hrs_to_deadline <= 24)
        task["sla_pressure"] = sla_pressure
        task["urgency_score"] = urgency
        task["computed_at"] = now.isoformat()
    except Exception as e:
        logger.warning(f"Failed to add task metadata: {e}")

    score = (
        0.30 * urgency +
        0.25 * importance +
        0.15 * effort_factor +
        0.10 * freshness +
        0.15 * sla_pressure +
        0.05 * recent_progress_inv
    )

    # Add micro tie-breaker for deadline precision
    if hrs_to_deadline is not None:
        tiebreaker = (-float(hrs_to_deadline)) * 1e-9
        score += tiebreaker
        logger.debug(f"Applied deadline tiebreaker: {tiebreaker}")
    
    # Ensure score is within valid range
    final_score = max(0.0, min(1.0, float(score)))
    
    logger.debug(
        f"Score computed: {final_score:.6f} "
        f"(urgency={urgency:.3f}, importance={importance:.3f}, "
        f"effort={effort_factor:.3f}, freshness={freshness:.3f}, "
        f"sla={sla_pressure:.3f}, progress={recent_progress_inv:.3f})"
    )
    
    return final_score
