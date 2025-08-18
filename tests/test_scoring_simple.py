"""
Simple scoring tests to verify monotonicity and correctness
"""

from datetime import datetime, timezone, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.scoring import compute_score

def test_scoring_monotonicity_deadline():
    """Due date closer must not decrease score (holding other fields constant)"""
    
    base_task = {
        "id": "test_1",
        "title": "Test Task",
        "client": "test-client",
        "importance": 3,
        "effort_hours": 2.0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "recent_progress": 0.0
    }
    
    rules = {"clients": {"test-client": {"importance_bias": 1.0, "sla_hours": 72}}}
    
    # Task due in 7 days
    far_task = base_task.copy()
    far_task["deadline"] = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    
    # Task due in 1 day (closer deadline)
    near_task = base_task.copy() 
    near_task["deadline"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    
    far_score = compute_score(far_task, rules)
    near_score = compute_score(near_task, rules)
    
    # Closer deadline should have higher urgency and thus higher score
    assert near_score >= far_score, f"Near deadline score {near_score} should be >= far deadline score {far_score}"

def test_scoring_monotonicity_progress():
    """Higher recent_progress must not increase the 'no movement' term"""
    
    base_task = {
        "id": "test_2",
        "title": "Test Task", 
        "client": "test-client",
        "importance": 3,
        "effort_hours": 2.0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "deadline": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    }
    
    rules = {"clients": {"test-client": {"importance_bias": 1.0, "sla_hours": 72}}}
    
    # Task with no recent progress
    no_progress_task = base_task.copy()
    no_progress_task["recent_progress"] = 0.0
    
    # Task with recent progress
    progress_task = base_task.copy()
    progress_task["recent_progress"] = 0.8
    
    no_progress_score = compute_score(no_progress_task, rules)
    progress_score = compute_score(progress_task, rules)
    
    # Task with more recent progress should have lower "no movement" penalty, thus lower score
    assert progress_score <= no_progress_score, f"Progress score {progress_score} should be <= no progress score {no_progress_score}"

def test_effort_factor_inverted():
    """Smaller tasks should get higher effort factor score"""
    
    base_task = {
        "id": "test_3",
        "title": "Test Task",
        "client": "test-client", 
        "importance": 3,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "deadline": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        "recent_progress": 0.0
    }
    
    rules = {"clients": {"test-client": {"importance_bias": 1.0, "sla_hours": 72}}}
    
    # Small task (0.5 hours)
    small_task = base_task.copy()
    small_task["effort_hours"] = 0.5
    
    # Large task (8 hours)
    large_task = base_task.copy()
    large_task["effort_hours"] = 8.0
    
    small_score = compute_score(small_task, rules)
    large_score = compute_score(large_task, rules)
    
    # Small task should have higher score due to inverted effort factor
    assert small_score > large_score, f"Small task score {small_score} should be > large task score {large_score}"

def test_urgency_flags_set():
    """Scorer should set deadline_within_24h and sla_pressure flags"""
    
    # Task due in 12 hours (within 24h)
    urgent_task = {
        "id": "test_4",
        "title": "Urgent Task",
        "client": "test-client",
        "importance": 3,
        "effort_hours": 2.0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "deadline": (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
        "recent_progress": 0.0
    }
    
    rules = {"clients": {"test-client": {"importance_bias": 1.0, "sla_hours": 72}}}
    
    _ = compute_score(urgent_task, rules)
    
    # Check that urgency flags are set
    assert "deadline_within_24h" in urgent_task
    assert urgent_task["deadline_within_24h"]
    assert "sla_pressure" in urgent_task
    assert isinstance(urgent_task["sla_pressure"], float)

def test_sla_pressure_calculation():
    """SLA pressure should be calculated correctly based on time since creation"""
    
    # Task created 60 hours ago (within 72h SLA but approaching)
    old_creation_time = datetime.now(timezone.utc) - timedelta(hours=60)
    
    task = {
        "id": "test_5",
        "title": "SLA Test Task",
        "client": "test-client", 
        "importance": 3,
        "effort_hours": 2.0,
        "created_at": old_creation_time.isoformat(),
        "deadline": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        "recent_progress": 0.0
    }
    
    rules = {"clients": {"test-client": {"importance_bias": 1.0, "sla_hours": 72}}}
    
    _ = compute_score(task, rules)
    
    # Should have significant SLA pressure (12 hours left out of 72)
    assert task["sla_pressure"] > 0.5, f"SLA pressure {task['sla_pressure']} should be > 0.5 with 12h left in 72h SLA"

if __name__ == "__main__":
    # Run basic tests
    test_scoring_monotonicity_deadline()
    test_scoring_monotonicity_progress() 
    test_effort_factor_inverted()
    test_urgency_flags_set()
    test_sla_pressure_calculation()
    print("✅ All scoring tests passed!")