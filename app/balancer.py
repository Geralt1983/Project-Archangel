from .config import load_rules

def plan_today(tasks: list[dict], available_hours_today: float, fairness_deficits: dict[str, float] = None) -> dict[str, list[str]]:
    rules = load_rules()
    fairness_deficits = fairness_deficits or {}
    
    per_client = {}
    for t in tasks:
        c = t.get("client","")
        per_client.setdefault(c, []).append(t)
    
    # FIX: Apply fairness deficit boost to scores before sorting
    for client, arr in per_client.items():
        deficit = fairness_deficits.get(client, 0.0)
        fairness_boost = max(0.0, min(0.5, deficit))  # Bounded boost up to +0.5
        for t in arr:
            t["adjusted_score"] = t.get("score", 0.0) + fairness_boost
        # Sort by adjusted score
        arr.sort(key=lambda x: x.get("adjusted_score", 0), reverse=True)
    
    plan = {}
    remaining = available_hours_today
    for client, arr in per_client.items():
        cap = min(rules["clients"].get(client,{}).get("daily_cap_hours", 2), remaining)
        cur = 0.0
        chosen = []
        for t in arr:
            eh = max(0.25, float(t.get("effort_hours",1.0)))
            if cur + eh <= cap or urgent(t, rules):
                chosen.append(t["id"])
                cur += eh
        if chosen:
            plan[client] = chosen
        remaining = max(0.0, remaining - cur)
    return plan

def urgent(t, rules):
    # override if deadline within 24 hours or client SLA pressure near 1
    return t.get("deadline_within_24h", False) or t.get("sla_pressure", 0) > 0.9