import pytest
from datetime import datetime, timezone, timedelta
from app.models import Task, TaskStatus
from app.scoring import compute_score, is_task_stale, is_sla_at_risk, clamp

def test_clamp():
    """Test the clamp utility function."""
    assert clamp(0.5, 0, 1) == 0.5
    assert clamp(-0.5, 0, 1) == 0.0
    assert clamp(1.5, 0, 1) == 1.0

def test_score_increases_with_deadline_pressure():
    """Test that tasks with closer deadlines get higher scores."""
    base_time = datetime.now(timezone.utc)
    
    # Task with deadline in 2 days
    task1 = Task(
        id="test1",
        title="Test task 1",
        client="acme",
        deadline=base_time + timedelta(days=2),
        importance=3,
        effort_hours=2,
        created_at=base_time - timedelta(hours=1)
    )
    
    # Task with deadline in 1 day (more urgent)
    task2 = Task(
        id="test2", 
        title="Test task 2",
        client="acme",
        deadline=base_time + timedelta(days=1),
        importance=3,
        effort_hours=2,
        created_at=base_time - timedelta(hours=1)
    )
    
    rules = {
        "defaults": {"aging_boost_per_day": 2},
        "clients": {"acme": {"sla_hours": 48, "importance_bias": 1.0}},
        "scoring": {
            "urgency_weight": 0.30,
            "importance_weight": 0.25,
            "effort_weight": 0.15,
            "freshness_weight": 0.10,
            "sla_weight": 0.15,
            "progress_weight": 0.05
        }
    }
    
    score1 = compute_score(task1, rules)
    score2 = compute_score(task2, rules)
    
    assert score2 > score1, f"More urgent task should have higher score: {score2} > {score1}"

def test_importance_affects_score():
    """Test that higher importance tasks get higher scores."""
    base_time = datetime.now(timezone.utc)
    
    # Low importance task
    task1 = Task(
        id="test1",
        title="Low priority task",
        client="acme", 
        importance=1,
        effort_hours=2,
        created_at=base_time - timedelta(hours=1)
    )
    
    # High importance task
    task2 = Task(
        id="test2",
        title="High priority task", 
        client="acme",
        importance=5,
        effort_hours=2,
        created_at=base_time - timedelta(hours=1)
    )
    
    rules = {
        "defaults": {"aging_boost_per_day": 2},
        "clients": {"acme": {"sla_hours": 48, "importance_bias": 1.0}},
        "scoring": {
            "urgency_weight": 0.30,
            "importance_weight": 0.25,
            "effort_weight": 0.15,
            "freshness_weight": 0.10,
            "sla_weight": 0.15,
            "progress_weight": 0.05
        }
    }
    
    score1 = compute_score(task1, rules)
    score2 = compute_score(task2, rules)
    
    assert score2 > score1, f"Higher importance task should have higher score: {score2} > {score1}"

def test_client_importance_bias():
    """Test that client importance bias affects scoring."""
    base_time = datetime.now(timezone.utc)
    
    task = Task(
        id="test1",
        title="Test task",
        client="meridian",  # Has 1.5x importance bias
        importance=3,
        effort_hours=2,
        created_at=base_time - timedelta(hours=1)
    )
    
    rules = {
        "defaults": {"aging_boost_per_day": 2},
        "clients": {
            "meridian": {"sla_hours": 24, "importance_bias": 1.5},
            "acme": {"sla_hours": 48, "importance_bias": 1.0}
        },
        "scoring": {
            "urgency_weight": 0.30,
            "importance_weight": 0.25,
            "effort_weight": 0.15,
            "freshness_weight": 0.10,
            "sla_weight": 0.15,
            "progress_weight": 0.05
        }
    }
    
    score_meridian = compute_score(task, rules)
    
    # Same task for different client
    task.client = "acme"
    score_acme = compute_score(task, rules)
    
    assert score_meridian > score_acme, "Client with higher bias should get higher score"

def test_aging_boost():
    """Test that older tasks get aging boost."""
    base_time = datetime.now(timezone.utc)
    
    # New task
    task1 = Task(
        id="test1",
        title="New task",
        client="acme",
        importance=3,
        effort_hours=2,
        created_at=base_time - timedelta(hours=1)
    )
    
    # Old task (3 days old)
    task2 = Task(
        id="test2", 
        title="Old task",
        client="acme",
        importance=3,
        effort_hours=2,
        created_at=base_time - timedelta(days=3)
    )
    
    rules = {
        "defaults": {"aging_boost_per_day": 5},  # Higher boost for testing
        "clients": {"acme": {"sla_hours": 48, "importance_bias": 1.0}},
        "scoring": {
            "urgency_weight": 0.30,
            "importance_weight": 0.25,
            "effort_weight": 0.15,
            "freshness_weight": 0.10,
            "sla_weight": 0.15,
            "progress_weight": 0.05
        }
    }
    
    score1 = compute_score(task1, rules)
    score2 = compute_score(task2, rules)
    
    assert score2 > score1, f"Older task should have higher score due to aging: {score2} > {score1}"

def test_is_task_stale():
    """Test stale task detection."""
    now = datetime.now(timezone.utc)
    
    # Fresh task
    fresh_task = Task(
        id="test1",
        title="Fresh task",
        client="acme",
        updated_at=now - timedelta(hours=12)
    )
    
    # Stale task  
    stale_task = Task(
        id="test2",
        title="Stale task", 
        client="acme",
        updated_at=now - timedelta(days=5)
    )
    
    rules = {"defaults": {"stale_after_days": 3}}
    
    assert not is_task_stale(fresh_task, rules)
    assert is_task_stale(stale_task, rules)

def test_is_sla_at_risk():
    """Test SLA risk detection."""
    now = datetime.now(timezone.utc)
    
    # Task created recently, plenty of time
    safe_task = Task(
        id="test1",
        title="Safe task",
        client="acme",
        client_sla_hours=48,
        created_at=now - timedelta(hours=2)
    )
    
    # Task approaching SLA
    risky_task = Task(
        id="test2",
        title="Risky task",
        client="acme", 
        client_sla_hours=48,
        created_at=now - timedelta(hours=40)  # 8 hours left, under 12h threshold
    )
    
    assert not is_sla_at_risk(safe_task)
    assert is_sla_at_risk(risky_task)

def test_score_capping():
    """Test that scores are capped at 1.0."""
    base_time = datetime.now(timezone.utc)
    
    # Extreme task with everything maxed out
    extreme_task = Task(
        id="extreme",
        title="Extreme urgent task",
        client="meridian",
        importance=5,
        effort_hours=0.5,  # Small effort
        deadline=base_time - timedelta(hours=1),  # Past deadline
        client_sla_hours=1,  # Very short SLA
        created_at=base_time - timedelta(days=10),  # Very old
        recent_progress=0.0  # No progress
    )
    
    rules = {
        "defaults": {"aging_boost_per_day": 10},  # High aging boost
        "clients": {"meridian": {"sla_hours": 1, "importance_bias": 2.0}},
        "scoring": {
            "urgency_weight": 0.30,
            "importance_weight": 0.25,
            "effort_weight": 0.15,
            "freshness_weight": 0.10,
            "sla_weight": 0.15,
            "progress_weight": 0.05
        }
    }
    
    score = compute_score(extreme_task, rules)
    
    assert score <= 1.0, f"Score should be capped at 1.0, got {score}"