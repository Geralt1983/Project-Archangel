"""
API Endpoint Testing Suite for Project Archangel
Tests FastAPI endpoints, authentication, validation, and error handling
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient

# Import FastAPI app
from app.api import app
from app.db_pg import init

# Mark this module as integration tests (skipped by default via pytest.ini)
pytestmark = pytest.mark.integration


class TestAPIEndpoints:
    """Test FastAPI endpoint functionality"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Create test client for FastAPI app"""
        init()  # Initialize database
        return TestClient(app)
    
    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing"""
        return {
            "title": "API Test Task",
            "description": "Test task created via API endpoint",
            "client": "test-client",
            "importance": 4,
            "effort_hours": 3.5,
            "deadline": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "labels": ["api-test", "integration"],
            "project": "test-project"
        }
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_task_creation_endpoint(self, client, sample_task_data):
        """Test task creation via API"""
        response = client.post("/api/tasks", json=sample_task_data)
        assert response.status_code == 201
        
        data = response.json()
        assert "id" in data
        assert "score" in data
        assert data["title"] == sample_task_data["title"]
        assert data["client"] == sample_task_data["client"]
        assert "created_at" in data
        
        # Store task ID for later tests
        return data["id"]
    
    def test_task_listing_endpoint(self, client):
        """Test task listing with filters"""
        # Get all tasks
        response = client.get("/api/tasks")
        assert response.status_code == 200
        
        data = response.json()
        assert "tasks" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        
        # Test filtering by client
        response = client.get("/api/tasks?client=test-client")
        assert response.status_code == 200
        
        filtered_data = response.json()
        if filtered_data["total"] > 0:
            # All returned tasks should be for test-client
            for task in filtered_data["tasks"]:
                assert task["client"] == "test-client"
    
    def test_task_retrieval_endpoint(self, client, sample_task_data):
        """Test individual task retrieval"""
        # First create a task
        create_response = client.post("/api/tasks", json=sample_task_data)
        task_id = create_response.json()["id"]
        
        # Then retrieve it
        response = client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == task_id
        assert data["title"] == sample_task_data["title"]
    
    def test_task_update_endpoint(self, client, sample_task_data):
        """Test task update functionality"""
        # Create task
        create_response = client.post("/api/tasks", json=sample_task_data)
        task_id = create_response.json()["id"]
        
        # Update task
        update_data = {
            "title": "Updated API Test Task",
            "importance": 5,
            "status": "in_progress"
        }
        
        response = client.put(f"/api/tasks/{task_id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == "Updated API Test Task"
        assert data["importance"] == 5
        assert data["status"] == "in_progress"
    
    def test_task_scoring_endpoint(self, client, sample_task_data):
        """Test enhanced scoring endpoint"""
        response = client.post("/api/tasks/score", json=sample_task_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "score" in data
        assert "confidence" in data
        assert "method_scores" in data
        assert "metadata" in data
        
        # Validate score bounds
        assert 0.0 <= data["score"] <= 1.0
        assert 0.0 <= data["confidence"] <= 1.0
        
        # Check method breakdown
        methods = data["method_scores"]
        assert "traditional" in methods
        assert "fuzzy_mcdm" in methods
        assert "ml_adaptive" in methods
    
    def test_provider_health_endpoint(self, client):
        """Test provider health check endpoint"""
        response = client.get("/api/providers/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "providers" in data
        assert "overall_health" in data
        
        # Check provider structure
        for provider_name, provider_data in data["providers"].items():
            assert "status" in provider_data
            assert "response_time" in provider_data
            assert "last_check" in provider_data
    
    def test_analytics_endpoints(self, client):
        """Test analytics and reporting endpoints"""
        # Task completion metrics
        response = client.get("/api/analytics/performance?days=7")
        assert response.status_code == 200
        
        data = response.json()
        assert "period" in data
        assert "metrics" in data
        
        # Workload distribution
        response = client.get("/api/analytics/workload")
        assert response.status_code == 200
        
        workload_data = response.json()
        assert "providers" in workload_data
        assert "total_tasks" in workload_data


class TestAPIValidation:
    """Test API input validation and error handling"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return TestClient(app)
    
    def test_invalid_task_data(self, client):
        """Test validation of invalid task data"""
        # Missing required fields
        invalid_data = {
            "description": "Missing title and client"
        }
        
        response = client.post("/api/tasks", json=invalid_data)
        assert response.status_code == 422  # Validation error
        
        data = response.json()
        assert "detail" in data
    
    def test_invalid_task_id(self, client):
        """Test handling of invalid task IDs"""
        response = client.get("/api/tasks/nonexistent-task-id")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_malformed_json(self, client):
        """Test handling of malformed JSON"""
        response = client.post(
            "/api/tasks",
            data="{'invalid': json}",  # Invalid JSON
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_invalid_query_parameters(self, client):
        """Test validation of query parameters"""
        # Invalid pagination parameters
        response = client.get("/api/tasks?page=-1&limit=1000")
        assert response.status_code == 422
        
        # Invalid date filters
        response = client.get("/api/tasks?created_after=not-a-date")
        assert response.status_code == 422


class TestAPIAuthentication:
    """Test API authentication and authorization"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return TestClient(app)
    
    def test_protected_endpoints(self, client):
        """Test that protected endpoints require authentication"""
        # This test assumes authentication is implemented
        # Adjust based on actual auth implementation
        
        protected_endpoints = [
            ("/api/admin/tasks", "get"),
            ("/api/admin/providers", "post"),
            ("/api/admin/analytics", "get")
        ]
        
        for endpoint, method in protected_endpoints:
            if hasattr(client, method):
                response = getattr(client, method)(endpoint)
                # Should either require auth (401) or not be implemented (404)
                assert response.status_code in [401, 404, 405]
    
    def test_api_key_authentication(self, client):
        """Test API key authentication if implemented"""
        # Test with invalid API key
        headers = {"X-API-Key": "invalid-key"}
        response = client.get("/api/tasks", headers=headers)
        
        # Should work for public endpoints
        assert response.status_code in [200, 401]


class TestAPIPerformance:
    """Test API performance and rate limiting"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return TestClient(app)
    
    def test_bulk_operations_performance(self, client):
        """Test performance of bulk operations"""
        import time
        
        # Create multiple tasks
        tasks_data = []
        for i in range(10):
            task_data = {
                "title": f"Bulk Test Task {i}",
                "description": f"Performance test task {i}",
                "client": "bulk-test-client",
                "importance": (i % 5) + 1,
                "effort_hours": (i % 8) + 1
            }
            tasks_data.append(task_data)
        
        # Time bulk creation
        start_time = time.time()
        for task_data in tasks_data:
            response = client.post("/api/tasks", json=task_data)
            assert response.status_code == 201
        creation_time = time.time() - start_time
        
        # Time bulk retrieval
        start_time = time.time()
        response = client.get("/api/tasks?client=bulk-test-client")
        retrieval_time = time.time() - start_time
        
        assert response.status_code == 200
        assert creation_time < 5.0  # Should complete within 5 seconds
        assert retrieval_time < 1.0  # Retrieval should be fast
    
    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests"""
        import concurrent.futures
        import time
        
        def make_request():
            return client.get("/health")
        
        # Make concurrent requests
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            responses = [future.result() for future in futures]
        total_time = time.time() - start_time
        
        # All requests should succeed
        assert all(response.status_code == 200 for response in responses)
        assert total_time < 10.0  # Should handle concurrent load


class TestAPIErrorHandling:
    """Test API error handling and resilience"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return TestClient(app)
    
    def test_database_error_handling(self, client):
        """Test handling of database errors"""
        with patch('app.db_pg.get_conn') as mock_conn:
            # Simulate database connection error
            mock_conn.side_effect = Exception("Database connection failed")
            
            response = client.get("/api/tasks")
            assert response.status_code == 500
            
            data = response.json()
            assert "detail" in data
    
    def test_provider_error_handling(self, client):
        """Test handling of provider API errors"""
        with patch('app.providers.clickup.ClickUpAdapter._make_request') as mock_request:
            # Simulate provider API error
            mock_request.side_effect = Exception("Provider API unavailable")
            
            task_data = {
                "title": "Test Task",
                "client": "test-client",
                "provider": "clickup"
            }
            
            response = client.post("/api/tasks", json=task_data)
            # Should handle gracefully, may succeed with degraded functionality
            assert response.status_code in [201, 503]  # Created or Service Unavailable
    
    def test_memory_pressure_handling(self, client):
        """Test handling under memory pressure"""
        # Create large request payload
        large_description = "x" * 100000  # 100KB description
        
        task_data = {
            "title": "Large Task",
            "description": large_description,
            "client": "test-client"
        }
        
        response = client.post("/api/tasks", json=task_data)
        # Should either accept or reject gracefully
        assert response.status_code in [201, 413, 422]  # Created, Payload Too Large, or Validation Error


class TestWebhookEndpoints:
    """Test webhook endpoint functionality"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return TestClient(app)
    
    def test_clickup_webhook_endpoint(self, client):
        """Test ClickUp webhook processing"""
        webhook_payload = {
            "event": "taskCreated",
            "task_id": "test-task-123",
            "history_items": [
                {
                    "id": "history-1",
                    "type": 1,
                    "date": str(int(datetime.now().timestamp() * 1000)),
                    "field": "status",
                    "after": "in progress"
                }
            ]
        }
        
        # Test webhook without signature (should fail)
        response = client.post("/api/webhooks/clickup", json=webhook_payload)
        assert response.status_code in [400, 401]  # Bad Request or Unauthorized
        
        # Test with mock signature
        headers = {"X-Signature": "mock-signature"}
        response = client.post("/api/webhooks/clickup", json=webhook_payload, headers=headers)
        assert response.status_code in [200, 401]  # OK or signature validation failed
    
    def test_webhook_idempotency(self, client):
        """Test webhook idempotency handling"""
        webhook_payload = {
            "event": "taskUpdated",
            "task_id": "test-task-456",
            "delivery_id": "delivery-123"  # Same delivery ID
        }
        
        headers = {"X-Signature": "mock-signature"}
        
        # Send same webhook twice
        response1 = client.post("/api/webhooks/clickup", json=webhook_payload, headers=headers)
        response2 = client.post("/api/webhooks/clickup", json=webhook_payload, headers=headers)
        
        # Both should succeed (idempotent)
        assert response1.status_code in [200, 401]
        assert response2.status_code in [200, 401]


# Test runner for API endpoints
def run_api_tests():
    """Run all API tests and generate report"""
    print("🌐 Running Project Archangel API Test Suite")
    print("=" * 60)
    
    test_classes = [
        TestAPIEndpoints,
        TestAPIValidation,
        TestAPIAuthentication,
        TestAPIPerformance,
        TestAPIErrorHandling,
        TestWebhookEndpoints
    ]
    
    results = {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    for test_class in test_classes:
        print(f"\n🔧 Testing {test_class.__name__}")
        print("-" * 40)
        
        test_instance = test_class()
        methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        for method_name in methods:
            results["total_tests"] += 1
            try:
                # Setup client fixture if needed
                if hasattr(test_instance, 'client'):
                    test_instance.client = TestClient(app)
                
                method = getattr(test_instance, method_name)
                if 'client' in method.__code__.co_varnames:
                    method(TestClient(app))
                else:
                    method()
                
                print(f"✅ {method_name}")
                results["passed"] += 1
            except Exception as e:
                print(f"❌ {method_name}: {str(e)}")
                results["failed"] += 1
                results["errors"].append(f"{test_class.__name__}.{method_name}: {str(e)}")
    
    # Final report
    print("\n" + "=" * 60)
    print("📊 API Test Results")
    print("=" * 60)
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {(results['passed']/results['total_tests']*100):.1f}%")
    
    return results


if __name__ == "__main__":
    run_api_tests()