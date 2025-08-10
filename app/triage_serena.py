from .triage import normalize, classify, fill_defaults
from .scoring import compute_score
from .subtasks import build_checklist_and_subtasks
from .config import load_rules
from .mcp_client import triage_call
import datetime as dt

def triage_with_serena(task_in: dict, provider: str) -> dict:
    rules = load_rules()
    task = normalize(task_in)
    classify(task)
    fill_defaults(task)
    # deterministic baseline
    baseline_checklist, baseline_subs = build_checklist_and_subtasks(task)
    task["checklist"] = baseline_checklist
    task["subtasks"] = baseline_subs
    task["score"] = compute_score(task, rules)

    if not _enabled(): 
        return task

    envelope = {
        "task": {k: task.get(k) for k in [
            "id","title","description","client","project","deadline","importance",
            "effort_hours","created_at","labels"
        ]},
        "context": {
            "now": dt.datetime.utcnow().isoformat() + "Z",
            "client_prefs": rules.get("clients",{}),
            "rules_version": "v1",
            "provider": provider
        }
    }
    res = triage_call(envelope)
    if not res:
        return task

    # apply Serena output conservatively
    task["task_type"] = res.get("task_type", task.get("task_type"))
    task["labels"] = sorted(set(task.get("labels", []) + res.get("labels", [])))
    task["effort_hours"] = res.get("effort_hours", task.get("effort_hours"))
    task["importance"] = res.get("importance", task.get("importance"))
    if res.get("checklist"): task["checklist"] = res["checklist"]
    if res.get("subtasks"): task["subtasks"] = res["subtasks"]

    # score overrides if present
    if "score_overrides" in res:
        ov = res["score_overrides"]
        # you can map component overrides to a final score or just rescore
        task["score"] = compute_score(task, rules)

    task["serena_meta"] = {
        "explanations": res.get("explanations", []),
        "policy": res.get("policy", {})
    }
    return task

def _enabled():
    import os
    return os.getenv("SERENA_ENABLED","true").lower() == "true"