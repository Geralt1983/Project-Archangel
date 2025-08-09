from .config import load_rules

def build_checklist_and_subtasks(task: dict):
    rules = load_rules()
    tt = rules["task_types"].get(task["task_type"], {})
    checklist = tt.get("checklist", [])
    subtasks = [{"title": s["title"], "status": "new"} for s in tt.get("subtasks", [])]
    return checklist, subtasks