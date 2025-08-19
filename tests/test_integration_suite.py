"""
Comprehensive Integration Test Suite for Project Archangel Initial Build
Tests core task orchestration functionality, database operations, and provider integrations
"""

import pytest
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

# Import Project Archangel components
from app.db_pg import init, get_conn, save_task, fetch_open_tasks, map_upsert, map_get_internal
from app.scoring import compute_score
from app.scoring_enhanced import compute_enhanced_score, compute_score_with_details
from app.providers.clickup import ClickUpAdapter
from app.utils.outbox import OutboxManager, make_idempotency_key
from app.utils.retry import retry, retry_async, next_backoff


class TestDatabaseOperations:
    """Test core database operations and schema"""
    
    @pytest.fixture(scope="class")
    def db_setup(self):
        """Setup test database"""
        # Initialize database schema
        init()
        yield
        # Cleanup would go here if needed
    
    def test_database_initialization(self, db_setup):
        """Test database schema initialization"""
        conn = get_conn()
        cursor = conn.cursor()
        
        # Check that all required tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['events', 'tasks', 'outbox', 'providers', 'task_routing_history']
        for table in required_tables:
            assert table in tables, f"Required table '{table}' not found"
    
    def test_task_crud_operations(self, db_setup):
        """Test task creation, reading, updating"""
        now = datetime.now(timezone.utc)
        
        # Create test task
        test_task = {
            "id": "test-task-001",
            "external_id": "clickup-123",
            "provider": "clickup",
            "title": "Test Task for Integration",
            "description": "Integration test task",
            "importance": 4.0,
            "effort_hours": 3.0,
            "deadline": (now + timedelta(hours=24)).isoformat(),
            "client": "test-client",
            "status": "triaged",
            "score": 0.75,
            "created_at": now.isoformat()
        }
        
        # Save task
        save_task(test_task)
        
        # Fetch open tasks
        open_tasks = fetch_open_tasks()
        task_ids = [task.get("id") for task in open_tasks]
        assert "test-task-001" in task_ids
        
        # Test task mapping
        map_upsert("clickup", "clickup-123", "test-task-001")
        internal_id = map_get_internal("clickup", "clickup-123")
        assert internal_id == "test-task-001"
    
    def test_provider_schema(self, db_setup):
        """Test provider configuration storage"""
        conn = get_conn()
        cursor = conn.cursor()
        
        # Insert test provider
        cursor.execute("""
            INSERT INTO providers (id, name, type, config, health_status, active_tasks, wip_limit)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                health_status = EXCLUDED.health_status,
                active_tasks = EXCLUDED.active_tasks
        """, (
            "test-clickup-001",
            "Test ClickUp Instance",
            "clickup",
            json.dumps({"team_id": "123", "list_id": "456"}),
            "active",
            5,
            10
        ))
        
        # Verify provider was stored
        cursor.execute("SELECT * FROM providers WHERE id = %s", ("test-clickup-001",))
        result = cursor.fetchone()
        assert result is not None
        assert result[1] == "Test ClickUp Instance"  # name
        assert result[2] == "clickup"  # type


class TestScoringAlgorithms:
    """Test both traditional and enhanced scoring algorithms"""
    
    @pytest.fixture
    def sample_rules(self):
        """Sample scoring rules configuration"""
        return {
            "clients": {
                "acme": {
                    "importance_bias": 1.2,
                    "sla_hours": 48,
                    "priority_multiplier": 1.5,
                    "urgency_threshold": 0.8,
                    "complexity_preference": 0.3
                },
                "beta": {
                    "importance_bias": 0.9,
                    "sla_hours": 72,
                    "priority_multiplier": 1.0,
                    "urgency_threshold": 0.6,
                    "complexity_preference": 0.7
                }
            }
        }
    
    def test_traditional_scoring_algorithm(self, sample_rules):
        """Test traditional weighted scoring"""
        now = datetime.now(timezone.utc)
        
        # High priority urgent task
        urgent_task = {
            "client": "acme",
            "importance": 5.0,
            "effort_hours": 2.0,
            "deadline": (now + timedelta(hours=4)).isoformat(),
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "recent_progress": 0.0
        }
        
        # Low priority task
        low_priority_task = {
            "client": "beta",
            "importance": 2.0,
            "effort_hours": 8.0,
            "deadline": (now + timedelta(days=7)).isoformat(),
            "created_at": (now - timedelta(days=2)).isoformat(),
            "recent_progress": 0.5
        }
        
        urgent_score = compute_score(urgent_task, sample_rules)
        low_score = compute_score(low_priority_task, sample_rules)
        
        # Urgent task should score higher
        assert urgent_score > low_score
        assert urgent_score > 0.7  # Should be high priority
        assert low_score < 0.5     # Should be lower priority
    
    def test_enhanced_scoring_algorithm(self, sample_rules):
        """Test enhanced ensemble scoring"""
        now = datetime.now(timezone.utc)
        
        # Complex task with dependencies
        complex_task = {
            "client": "acme",
            "importance": 4.0,
            "effort_hours": 12.0,
            "deadline": (now + timedelta(hours=8)).isoformat(),
            "created_at": now.isoformat(),
            "task_type": "bugfix",
            "assigned_provider": "clickup",
            "dependencies": ["task-1", "task-2"],
            "historical_similar_tasks": 8,
            "user_feedback_score": 0.9
        }
        
        # Get detailed scoring results
        result = compute_score_with_details(complex_task, sample_rules)
        
        # Validate result structure
        assert "score" in result
        assert "confidence" in result
        assert "uncertainty" in result
        assert "method_scores" in result
        assert "metadata" in result
        
        # Check score bounds
        assert 0.0 <= result["score"] <= 1.0
        assert 0.0 <= result["confidence"] <= 1.0
        
        # Check method breakdown
        methods = result["method_scores"]
        assert "traditional" in methods
        assert "fuzzy_mcdm" in methods
        assert "ml_adaptive" in methods
        
        # Check metadata
        metadata = result["metadata"]
        assert "urgency_level" in metadata
        assert "complexity_level" in metadata
        assert metadata["urgency_level"] in ["critical", "high", "medium", "low"]
        assert metadata["complexity_level"] in ["simple", "moderate", "complex", "epic"]
    
    def test_scoring_comparison_and_consistency(self, sample_rules):
        """Test consistency between traditional and enhanced scoring"""
        now = datetime.now(timezone.utc)
        
        test_cases = [
            {
                "name": "Critical Urgent Task",
                "task": {
                    "client": "acme",
                    "importance": 5.0,
                    "effort_hours": 1.0,
                    "deadline": (now + timedelta(hours=2)).isoformat(),
                    "created_at": now.isoformat(),
                    "recent_progress": 0.0
                }
            },
            {
                "name": "Normal Feature Task",
                "task": {
                    "client": "beta",
                    "importance": 3.0,
                    "effort_hours": 6.0,
                    "deadline": (now + timedelta(days=3)).isoformat(),
                    "created_at": (now - timedelta(hours=12)).isoformat(),
                    "recent_progress": 0.2
                }
            },
            {
                "name": "Low Priority Maintenance",
                "task": {
                    "client": "beta",
                    "importance": 2.0,
                    "effort_hours": 4.0,
                    "deadline": (now + timedelta(weeks=2)).isoformat(),
                    "created_at": (now - timedelta(days=1)).isoformat(),
                    "recent_progress": 0.0
                }
            }
        ]
        
        results = []
        for case in test_cases:
            traditional = compute_score(case["task"], sample_rules)
            enhanced_result = compute_score_with_details(case["task"], sample_rules)
            enhanced = enhanced_result["score"]
            
            results.append({
                "name": case["name"],
                "traditional": traditional,
                "enhanced": enhanced,
                "confidence": enhanced_result["confidence"],
                "urgency": enhanced_result["metadata"]["urgency_level"]
            })
        
        # Verify ordering consistency (high priority tasks should rank higher in both)
        traditional_scores = [r["traditional"] for r in results]
        enhanced_scores = [r["enhanced"] for r in results]
        
        # Critical task should score highest in both
        assert traditional_scores[0] == max(traditional_scores)
        assert enhanced_scores[0] == max(enhanced_scores)
        
        # Low priority should score lowest in both
        assert traditional_scores[2] == min(traditional_scores)


class TestProviderIntegrations:
    """Test provider adapter functionality"""
    
    @pytest.fixture
    def mock_clickup_adapter(self):
        """Mock ClickUp adapter for testing"""
        adapter = ClickUpAdapter(
            token="test-token",
            team_id="test-team",
            list_id="test-list",
            webhook_secret="test-secret"
        )
        return adapter
    
    @pytest.mark.asyncio
    async def test_clickup_provider_interface(self, mock_clickup_adapter):
        """Test ClickUp provider adapter interface"""
        # Test adapter initialization
        assert mock_clickup_adapter.name == "clickup"
        assert mock_clickup_adapter.token == "test-token"
        assert mock_clickup_adapter.team_id == "test-team"
        assert mock_clickup_adapter.list_id == "test-list"
        
        # Test webhook signature verification
        test_body = '{"event": "taskCreated", "task_id": "123"}'
        test_signature = mock_clickup_adapter._generate_signature(test_body)
        
        # Verify signature validation
        is_valid = mock_clickup_adapter.verify_webhook_signature(
            test_body, test_signature
        )
        assert is_valid
        
        # Test invalid signature
        is_invalid = mock_clickup_adapter.verify_webhook_signature(
            test_body, "invalid-signature"
        )
        assert not is_invalid
    
    @pytest.mark.asyncio
    async def test_provider_error_handling(self, mock_clickup_adapter):
        """Test provider error handling and retry logic"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Simulate API rate limiting
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.json.return_value = {"error": "Rate limited"}
            mock_get.return_value = mock_response
            
            # Should handle rate limiting gracefully
            with pytest.raises(Exception):  # Should raise after retries
                await mock_clickup_adapter._make_request("GET", "/test")
    
    def test_provider_priority_mapping(self, mock_clickup_adapter):
        """Test priority mapping between internal and provider formats"""
        # Test priority mapping
        internal_priorities = [1, 2, 3, 4, 5]
        for priority in internal_priorities:
            clickup_priority = mock_clickup_adapter._map_priority_to_clickup(priority)
            assert clickup_priority in [1, 2, 3, 4]  # ClickUp valid priorities
        
        # Test reverse mapping
        clickup_priorities = [1, 2, 3, 4]
        for cp_priority in clickup_priorities:
            internal_priority = mock_clickup_adapter._map_priority_from_clickup(cp_priority)
            assert 1 <= internal_priority <= 5


class TestOutboxPattern:
    """Test outbox pattern implementation for reliable delivery"""
    
    @pytest.fixture
    def outbox_manager(self):
        """Create outbox manager instance"""
        init()  # Ensure database is initialized
        return OutboxManager()
    
    def test_outbox_operation_creation(self, outbox_manager):
        """Test creating outbox operations"""
        # Create test operation
        operation = outbox_manager.create_operation(
            operation_type="webhook",
            endpoint="https://api.clickup.com/webhook",
            request_body={"task_id": "123", "event": "created"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert operation.operation_type == "webhook"
        assert operation.endpoint == "https://api.clickup.com/webhook"
        assert operation.status == "pending"
        assert operation.attempts == 0
        
        # Check idempotency key generation
        assert len(operation.idempotency_key) == 64  # SHA256 hex
    
    def test_outbox_processing_workflow(self, outbox_manager):
        """Test complete outbox processing workflow"""
        # Create multiple operations
        operations = []
        for i in range(3):
            op = outbox_manager.create_operation(
                operation_type="api_call",
                endpoint=f"https://api.test.com/task/{i}",
                request_body={"id": i, "status": "created"}
            )
            operations.append(op)
        
        # Get pending operations
        pending = outbox_manager.get_pending_operations(limit=5)
        assert len(pending) >= 3
        
        # Mock successful processing
        for op in pending[:2]:
            outbox_manager.mark_operation_completed(op.id)
        
        # Mock failed processing
        if len(pending) > 2:
            outbox_manager.mark_operation_failed(
                pending[2].id, 
                "Connection timeout",
                retry_after_seconds=300
            )
        
        # Verify status updates
        outbox_manager.get_pending_operations(limit=5)
        completed_count = len([op for op in pending if outbox_manager.get_operation_status(op.id) == "completed"])
        assert completed_count >= 2
    
    def test_idempotency_key_uniqueness(self, outbox_manager):
        """Test idempotency key generation and uniqueness"""
        # Same request should generate same key
        key1 = make_idempotency_key("webhook", "/api/task", {"id": 123, "action": "create"})
        key2 = make_idempotency_key("webhook", "/api/task", {"id": 123, "action": "create"})
        assert key1 == key2
        
        # Different requests should generate different keys
        key3 = make_idempotency_key("webhook", "/api/task", {"id": 124, "action": "create"})
        assert key1 != key3
        
        # Order independence
        key4 = make_idempotency_key("webhook", "/api/task", {"action": "create", "id": 123})
        assert key1 == key4


class TestRetryAndResilience:
    """Test retry mechanisms and system resilience"""
    
    def test_exponential_backoff_calculation(self):
        """Test exponential backoff timing"""
        # Test various retry attempts
        delays = [next_backoff(i) for i in range(1, 6)]
        
        # Should be increasing (generally)
        assert delays[0] < delays[-1]
        
        # Should respect cap
        big_delay = next_backoff(20)
        assert big_delay <= 60.0
        
        # Should have minimum
        assert all(delay >= 0.05 for delay in delays)
    
    def test_retry_function_success(self):
        """Test retry function with eventual success"""
        attempt_count = 0
        
        def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = retry(flaky_function, max_tries=5)
        assert result == "success"
        assert attempt_count == 3
    
    def test_retry_function_permanent_failure(self):
        """Test retry function with permanent failure"""
        def always_fails():
            raise ValueError("Permanent failure")
        
        with pytest.raises(ValueError):
            retry(always_fails, max_tries=3)
    
    @pytest.mark.asyncio
    async def test_async_retry_functionality(self):
        """Test async retry functionality"""
        attempt_count = 0
        
        async def async_flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ConnectionError("Async failure")
            return "async_success"
        
        result = await retry_async(async_flaky_function, max_tries=3)
        assert result == "async_success"
        assert attempt_count == 2


class TestSystemPerformance:
    """Test system performance and resource utilization"""
    
    def test_scoring_performance(self):
        """Test scoring algorithm performance"""
        now = datetime.now(timezone.utc)
        
        # Create test tasks
        tasks = []
        for i in range(100):
            task = {
                "client": f"client-{i % 3}",
                "importance": (i % 5) + 1,
                "effort_hours": (i % 8) + 1,
                "deadline": (now + timedelta(hours=i)).isoformat(),
                "created_at": (now - timedelta(hours=i % 24)).isoformat(),
                "recent_progress": (i % 10) / 10.0
            }
            tasks.append(task)
        
        rules = {
            "clients": {
                f"client-{i}": {"importance_bias": 1.0, "sla_hours": 72}
                for i in range(3)
            }
        }
        
        # Time traditional scoring
        start_time = time.time()
        traditional_scores = [compute_score(task, rules) for task in tasks]
        traditional_time = time.time() - start_time
        
        # Time enhanced scoring
        start_time = time.time()
        enhanced_scores = [compute_enhanced_score(task, rules) for task in tasks]
        enhanced_time = time.time() - start_time
        
        # Performance assertions
        assert traditional_time < 1.0  # Should be very fast
        assert enhanced_time < 5.0     # Should be reasonable
        assert len(traditional_scores) == 100
        assert len(enhanced_scores) == 100
        
        print(f"Traditional scoring: {traditional_time:.3f}s for 100 tasks")
        print(f"Enhanced scoring: {enhanced_time:.3f}s for 100 tasks")
    
    def test_database_performance(self):
        """Test database operation performance"""
        init()
        
        # Test bulk task operations
        now = datetime.now(timezone.utc)
        tasks = []
        
        for i in range(50):
            task = {
                "id": f"perf-test-{i}",
                "external_id": f"ext-{i}",
                "provider": "clickup",
                "title": f"Performance Test Task {i}",
                "client": f"client-{i % 5}",
                "status": "triaged",
                "score": 0.5,
                "created_at": now.isoformat()
            }
            tasks.append(task)
        
        # Time bulk insertion
        start_time = time.time()
        for task in tasks:
            save_task(task)
        insertion_time = time.time() - start_time
        
        # Time bulk retrieval
        start_time = time.time()
        open_tasks = fetch_open_tasks()
        retrieval_time = time.time() - start_time
        
        # Performance assertions
        assert insertion_time < 5.0  # Should complete in reasonable time
        assert retrieval_time < 1.0  # Retrieval should be fast
        assert len(open_tasks) >= 50  # Should retrieve our test tasks
        
        print(f"Database insertion: {insertion_time:.3f}s for 50 tasks")
        print(f"Database retrieval: {retrieval_time:.3f}s")


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases"""
    
    def test_malformed_task_data(self):
        """Test handling of malformed task data"""
        rules = {"clients": {"test": {"importance_bias": 1.0, "sla_hours": 72}}}
        
        # Missing required fields
        incomplete_task = {"client": "test"}
        score = compute_score(incomplete_task, rules)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        
        # Invalid date formats
        invalid_date_task = {
            "client": "test",
            "importance": 3.0,
            "deadline": "not-a-date",
            "created_at": "also-not-a-date"
        }
        score = compute_score(invalid_date_task, rules)
        assert isinstance(score, float)
    
    def test_extreme_values(self):
        """Test handling of extreme values"""
        rules = {"clients": {"test": {"importance_bias": 1.0, "sla_hours": 72}}}
        now = datetime.now(timezone.utc)
        
        # Extreme values
        extreme_task = {
            "client": "test",
            "importance": 1000.0,  # Very high
            "effort_hours": -5.0,  # Negative
            "deadline": (now - timedelta(days=365)).isoformat(),  # Far past
            "created_at": (now - timedelta(days=1000)).isoformat(),
            "recent_progress": 2.0  # > 1.0
        }
        
        score = compute_score(extreme_task, rules)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
    
    def test_missing_client_configuration(self):
        """Test handling of missing client configuration"""
        rules = {"clients": {}}  # No client configs
        
        task = {
            "client": "unknown-client",
            "importance": 3.0,
            "effort_hours": 4.0
        }
        
        # Should handle gracefully with defaults
        score = compute_score(task, rules)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


# Integration test runner
def run_integration_tests():
    """Run all integration tests and generate report"""
    print("🚀 Running Project Archangel Integration Test Suite")
    print("=" * 60)
    
    # Test categories
    test_classes = [
        TestDatabaseOperations,
        TestScoringAlgorithms,
        TestProviderIntegrations,
        TestOutboxPattern,
        TestRetryAndResilience,
        TestSystemPerformance,
        TestErrorHandlingAndEdgeCases
    ]
    
    results = {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    for test_class in test_classes:
        print(f"\n📋 Testing {test_class.__name__}")
        print("-" * 40)
        
        # Run tests in class
        test_instance = test_class()
        methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        for method_name in methods:
            results["total_tests"] += 1
            try:
                method = getattr(test_instance, method_name)
                method()
                print(f"✅ {method_name}")
                results["passed"] += 1
            except Exception as e:
                print(f"❌ {method_name}: {str(e)}")
                results["failed"] += 1
                results["errors"].append(f"{test_class.__name__}.{method_name}: {str(e)}")
    
    # Final report
    print("\n" + "=" * 60)
    print("📊 Integration Test Results")
    print("=" * 60)
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {(results['passed']/results['total_tests']*100):.1f}%")
    
    if results["errors"]:
        print("\n❌ Failed Tests:")
        for error in results["errors"]:
            print(f"  - {error}")
    
    return results


if __name__ == "__main__":
    run_integration_tests()