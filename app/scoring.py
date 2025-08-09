from datetime import datetime, timezone
from typing import Dict, Any, Optional
from .models import Task
from .config import load_rules, get_client_config

def compute_score(task: Task, rules: Optional[Dict[str, Any]] = None) -> float:
    """
    Compute priority score for a task using weighted formula.
    
    score = 0.30 * urgency + 0.25 * importance + 0.15 * effort_factor + 
            0.10 * freshness + 0.15 * sla_pressure + 0.05 * recent_progress_inverse
    
    Lower scores indicate higher priority.
    """
    if rules is None:
        rules = load_rules()
    
    scoring_config = rules.get("scoring", {})
    weights = {
        "urgency": scoring_config.get("urgency_weight", 0.30),
        "importance": scoring_config.get("importance_weight", 0.25),
        "effort": scoring_config.get("effort_weight", 0.15),
        "freshness": scoring_config.get("freshness_weight", 0.10),
        "sla": scoring_config.get("sla_weight", 0.15),
        "progress": scoring_config.get("progress_weight", 0.05),
    }
    
    now = datetime.now(timezone.utc)
    
    # 1. Urgency: higher score for closer deadlines
    urgency = 0.0
    if task.deadline:
        if task.deadline.tzinfo is None:
            deadline = task.deadline.replace(tzinfo=timezone.utc)
        else:
            deadline = task.deadline
        
        hours_to_deadline = (deadline - now).total_seconds() / 3600
        urgency = clamp(1 - hours_to_deadline / 168, 0, 1)  # 168 hours = 1 week
    
    # 2. Importance: normalize and apply client bias
    client_config = get_client_config(task.client)
    importance_bias = client_config.get("importance_bias", 1.0)
    importance = (task.importance / 5.0) * importance_bias
    importance = min(importance, 1.0)  # Cap at 1.0
    
    # 3. Effort factor: prefer smaller tasks (inverted)
    effort_hours = task.effort_hours or 1.0
    effort_factor = clamp(effort_hours / 8.0, 0, 1)  # Normalize to 8-hour workday
    
    # 4. Freshness: newer tasks get higher scores
    if task.created_at.tzinfo is None:
        created_at = task.created_at.replace(tzinfo=timezone.utc)
    else:
        created_at = task.created_at
    
    hours_since_created = (now - created_at).total_seconds() / 3600
    freshness = clamp(1 - hours_since_created / 168, 0, 1)  # 168 hours = 1 week
    
    # 5. SLA pressure: higher score when approaching SLA
    sla_pressure = 0.0
    client_sla_hours = task.client_sla_hours or client_config.get("sla_hours", 72)
    if client_sla_hours:
        hours_since_created = (now - created_at).total_seconds() / 3600
        hours_to_sla = client_sla_hours - hours_since_created
        sla_pressure = clamp(1 - hours_to_sla / 72, 0, 1)  # 72 hours warning window
    
    # 6. Recent progress: boost stalled tasks
    recent_progress_inverse = clamp(1 - task.recent_progress, 0, 1)
    
    # Apply aging boost
    defaults = rules.get("defaults", {})
    aging_boost_per_day = defaults.get("aging_boost_per_day", 2)
    days_since_created = hours_since_created / 24
    aging_boost = min(days_since_created * aging_boost_per_day / 100, 0.5)  # Cap at 50% boost
    
    # Calculate weighted score
    score = (
        weights["urgency"] * urgency +
        weights["importance"] * importance +
        weights["effort"] * effort_factor +
        weights["freshness"] * freshness +
        weights["sla"] * sla_pressure +
        weights["progress"] * recent_progress_inverse +
        aging_boost
    )
    
    return min(score, 1.0)  # Cap at 1.0

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))

def is_task_stale(task: Task, rules: Optional[Dict[str, Any]] = None) -> bool:
    """Check if task is considered stale."""
    if rules is None:
        rules = load_rules()
    
    defaults = rules.get("defaults", {})
    stale_after_days = defaults.get("stale_after_days", 3)
    
    now = datetime.now(timezone.utc)
    if task.updated_at.tzinfo is None:
        updated_at = task.updated_at.replace(tzinfo=timezone.utc)
    else:
        updated_at = task.updated_at
    
    days_since_update = (now - updated_at).total_seconds() / (24 * 3600)
    return days_since_update > stale_after_days

def is_sla_at_risk(task: Task, rules: Optional[Dict[str, Any]] = None) -> bool:
    """Check if task is at risk of missing SLA."""
    client_config = get_client_config(task.client)
    client_sla_hours = task.client_sla_hours or client_config.get("sla_hours", 72)
    
    if not client_sla_hours:
        return False
    
    now = datetime.now(timezone.utc)
    if task.created_at.tzinfo is None:
        created_at = task.created_at.replace(tzinfo=timezone.utc)
    else:
        created_at = task.created_at
    
    hours_since_created = (now - created_at).total_seconds() / 3600
    hours_remaining = client_sla_hours - hours_since_created
    
    # Consider at risk if less than 12 hours remaining
    return hours_remaining < 12