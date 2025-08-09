import uuid, datetime as dt
from .scoring import compute_score
from .subtasks import build_checklist_and_subtasks
from .config import load_rules

rules = load_rules()

def normalize(d: dict) -> dict:
    return {
        "id": d.get("id") or f"tsk_{uuid.uuid4().hex[:8]}",
        "title": d["title"].strip(),
        "description": d.get("description", ""),
        "client": d.get("client", "unknown").lower(),
        "project": d.get("project"),
        "deadline": d.get("deadline"),
        "importance": d.get("importance", 3),
        "effort_hours": d.get("effort_hours"),
        "created_at": d.get("created_at") or dt.datetime.utcnow().isoformat() + "Z",
        "source": d.get("source", "api"),
        "labels": d.get("labels", []),
        "recent_progress": d.get("recent_progress", 0.0),
    }

def classify(task: dict):
    t = task["title"].lower()
    if any(k in t for k in ["fix", "error", "fail", "bug", "500"]):
        task["task_type"] = "bugfix"
    elif any(k in t for k in ["report", "analysis", "dashboard"]):
        task["task_type"] = "report"
    elif any(k in t for k in ["setup", "onboard", "access", "provision"]):
        task["task_type"] = "onboarding"
    else:
        task["task_type"] = "general"

def fill_defaults(task: dict):
    tt = rules["task_types"].get(task["task_type"], {})
    if not task.get("effort_hours"):
        task["effort_hours"] = tt.get("default_effort_hours", 1.0)
    if "labels" in tt:
        task["labels"] = list(set(task["labels"] + tt["labels"]))

def triage(task_in: dict) -> dict:
    task = normalize(task_in)
    classify(task)
    fill_defaults(task)
    task["score"] = compute_score(task, rules)
    checklist, subtasks = build_checklist_and_subtasks(task)
    task["checklist"] = checklist
    task["subtasks"] = subtasks
    return task