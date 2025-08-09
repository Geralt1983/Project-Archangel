import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base, get_db

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    # Override the dependency
    from app import db
    original_get_db = db.get_db
    db.get_db = override_get_db
    
    yield TestingSessionLocal
    
    # Restore original function
    db.get_db = original_get_db

@pytest.fixture
def sample_rules():
    """Sample rules configuration for testing."""
    return {
        "defaults": {
            "aging_boost_per_day": 2,
            "stale_after_days": 3,
            "nudge_channel": "slack:#ops"
        },
        "clients": {
            "acme": {
                "sla_hours": 48,
                "daily_cap_hours": 3,
                "importance_bias": 1.2
            },
            "meridian": {
                "sla_hours": 24,
                "daily_cap_hours": 2,
                "importance_bias": 1.5
            },
            "unknown": {
                "sla_hours": 72,
                "daily_cap_hours": 4,
                "importance_bias": 1.0
            }
        },
        "task_types": {
            "bugfix": {
                "labels": ["bug", "fix"],
                "checklist": ["Confirm repro", "Assess impact", "Patch", "Regression test", "Notify client"],
                "subtasks": [
                    {"title": "Draft fix plan", "effort_hours": 0.5},
                    {"title": "Implement", "effort_hours": 1.0},
                    {"title": "Review", "effort_hours": 0.25},
                    {"title": "Deliver", "effort_hours": 0.25},
                    {"title": "Follow up", "effort_hours": 0.25}
                ],
                "default_effort_hours": 2,
                "importance": 4
            },
            "report": {
                "labels": ["report", "analysis"],
                "checklist": ["Define question", "Pull data", "QA results", "Share link"],
                "subtasks": [
                    {"title": "Draft", "effort_hours": 1.5},
                    {"title": "Review", "effort_hours": 0.5},
                    {"title": "Deliver", "effort_hours": 0.5},
                    {"title": "Follow up", "effort_hours": 0.5}
                ],
                "default_effort_hours": 3,
                "importance": 3
            },
            "onboarding": {
                "labels": ["setup"],
                "checklist": ["Collect access", "Create project", "Baseline tasks"],
                "subtasks": [
                    {"title": "Prepare", "effort_hours": 0.5},
                    {"title": "Execute", "effort_hours": 0.75},
                    {"title": "Confirm access", "effort_hours": 0.25}
                ],
                "default_effort_hours": 1.5,
                "importance": 3
            },
            "general": {
                "labels": ["task"],
                "checklist": ["Review requirements", "Plan approach", "Execute", "Validate results"],
                "subtasks": [
                    {"title": "Plan", "effort_hours": 0.5},
                    {"title": "Execute", "effort_hours": 1.0},
                    {"title": "Review", "effort_hours": 0.5}
                ],
                "default_effort_hours": 2,
                "importance": 2
            }
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

@pytest.fixture
def mock_clickup_adapter():
    """Mock ClickUp adapter for testing."""
    class MockClickUpAdapter:
        name = "clickup"
        
        def __init__(self):
            self.created_tasks = []
            self.created_subtasks = []
            self.added_checklists = []
            self.updated_statuses = []
        
        def create_task(self, task):
            task_data = {
                "id": f"clickup_{len(self.created_tasks) + 1}",
                "name": task.title,
                "status": "Open"
            }
            self.created_tasks.append(task_data)
            return task_data
        
        def create_subtasks(self, parent_external_id, subtasks):
            created = []
            for i, subtask in enumerate(subtasks):
                subtask_data = {
                    "id": f"clickup_sub_{len(self.created_subtasks) + 1}",
                    "name": subtask.title,
                    "parent": parent_external_id
                }
                self.created_subtasks.append(subtask_data)
                created.append(subtask_data)
            return created
        
        def add_checklist(self, external_id, items):
            self.added_checklists.append({
                "task_id": external_id,
                "items": items
            })
        
        def update_status(self, external_id, status):
            self.updated_statuses.append({
                "task_id": external_id,
                "status": status
            })
        
        def get_task(self, external_id):
            # Find task by ID
            for task in self.created_tasks:
                if task["id"] == external_id:
                    return task
            return None
        
        def verify_webhook(self, headers, raw_body):
            # For testing, always return True
            return True
        
        def supports_subtasks(self):
            return True
        
        def supports_checklists(self):
            return True
    
    return MockClickUpAdapter()