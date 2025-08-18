from fastapi import FastAPI
app = FastAPI()

@app.post("/v1/triage")
def triage(envelope: dict):
    t = envelope["task"]
    name = t["title"].lower()
    if any(k in name for k in ["fix","error","bug","500"]):
        tt = "bugfix"
        chk = ["Confirm repro","Assess impact","Patch","Regression test","Notify client"]
        subs = [
            {"title":"Draft fix plan"},
            {"title":"Implement"},
            {"title":"Review"},
            {"title":"Deliver"},
            {"title":"Follow up"}
        ]
        imp = 4
    else:
        tt = "general"
        chk = ["Clarify ask","Define done","Confirm deadline"]
        subs = [{"title":"Draft"},{"title":"Review"}]
        imp = 3
    return {
      "task_type": tt,
      "labels": [tt],
      "effort_hours": t.get("effort_hours",1),
      "importance": imp,
      "checklist": chk,
      "subtasks": subs,
      "score_overrides": {"notes": "mock"},
      "explanations": ["mock rules"],
      "policy": {"hold_creation": False, "requires_review": False}
    }

@app.post("/v1/rebalance")
def rebalance(payload: dict):
    tasks = sorted(payload["tasks"], key=lambda x: x["score"], reverse=True)
    plan = {}
    hours = payload["constraints"]["available_hours_today"]
    caps = payload["constraints"]["client_caps"]
    used = {c: 0.0 for c in caps}
    for t in tasks:
        c = t["client"]
        need = max(0.25, float(t.get("effort_hours",1.0)))
        if used[c] + need <= caps.get(c, 2) and need <= hours:
            plan.setdefault(c, []).append(t["id"])
            used[c] += need
            hours -= need
    return {"plan": plan, "rationale": "mock greedy"}