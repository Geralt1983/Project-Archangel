from datetime import datetime, timezone

def _hours_until(dt_iso):
    if not dt_iso: return None
    dt = datetime.fromisoformat(dt_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    return (dt - now).total_seconds() / 3600

def _hours_since(dt_iso):
    dt = datetime.fromisoformat(dt_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 3600)

def compute_score(task: dict, rules: dict) -> float:
    client_cfg = rules.get("clients", {}).get(task.get("client", ""), {})
    imp_bias = client_cfg.get("importance_bias", 1.0)

    # Accept both 'due_at' and 'deadline'
    due_iso = task.get("due_at") or task.get("deadline")
    hrs_to_deadline = _hours_until(due_iso)

    if hrs_to_deadline is None:
        urgency = 0.0
    else:
        h = max(0.0, hrs_to_deadline)
        # Make bins strictly decreasing so closer deadline yields higher urgency
        if h <= 4:
            urgency = 1.0
        elif h <= 24:
            urgency = 0.8
        elif h <= 72:
            urgency = 0.6
        elif h <= 168:
            urgency = 0.4
        elif h <= 336:
            urgency = 0.2
        else:
            urgency = 0.0

    importance = (task.get("importance", 3) / 5.0) * imp_bias
    
    # FIX: Invert effort factor to favor smaller tasks (small wins)
    effort_factor = max(0.0, min(1.0, 1 - (task.get("effort_hours", 1.0) / 8.0)))
    freshness = max(0.0, min(1.0, 1 - (_hours_since(task["created_at"]) / 168.0)))

    sla_hours = client_cfg.get("sla_hours", 72)
    # FIX: Correct SLA pressure calculation - hours left in SLA window
    hours_since_created = _hours_since(task["created_at"])
    hours_left_in_sla = max(0.0, sla_hours - hours_since_created)
    sla_pressure = max(0.0, min(1.0, 1 - (hours_left_in_sla / sla_hours)))

    recent_progress_inv = max(0.0, min(1.0, 1 - task.get("recent_progress", 0.0)))

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
    return round(float(score), 4)