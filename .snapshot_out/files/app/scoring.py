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
    # Freeze "now" to prevent drift within single evaluation
    now = datetime.now(timezone.utc)
    
    def _parse_iso(s):
        if not s:
            return None
        s = s.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    client_cfg = rules.get("clients", {}).get(task.get("client", ""), {})
    imp_bias = client_cfg.get("importance_bias", 1.0)

    # Accept both 'due_at' and 'deadline'
    due_iso = task.get("due_at") or task.get("deadline")
    due_dt = _parse_iso(due_iso)
    hrs_to_deadline = None if not due_dt else (due_dt - now).total_seconds() / 3600.0

    # Continuous urgency:
    # - If overdue (hrs < 0): treat as max urgency 1.0
    # - If in future: urgency decays linearly over a 14-day (336h) horizon
    #   0h -> 1.0, 336h -> 0.0, clamp to [0,1]
    if hrs_to_deadline is None:
        urgency = 0.0
    elif hrs_to_deadline <= 0:
        urgency = 1.0
    else:
        horizon = 336.0  # 14 days
        urgency = max(0.0, min(1.0, 1.0 - (float(hrs_to_deadline) / horizon)))

    importance = (task.get("importance", 3) / 5.0) * imp_bias
    
    # FIX: Invert effort factor to favor smaller tasks (small wins)
    effort_factor = max(0.0, min(1.0, 1 - (task.get("effort_hours", 1.0) / 8.0)))
    
    # Use frozen "now" for consistent time calculations
    created_dt = _parse_iso(task.get("created_at") or task.get("ingested_at"))
    hours_since_created = None if not created_dt else (now - created_dt).total_seconds() / 3600.0
    freshness = 0.0 if hours_since_created is None else max(0.0, min(1.0, 1 - (hours_since_created / 168.0)))

    sla_hours = client_cfg.get("sla_hours", 72)
    # FIX: Correct SLA pressure calculation - hours left in SLA window
    hours_left_in_sla = 0.0 if hours_since_created is None else max(0.0, sla_hours - hours_since_created)
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

    # Micro tie-breaker: earlier deadlines (smaller hours) get a tiny boost.
    # This counters sub-millisecond drift in freshness/SLA between two calls.
    if hrs_to_deadline is not None:
        # Scale is ~1e-9 per hour; 1000h shifts score by ~1e-6.
        score += (-float(hrs_to_deadline)) * 1e-9

    return float(score)