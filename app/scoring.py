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

    hrs_to_deadline = _hours_until(task.get("deadline")) or 168.0
    urgency = max(0.0, min(1.0, 1 - hrs_to_deadline / 168.0))

    importance = (task.get("importance", 3) / 5.0) * imp_bias
    effort_factor = max(0.0, min(1.0, (task.get("effort_hours", 1.0) / 8.0)))
    freshness = max(0.0, min(1.0, 1 - (_hours_since(task["created_at"]) / 168.0)))

    sla_hours = client_cfg.get("sla_hours", 72)
    hrs_to_sla = (_hours_until(task.get("created_at")) or 0) + sla_hours  # created_at until SLA window ends
    sla_pressure = max(0.0, min(1.0, 1 - (hrs_to_sla / 72.0)))

    recent_progress_inv = max(0.0, min(1.0, 1 - task.get("recent_progress", 0.0)))

    score = (
        0.30 * urgency +
        0.25 * importance +
        0.15 * effort_factor +
        0.10 * freshness +
        0.15 * sla_pressure +
        0.05 * recent_progress_inv
    )
    return round(float(score), 4)