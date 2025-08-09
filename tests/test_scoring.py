from app.scoring import compute_score

def test_score_increases_with_deadline_pressure():
    t = {
        "deadline": "2025-08-10T12:00:00Z",
        "importance": 3,
        "effort_hours": 2,
        "client": "acme",
        "recent_progress": 0.0,
        "created_at": "2025-08-08T12:00:00Z"
    }
    rules = {"clients": {"acme": {"importance_bias": 1.2, "sla_hours": 48}}}
    s1 = compute_score(t, rules)
    t["deadline"] = "2025-08-09T14:00:00Z"
    s2 = compute_score(t, rules)
    assert s2 > s1