from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


@dataclass
class ClientConfig:
    importance_bias: float = 1.0
    sla_hours: int = 72


@dataclass
class Task:
    client: str = ""
    importance: float = 3.0
    effort_hours: float = 1.0
    due_at: Optional[str] = None
    deadline: Optional[str] = None
    recent_progress: float = 0.0
    created_at: Optional[str] = None
    ingested_at: Optional[str] = None

    @property
    def deadline_iso(self) -> Optional[str]:
        return self.due_at or self.deadline


def compute_score(task: Dict[str, Any], rules: Dict[str, Any]) -> float:
    """Compute a priority score for a task based on urgency and client rules."""
    now = datetime.now(timezone.utc)

    # Map incoming dictionary to the Task dataclass, ignoring extra keys
    t = Task(**{k: task.get(k) for k in Task.__dataclass_fields__})
    client_cfg = ClientConfig(**rules.get("clients", {}).get(t.client, {}))

    due_dt = _parse_iso(t.deadline_iso)
    hrs_to_deadline = None if not due_dt else (due_dt - now).total_seconds() / 3600.0

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

    task["deadline_within_24h"] = bool(hrs_to_deadline is not None and hrs_to_deadline <= 24)
    task["sla_pressure"] = sla_pressure

    score = (
        0.30 * urgency +
        0.25 * importance +
        0.15 * effort_factor +
        0.10 * freshness +
        0.15 * sla_pressure +
        0.05 * recent_progress_inv
    )

    if hrs_to_deadline is not None:
        score += (-float(hrs_to_deadline)) * 1e-9

    return float(score)
