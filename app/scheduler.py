import os, datetime as dt
from .db import fetch_open_tasks, save_task
from .scoring import compute_score
from .config import load_rules
from .providers.clickup import ClickUpAdapter

def daily_reeval():
    rules = load_rules()
    for t in fetch_open_tasks():
        t["score"] = compute_score(t, rules)
        save_task(t)

def weekly_checkins():
    # stub: compute per client summary and send to Slack or email
    pass

def make_adapter():
    return ClickUpAdapter(
        token=os.getenv("CLICKUP_TOKEN",""),
        team_id=os.getenv("CLICKUP_TEAM_ID",""),
        list_id=os.getenv("CLICKUP_LIST_ID",""),
        webhook_secret=os.getenv("CLICKUP_WEBHOOK_SECRET",""),
    )