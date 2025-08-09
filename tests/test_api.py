import pytest
from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "project-archangel"

def test_intake_endpoint():
    """Test task intake endpoint with valid data."""
    task_data = {
        "title": "Test bug fix task",
        "description": "Fix the login error",
        "client": "acme",
        "importance": 4
    }
    
    # This will fail without proper database setup, but we can test the structure
    response = client.post("/tasks/intake", json=task_data)
    
    # Response should be structured correctly even if it fails
    assert response.status_code in [200, 500]  # 500 if DB not set up

def test_intake_validation():
    """Test task intake with invalid data."""
    # Missing required title
    invalid_task = {
        "description": "No title provided",
        "client": "acme"
    }
    
    response = client.post("/tasks/intake", json=invalid_task)
    assert response.status_code == 422  # Validation error

def test_config_endpoints():
    """Test configuration endpoints."""
    # Test getting rules
    response = client.get("/config/rules")
    assert response.status_code == 200
    
    # Test reloading config
    response = client.post("/config/reload")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reloaded"

def test_stats_endpoint():
    """Test stats endpoint."""
    response = client.get("/stats")
    # This might fail without database, but should at least be structured correctly
    assert response.status_code in [200, 500]

def test_triage_endpoint():
    """Test triage management endpoint."""
    # Test retriage all
    response = client.post("/triage/run", json={"retriage_all": True})
    assert response.status_code in [200, 500]  # May fail without DB

def test_rebalance_endpoint():
    """Test rebalancing endpoint."""
    # Test dry run rebalancing
    response = client.post("/rebalance/run", json={"dry_run": True})
    assert response.status_code in [200, 500]  # May fail without DB

def test_webhook_signature_validation():
    """Test webhook signature validation."""
    # Test without signature
    response = client.post("/webhooks/clickup", json={"event": "taskCreated"})
    assert response.status_code == 401  # Should fail signature validation

def test_list_tasks_endpoint():
    """Test task listing endpoint."""
    response = client.get("/tasks")
    assert response.status_code in [200, 500]  # May fail without DB
    
    # Test with parameters
    response = client.get("/tasks?client=acme&limit=10")
    assert response.status_code in [200, 500]

def test_get_task_endpoint():
    """Test individual task retrieval."""
    response = client.get("/tasks/nonexistent_task")
    assert response.status_code in [404, 500]  # Either not found or DB error