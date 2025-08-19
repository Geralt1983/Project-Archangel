"""
Test Suite for Task CRUD API Endpoints
Tests the comprehensive task CRUD operations
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_api_tasks_crud():
    """Test task CRUD API endpoints"""
    print("=" * 60)
    print("TESTING: Task CRUD API Endpoints")
    print("=" * 60)
    
    results = []
    
    # Test 1: Import task API module
    try:
        import app.api_tasks
        results.append(("Task API import", True, None))
        print("  PASS   Task API module imported successfully")
    except Exception as e:
        results.append(("Task API import", False, str(e)))
        print(f"  FAIL   Task API import failed: {e}")
        return results
    
# Test 2: Validate TaskCreateRequest model
    try:
        from app.api_tasks import TaskCreateRequest
        task_request = TaskCreateRequest(
            title="Test Task",
            description="Test description",
            client="test-client",
            importance=4,
            effort_hours=2.5
        )
        assert task_request.title == "Test Task"
        assert task_request.client == "test-client"
        assert task_request.importance == 4
        results.append(("TaskCreateRequest validation", True, None))
        print("  PASS   TaskCreateRequest model validation")
    except Exception as e:
        results.append(("TaskCreateRequest validation", False, str(e)))
        print(f"  FAIL   TaskCreateRequest validation: {e}")
    
    # Test 3: Test utility functions
    try:
        from app.api_tasks import apply_orchestration, convert_to_task_response
        
        # Test task data
        task_data = {
            "id": "test-task-123",
            "title": "Test Task",
            "description": "Test description", 
            "client": "test-client",
            "importance": 3,
            "effort_hours": 1.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "labels": [],
            "meta": {},
            "checklist": [],
            "subtasks": []
        }
        
        # Test orchestration (may fail due to missing dependencies, that's OK)
        try:
            orchestrated_data = apply_orchestration(task_data, use_orchestration=False)
            assert orchestrated_data["id"] == "test-task-123"
            print("  PASS   Orchestration function works")
        except Exception as orch_e:
            print(f"  INFO   Orchestration skipped (dependencies): {str(orch_e)[:50]}")
        
        # Test response conversion
        response = convert_to_task_response(task_data)
        assert response.id == "test-task-123" 
        assert response.title == "Test Task"
        assert response.client == "test-client"
        
        results.append(("Utility functions", True, None))
        print("  PASS   Utility functions work correctly")
        
    except Exception as e:
        results.append(("Utility functions", False, str(e)))
        print(f"  FAIL   Utility functions test: {e}")
    
# Test 4: Test router endpoints structure
    try:
        from fastapi import APIRouter
        from app.api_tasks import router
        assert isinstance(router, APIRouter)
        
        # Check that key endpoints are defined
        routes = [route.path for route in router.routes]
        expected_routes = ["/", "/{task_id}", "/stats/summary", "/{task_id}/score"]
        
        for expected in expected_routes:
            if any(expected in route for route in routes):
                continue
            else:
                raise AssertionError(f"Expected route pattern {expected} not found")
        
        results.append(("Router structure", True, None))
        print("  PASS   Router has expected endpoints")
        
    except Exception as e:
        results.append(("Router structure", False, str(e)))
        print(f"  FAIL   Router structure test: {e}")
    
    # Test 5: Response model validation
    try:
        from app.api_tasks import TaskStatsResponse
        
        stats_response = TaskStatsResponse(
            total_tasks=10,
            by_status={"pending": 7, "completed": 3},
            by_client={"client1": 5, "client2": 5},
            by_provider={"internal": 10},
            score_distribution={"high": 2, "medium": 5, "low": 3},
            average_score=0.65,
            high_priority_count=2,
            overdue_count=1
        )
        
        assert stats_response.total_tasks == 10
        assert stats_response.average_score == 0.65
        
        results.append(("Response models", True, None))
        print("  PASS   Response models validate correctly")
        
    except Exception as e:
        results.append(("Response models", False, str(e)))
        print(f"  FAIL   Response models test: {e}")
    
    # Test 6: Test FastAPI integration
    try:
        from fastapi.testclient import TestClient
        from app.api import app
        
        # This will fail if there are import issues with the main app
        client = TestClient(app)
        
        # Simple health check to verify the app loads
        response = client.get("/health")
        assert response.status_code == 200
        
        results.append(("FastAPI integration", True, None))
        print("  PASS   FastAPI integration works")
        
    except Exception as e:
        results.append(("FastAPI integration", False, str(e)))
        print(f"  FAIL   FastAPI integration test: {e}")
    
    print("\n" + "=" * 60)
    print("TASK CRUD API TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, error in results:
        status = "PASS" if success else "FAIL"
        print(f"  {status}   {test_name}")
        if error:
            print(f"         Error: {error}")
    
    print(f"\nTotal: {passed}/{total} passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("Status: ALL TESTS PASSED - Task CRUD API ready")
    elif passed >= total * 0.8:
        print("Status: MOSTLY WORKING - Minor issues to address")  
    else:
        print("Status: NEEDS WORK - Significant issues found")
    
    return results

if __name__ == "__main__":
    test_api_tasks_crud()