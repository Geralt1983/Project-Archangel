from datetime import datetime, timezone
from .config import load_rules

def plan_today(tasks: list[dict], available_hours_today: float) -> dict[str, list[str]]:
    rules = load_rules()
    per_client = {}
    for t in tasks:
        c = t.get("client","")
        per_client.setdefault(c, []).append(t)
    # score already computed
    for arr in per_client.values():
        arr.sort(key=lambda x: x.get("score",0), reverse=True)
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