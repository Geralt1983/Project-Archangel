import os
import datetime as dt
from .db_pg import fetch_open_tasks, save_task
from .scoring import compute_score
from .config import load_rules
from .balancer import plan_today
from .providers.clickup import ClickUpAdapter

def daily_reeval():
    rules = load_rules()
    tasks = fetch_open_tasks()
    for t in tasks:
        t["score"] = compute_score(t, rules)
        save_task(t)
    
    # FIX: Compute fairness deficits and apply to planning
    fairness_deficits = compute_fairness_deficits(tasks, rules)
    plan = plan_today(tasks, available_hours_today=5.0, fairness_deficits=fairness_deficits)
    return plan

def compute_fairness_deficits(tasks: list[dict], rules: dict) -> dict[str, float]:
    """Compute fairness deficit from current task counts vs configured target share"""
    from collections import defaultdict
    
    # Count tasks per client
    client_counts = defaultdict(int)
    for t in tasks:
        client_counts[t.get("client", "unknown")] += 1
    
    total_tasks = len(tasks)
    if total_tasks == 0:
        return {}
    
    # Calculate deficits based on target share vs actual share
    deficits = {}
    for client, config in rules.get("clients", {}).items():
        target_share = config.get("target_share", 0.2)  # Default 20% if not specified
        actual_count = client_counts.get(client, 0)
        actual_share = actual_count / total_tasks
        
        # Deficit is how far below target share this client is
        deficit = max(0.0, target_share - actual_share)
        if deficit > 0.05:  # Only apply meaningful deficits (>5%)
            deficits[client] = deficit
    
    return deficits

def weekly_checkins():
    from collections import defaultdict
    from .notify import post_slack
    
    tasks = fetch_open_tasks()
    by_client = defaultdict(lambda: {"open": 0, "avg_score": 0.0})
    for t in tasks:
        c = t.get("client","unknown")
        by_client[c]["open"] += 1
        by_client[c]["avg_score"] += float(t.get("score", 0.0))
    for c, agg in by_client.items():
        if agg["open"]:
            agg["avg_score"] = round(agg["avg_score"] / agg["open"], 3)
    lines = ["Weekly check in"]
    for c, agg in sorted(by_client.items()):
        lines.append(f"{c}: open {agg['open']}, avg score {agg['avg_score']}")
    text = "\n".join(lines)
    post_slack(text)
    return {"sent": True, "summary": by_client}

def _parse_iso(s: str):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))

def _days_since(iso_ts: str):
    try:
        return max(0.0, (dt.datetime.utcnow() - _parse_iso(iso_ts).replace(tzinfo=None)).total_seconds() / 86400.0)
    except Exception:
        return 0.0

def _task_link(t: dict) -> str:
    provider = t.get("provider","clickup")
    ext = t.get("external_id","")
    if provider == "clickup" and ext:
        return f"https://app.clickup.com/t/{ext}"
    if provider == "trello" and ext:
        return f"https://trello.com/c/{ext}"
    if provider == "todoist" and ext:
        return f"https://todoist.com/showTask?id={ext}"
    return ""

def hourly_stale_nudge():
    from .notify import post_slack, nudge_line
    
    rules = load_rules()
    stale_days = float(rules["defaults"].get("stale_after_days", 3))
    boost_per_day = float(rules["defaults"].get("aging_boost_per_day", 2))
    tasks = fetch_open_tasks()
    nudged = []
    now_iso = dt.datetime.utcnow().isoformat() + "Z"

    for t in tasks:
        payload = t
        updated_iso = payload.get("updated_at") or payload.get("created_at") or now_iso
        days = _days_since(updated_iso)
        if days >= stale_days:
            # bump score by aging boost
            bump = (days - stale_days + 1.0) * boost_per_day / 100.0
            old = float(payload.get("score", 0.0))
            payload["score"] = round(min(1.0, old + bump), 4)
            payload["updated_at"] = payload.get("updated_at", payload.get("created_at", now_iso))  # do not reset activity
            save_task(payload)
            link = _task_link(payload)
            line = nudge_line(
                task_id=payload["id"],
                title=payload.get("title",""),
                client=payload.get("client",""),
                provider=payload.get("provider",""),
                link=link,
                days_stale=int(days),
                score=payload["score"],
            )
            nudged.append(line)

    if nudged:
        post_slack("Stale nudges\n" + "\n".join(nudged))
    return {"nudged": len(nudged)}

def make_adapter():
    return ClickUpAdapter(
        token=os.getenv("CLICKUP_TOKEN",""),
        team_id=os.getenv("CLICKUP_TEAM_ID",""),
        list_id=os.getenv("CLICKUP_LIST_ID",""),
        webhook_secret=os.getenv("CLICKUP_WEBHOOK_SECRET",""),
    )