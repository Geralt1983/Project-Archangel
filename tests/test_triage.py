import pytest
from datetime import datetime, timezone
from app.models import TaskIntake, TaskStatus
from app.triage import normalize_task_input, classify_task, fill_task_defaults

def test_normalize_task_input():
    """Test task input normalization."""
    intake = TaskIntake(
        title="  Fix bug in login system  ",
        description="  Users can't log in  ",
        client="  ACME  ",
        importance=4
    )
    
    task = normalize_task_input(intake)
    
    assert task.title == "Fix bug in login system"
    assert task.description == "Users can't log in"
    assert task.client == "acme"  # Should be lowercased
    assert task.importance == 4
    assert task.id.startswith("tsk_")
    assert task.status == TaskStatus.NEW
    assert task.idempotency_key is not None
    assert isinstance(task.created_at, datetime)

def test_classify_bugfix():
    """Test classification of bug fix tasks."""
    task = normalize_task_input(TaskIntake(
        title="Fix 500 error on user registration",
        description="Server crashes when users try to register",
        client="acme"
    ))
    
    classify_task(task)
    
    assert task.task_type == "bugfix"

def test_classify_report():
    """Test classification of report tasks.""" 
    task = normalize_task_input(TaskIntake(
        title="Generate monthly analytics dashboard",
        description="Create report showing user metrics and KPIs",
        client="acme"
    ))
    
    classify_task(task)
    
    assert task.task_type == "report"

def test_classify_onboarding():
    """Test classification of onboarding tasks."""
    task = normalize_task_input(TaskIntake(
        title="Setup new client project access",
        description="Provision accounts and configure permissions",
        client="acme"
    ))
    
    classify_task(task)
    
    assert task.task_type == "onboarding"

def test_classify_general():
    """Test classification falls back to general."""
    task = normalize_task_input(TaskIntake(
        title="Update documentation for API endpoints",
        description="Document the new REST API changes",
        client="acme"
    ))
    
    classify_task(task)
    
    assert task.task_type == "general"

def test_client_extraction_from_title():
    """Test extracting client name from title prefix."""
    task = normalize_task_input(TaskIntake(
        title="[MERIDIAN] Fix payment processing issue",
        description="Payment gateway is failing",
        client="unknown"
    ))
    
    classify_task(task)
    
    assert task.client == "meridian"
    assert task.title == "Fix payment processing issue"  # Prefix removed

def test_fill_task_defaults():
    """Test filling default values based on task type."""
    task = normalize_task_input(TaskIntake(
        title="Fix critical bug",
        client="acme"
    ))
    
    task.task_type = "bugfix"
    fill_task_defaults(task)
    
    # Should get bugfix defaults
    assert task.effort_hours == 2.0  # From rules.yaml
    assert task.importance == 4      # From rules.yaml  
    assert "bug" in task.labels
    assert "fix" in task.labels
    assert task.client_sla_hours == 48  # From client config

def test_fill_defaults_preserves_existing():
    """Test that existing values are not overridden."""
    task = normalize_task_input(TaskIntake(
        title="Fix bug",
        client="acme",
        effort_hours=1.5,
        importance=5
    ))
    
    task.task_type = "bugfix"
    fill_task_defaults(task)
    
    # Should preserve original values
    assert task.effort_hours == 1.5
    assert task.importance == 5

def test_unknown_client_gets_defaults():
    """Test that unknown clients get default configuration."""
    task = normalize_task_input(TaskIntake(
        title="Some task",
        client="unknown_client" 
    ))
    
    fill_task_defaults(task)
    
    # Should get unknown client defaults
    assert task.client_sla_hours == 72  # From rules.yaml unknown client

def test_task_type_labels_merge():
    """Test that task type labels are merged with existing labels."""
    task = normalize_task_input(TaskIntake(
        title="Fix urgent bug",
        client="acme",
        labels=["urgent", "critical"]
    ))
    
    task.task_type = "bugfix"
    fill_task_defaults(task)
    
    # Should have both original and task type labels
    assert "urgent" in task.labels
    assert "critical" in task.labels  
    assert "bug" in task.labels
    assert "fix" in task.labels
    
    # Should not have duplicates
    label_counts = {}
    for label in task.labels:
        label_counts[label] = label_counts.get(label, 0) + 1
    
    for label, count in label_counts.items():
        assert count == 1, f"Label '{label}' appears {count} times"

def test_importance_validation():
    """Test importance value validation and correction."""
    # Test invalid importance gets corrected
    task = normalize_task_input(TaskIntake(
        title="Test task",
        client="acme",
        importance=10  # Invalid - too high
    ))
    
    task.task_type = "general"
    fill_task_defaults(task)
    
    # Should get task type default
    assert task.importance == 2  # From rules.yaml general task

def test_multiple_classification_keywords():
    """Test classification with multiple matching keywords."""
    task = normalize_task_input(TaskIntake(
        title="Generate error report for failed bug fixes",
        description="Analyze recent failures and create dashboard",
        client="acme"
    ))
    
    classify_task(task)
    
    # Should classify as report (appears first in title)
    assert task.task_type == "report"