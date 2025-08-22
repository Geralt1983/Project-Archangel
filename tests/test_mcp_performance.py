"""
Performance and Reliability Tests for MCP Integration
Tests performance characteristics, scalability, and reliability under various conditions
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List, Dict, Any, Tuple
import concurrent.futures
import threading
import os
import psutil

from app.integrations.mcp_bridge import MCPBridge, MCPBridgeError, MCPServerUnavailableError
from app.services.enhanced_tasks import EnhancedTaskService
from app.providers.clickup import ClickUpAdapter
from app.utils.outbox import OutboxManager
from app.utils.retry import RateLimitError, ServerError
from tests.fixtures.mcp_responses import MCPResponseFixtures, MCPTestDataBuilder
from tests.fixtures.test_configs import get_test_config


@pytest.mark.performance
class TestMCPBridgePerformance:
    """Test MCP Bridge performance characteristics"""
    
    @pytest.fixture
    def performance_config(self):
        """Get performance-optimized configuration"""
        return get_test_config("performance")
    
    @pytest.fixture
    def mock_adapter_fast(self):
        """Create fast mock adapter for performance testing"""
        adapter = Mock(spec=ClickUpAdapter)
        
        def fast_operation(*args, **kwargs):
            # Simulate very fast operation
            time.sleep(0.001)  # 1ms
            return {"id": f"fast-{time.time_ns()}", "title": "Fast Response"}
        
        adapter.create_task.side_effect = fast_operation
        adapter.get_task.side_effect = fast_operation
        adapter.update_task.side_effect = fast_operation
        adapter.list_tasks.side_effect = lambda *args, **kwargs: [fast_operation()]
        
        return adapter
    
    @pytest.mark.asyncio
    async def test_single_request_latency(self, performance_config, mock_adapter_fast):
        """Test single request latency"""
        bridge = MCPBridge(config_path=performance_config, clickup_adapter=mock_adapter_fast)
        bridge._server_available = True
        bridge.client = AsyncMock()
        
        # Mock fast MCP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = MCPResponseFixtures.successful_task_creation()
        bridge.client.post.return_value = mock_response
        
        # Measure single request latency
        start_time = time.perf_counter()
        
        task_data = {"title": "Latency Test Task"}
        result = await bridge.create_task(task_data)
        
        end_time = time.perf_counter()
        latency = end_time - start_time
        
        # Assert latency is reasonable (under 100ms for mocked response)
        assert latency < 0.1, f"Single request latency too high: {latency*1000:.2f}ms"
        assert result["external_id"] is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_throughput(self, performance_config, mock_adapter_fast):
        """Test throughput with concurrent requests"""
        bridge = MCPBridge(config_path=performance_config, clickup_adapter=mock_adapter_fast)
        bridge._server_available = True
        bridge.client = AsyncMock()
        
        # Mock MCP responses
        response_count = 0
        def mock_post(*args, **kwargs):
            nonlocal response_count
            response_count += 1
            
            mock_response = Mock()
            mock_response.status_code = 200
            
            # Create unique response for each request
            response_data = MCPResponseFixtures.successful_task_creation()
            response_data["result"]["content"]["id"] = f"concurrent-{response_count}"
            mock_response.json.return_value = response_data
            
            # Small async delay to simulate network
            return asyncio.sleep(0.005, result=mock_response)
        
        bridge.client.post.side_effect = mock_post
        
        # Test concurrent requests
        concurrent_count = 50
        tasks = []
        
        start_time = time.perf_counter()
        
        for i in range(concurrent_count):
            task_data = {"title": f"Concurrent Task {i}"}
            task_coro = bridge.create_task(task_data)
            tasks.append(task_coro)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Verify all requests succeeded
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == concurrent_count
        
        # Calculate throughput
        throughput = concurrent_count / total_time
        
        # Assert reasonable throughput (should handle at least 10 requests/second with mocking)
        assert throughput >= 10, f"Throughput too low: {throughput:.2f} req/sec"
        
        # Verify unique responses
        response_ids = {result["external_id"] for result in successful_results}
        assert len(response_ids) == concurrent_count, "Responses should be unique"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, performance_config, mock_adapter_fast):
        """Test memory usage during sustained load"""
        bridge = MCPBridge(config_path=performance_config, clickup_adapter=mock_adapter_fast)
        bridge._server_available = True
        bridge.client = AsyncMock()
        
        # Mock lightweight responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"content": {"id": "memory-test"}}}
        bridge.client.post.return_value = mock_response
        
        # Measure initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform sustained operations
        iterations = 1000
        batch_size = 50
        
        for batch in range(iterations // batch_size):
            tasks = []
            for i in range(batch_size):
                task_data = {"title": f"Memory Test {batch}_{i}"}
                tasks.append(bridge.create_task(task_data))
            
            await asyncio.gather(*tasks)
            
            # Force garbage collection occasionally
            if batch % 5 == 0:
                import gc
                gc.collect()
        
        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for this test)
        assert memory_increase < 50, f"Memory usage increased too much: {memory_increase:.2f}MB"
    
    @pytest.mark.asyncio
    async def test_connection_pool_efficiency(self, performance_config):
        """Test HTTP connection pool efficiency"""
        adapter = Mock(spec=ClickUpAdapter)
        bridge = MCPBridge(config_path=performance_config, clickup_adapter=adapter)
        
        # Track connection creation
        connection_count = 0
        original_client_init = None
        
        def track_client_creation(*args, **kwargs):
            nonlocal connection_count
            connection_count += 1
            client = AsyncMock()
            
            # Mock successful responses
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": {"content": {"id": "pool-test"}}}
            client.post.return_value = mock_response
            client.get.return_value = mock_response
            
            return client
        
        with patch('httpx.AsyncClient', side_effect=track_client_creation):
            await bridge.connect()
            
            # Perform multiple operations
            for _ in range(10):
                await bridge._health_check()
                await bridge.create_task({"title": "Pool Test"})
            
            await bridge.disconnect()
        
        # Should only create one client connection
        assert connection_count == 1, f"Too many connections created: {connection_count}"


@pytest.mark.performance
class TestEnhancedTaskServicePerformance:
    """Test Enhanced Task Service performance"""
    
    @pytest.fixture
    def performance_service(self):
        """Create service optimized for performance testing"""
        adapter = Mock(spec=ClickUpAdapter)
        
        # Fast adapter responses
        def fast_response(data=None):
            return {"id": f"perf-{time.time_ns()}", "title": "Fast Response"}
        
        adapter.create_task.side_effect = lambda x: fast_response(x)
        adapter.get_task.side_effect = lambda x: fast_response()
        adapter.update_task.side_effect = lambda x, y: fast_response()
        adapter.list_tasks.side_effect = lambda *args: [fast_response() for _ in range(10)]
        
        # Mock outbox for performance
        outbox = Mock(spec=OutboxManager)
        outbox.enqueue_operation.return_value = None
        
        service = EnhancedTaskService(adapter, outbox)
        
        # Mock fast MCP bridge
        mock_bridge = AsyncMock(spec=MCPBridge)
        mock_bridge.create_task.side_effect = lambda x: asyncio.sleep(0.001, result={
            "external_id": f"mcp-{time.time_ns()}", "title": "MCP Fast"
        })
        mock_bridge.get_task.side_effect = lambda x: asyncio.sleep(0.001, result={
            "external_id": x, "title": "MCP Fast"
        })
        mock_bridge.update_task.side_effect = lambda x, y: asyncio.sleep(0.001, result={
            "external_id": x, "title": "MCP Updated"
        })
        mock_bridge.list_tasks.side_effect = lambda x=None: asyncio.sleep(0.001, result=[
            {"external_id": f"mcp-list-{i}", "title": f"Task {i}"} for i in range(10)
        ])
        
        service.mcp_bridge = mock_bridge
        
        return service
    
    @pytest.mark.asyncio
    async def test_bulk_operations_scaling(self, performance_service):
        """Test bulk operations scaling with task count"""
        batch_sizes = [10, 50, 100, 200]
        timings = []
        
        for batch_size in batch_sizes:
            updates = [
                {"task_id": f"bulk-{i}", "data": {"title": f"Bulk Update {i}"}}
                for i in range(batch_size)
            ]
            
            start_time = time.perf_counter()
            
            results = await performance_service.bulk_update_tasks(updates, use_outbox=False)
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            timings.append((batch_size, duration))
            
            # Verify all succeeded
            successful = [r for r in results if r.get("success")]
            assert len(successful) == batch_size
        
        # Verify scaling is reasonable (should be roughly linear)
        # Calculate operations per second for each batch size
        ops_per_second = [(batch / duration) for batch, duration in timings]
        
        # Throughput should remain relatively stable as batch size increases
        min_ops = min(ops_per_second)
        max_ops = max(ops_per_second)
        
        # Variance should be reasonable (not more than 3x difference)
        assert max_ops / min_ops < 3.0, f"Performance scaling poor: {ops_per_second}"
    
    @pytest.mark.asyncio
    async def test_concurrent_service_instances(self):
        """Test performance with multiple service instances"""
        # Create multiple service instances
        services = []
        
        for i in range(5):
            adapter = Mock(spec=ClickUpAdapter)
            adapter.create_task.return_value = {"id": f"service-{i}", "title": "Multi Service"}
            
            outbox = Mock(spec=OutboxManager)
            service = EnhancedTaskService(adapter, outbox)
            services.append(service)
        
        # Run operations concurrently across services
        tasks = []
        start_time = time.perf_counter()
        
        for i, service in enumerate(services):
            for j in range(10):
                task_data = {"title": f"Service {i} Task {j}"}
                tasks.append(service.create_task(task_data, use_outbox=False))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Verify all operations succeeded
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) == 50  # 5 services * 10 tasks each
        
        # Performance should be reasonable
        throughput = len(successful) / duration
        assert throughput >= 20, f"Multi-service throughput too low: {throughput:.2f}"
    
    @pytest.mark.asyncio
    async def test_outbox_performance_impact(self, performance_service):
        """Test performance impact of outbox integration"""
        task_data = {"title": "Outbox Performance Test"}
        iterations = 100
        
        # Test without outbox
        start_time = time.perf_counter()
        
        for _ in range(iterations):
            await performance_service.create_task(task_data, use_outbox=False)
        
        no_outbox_time = time.perf_counter() - start_time
        
        # Test with outbox
        start_time = time.perf_counter()
        
        for _ in range(iterations):
            await performance_service.create_task(task_data, use_outbox=True)
        
        with_outbox_time = time.perf_counter() - start_time
        
        # Outbox overhead should be minimal (less than 50% increase)
        overhead_ratio = with_outbox_time / no_outbox_time
        assert overhead_ratio < 1.5, f"Outbox overhead too high: {overhead_ratio:.2f}x"


@pytest.mark.performance
class TestMCPIntegrationReliability:
    """Test MCP integration reliability and fault tolerance"""
    
    @pytest.fixture
    def unreliable_bridge(self, tmp_path):
        """Create bridge with simulated unreliable server"""
        config_data = {
            "server": {"host": "localhost", "port": 3231, "endpoint": "/mcp", "max_retries": 3},
            "features": {"enabled_tools": ["create_task"], "disabled_tools": []},
            "integration": {"bridge_enabled": True, "fallback_to_adapter": True}
        }
        
        config_path = tmp_path / "unreliable_config.yml"
        with open(config_path, 'w') as f:
            import yaml
            yaml.safe_dump(config_data, f)
        
        adapter = Mock(spec=ClickUpAdapter)
        adapter.create_task.return_value = {"id": "fallback-success", "title": "Fallback"}
        
        bridge = MCPBridge(config_path=str(config_path), clickup_adapter=adapter)
        bridge._server_available = True
        bridge.client = AsyncMock()
        
        return bridge
    
    @pytest.mark.asyncio
    async def test_intermittent_failures_recovery(self, unreliable_bridge):
        """Test recovery from intermittent server failures"""
        call_count = 0
        success_pattern = [False, False, True, True, False, True]  # Mixed success/failure
        
        def unreliable_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            # Simulate intermittent failures
            should_succeed = success_pattern[(call_count - 1) % len(success_pattern)]
            
            if should_succeed:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = MCPResponseFixtures.successful_task_creation()
                return mock_response
            else:
                raise ServerError(500, "Simulated server error")
        
        unreliable_bridge.client.post.side_effect = unreliable_post
        
        # Attempt multiple operations
        operations = 20
        results = []
        errors = []
        
        for i in range(operations):
            try:
                task_data = {"title": f"Reliability Test {i}"}
                result = await unreliable_bridge.create_task(task_data)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Should have some successes and some errors based on pattern
        assert len(results) > 0, "Should have some successful operations"
        assert len(errors) > 0, "Should have some failed operations (for this test)"
        
        # Success rate should match the pattern (50% in this case)
        success_rate = len(results) / operations
        expected_rate = sum(success_pattern) / len(success_pattern)
        
        # Allow some variance due to retry logic
        assert abs(success_rate - expected_rate) < 0.3, f"Unexpected success rate: {success_rate}"
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, unreliable_bridge):
        """Test handling of rate limiting with backoff"""
        rate_limit_count = 0
        
        def rate_limited_post(*args, **kwargs):
            nonlocal rate_limit_count
            rate_limit_count += 1
            
            # First few requests get rate limited
            if rate_limit_count <= 3:
                mock_response = Mock()
                mock_response.status_code = 429
                mock_response.headers = {"retry-after": "1"}
                return mock_response
            
            # Later requests succeed
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = MCPResponseFixtures.successful_task_creation()
            return mock_response
        
        unreliable_bridge.client.post.side_effect = rate_limited_post
        
        # This test focuses on the rate limiting response, not retry logic
        # (since retry logic is handled by decorators)
        start_time = time.perf_counter()
        
        try:
            task_data = {"title": "Rate Limit Test"}
            result = await unreliable_bridge.create_task(task_data)
            
            # Should get rate limited initially
            assert rate_limit_count >= 1
            
        except RateLimitError:
            # Rate limiting was properly detected
            assert rate_limit_count >= 1
        
        end_time = time.perf_counter()
        
        # Should not take too long (no actual backoff in this test)
        assert end_time - start_time < 1.0
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_under_load(self, unreliable_bridge):
        """Test graceful degradation when server is overloaded"""
        response_times = []
        success_count = 0
        error_count = 0
        
        def overloaded_post(*args, **kwargs):
            nonlocal success_count, error_count
            
            # Simulate increasing response times under load
            base_delay = len(response_times) * 0.001  # Increasing delay
            
            if base_delay > 0.05:  # 50ms threshold
                # Start failing requests when overloaded
                error_count += 1
                raise ServerError(503, "Service Unavailable")
            
            # Successful response with delay
            success_count += 1
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = MCPResponseFixtures.successful_task_creation()
            
            # Record simulated response time
            response_times.append(base_delay)
            
            return mock_response
        
        unreliable_bridge.client.post.side_effect = overloaded_post
        
        # Generate load
        tasks = []
        for i in range(100):
            task_data = {"title": f"Load Test {i}"}
            tasks.append(unreliable_bridge.create_task(task_data))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        # Should have some successful operations before degradation
        assert len(successful_results) > 0, "Should have some successful operations"
        
        # Should start failing as load increases
        assert len(failed_results) > 0, "Should have some failures under load"
        
        # Success rate should degrade gracefully
        success_rate = len(successful_results) / len(results)
        assert 0.1 <= success_rate <= 0.9, f"Degradation pattern unexpected: {success_rate}"
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_on_errors(self, unreliable_bridge):
        """Test proper resource cleanup when errors occur"""
        initial_open_files = len(psutil.Process().open_files())
        
        # Mock client that fails and should clean up properly
        failing_client = AsyncMock()
        failing_client.post.side_effect = Exception("Connection failed")
        failing_client.aclose = AsyncMock()
        
        unreliable_bridge.client = failing_client
        
        # Attempt operations that will fail
        for i in range(10):
            try:
                await unreliable_bridge.create_task({"title": f"Cleanup Test {i}"})
            except:
                pass  # Expected to fail
        
        # Explicitly disconnect to trigger cleanup
        await unreliable_bridge.disconnect()
        
        # Check that resources were cleaned up
        final_open_files = len(psutil.Process().open_files())
        
        # Should not have leaked file handles
        assert final_open_files <= initial_open_files + 2, "Possible resource leak detected"
        
        # Verify cleanup method was called
        failing_client.aclose.assert_called()


@pytest.mark.performance
class TestMCPIntegrationStressTest:
    """Stress testing for MCP integration"""
    
    @pytest.mark.asyncio
    async def test_sustained_high_throughput(self):
        """Test sustained high throughput over time"""
        # Create lightweight service for stress testing
        adapter = Mock(spec=ClickUpAdapter)
        adapter.create_task.return_value = {"id": "stress-test", "title": "Stress"}
        
        outbox = Mock(spec=OutboxManager)
        service = EnhancedTaskService(adapter, outbox)
        
        # Mock fast MCP bridge
        mock_bridge = AsyncMock()
        mock_bridge.create_task.return_value = {"external_id": "stress-mcp", "title": "Stress MCP"}
        service.mcp_bridge = mock_bridge
        
        # Stress test parameters
        duration_seconds = 10
        target_rps = 50  # requests per second
        
        tasks_completed = 0
        start_time = time.perf_counter()
        
        # Generate sustained load
        while time.perf_counter() - start_time < duration_seconds:
            batch_tasks = []
            
            # Create batch of concurrent requests
            for _ in range(10):
                task_data = {"title": f"Stress Test {tasks_completed}"}
                batch_tasks.append(service.create_task(task_data, use_outbox=False))
                tasks_completed += 1
            
            await asyncio.gather(*batch_tasks)
            
            # Small delay to control rate
            await asyncio.sleep(0.1)
        
        end_time = time.perf_counter()
        actual_duration = end_time - start_time
        actual_rps = tasks_completed / actual_duration
        
        # Verify sustained throughput
        assert actual_rps >= target_rps * 0.8, f"Throughput below target: {actual_rps:.2f} < {target_rps}"
        assert tasks_completed >= duration_seconds * target_rps * 0.8
    
    @pytest.mark.asyncio
    async def test_memory_stability_over_time(self):
        """Test memory stability during extended operation"""
        adapter = Mock(spec=ClickUpAdapter)
        outbox = Mock(spec=OutboxManager)
        service = EnhancedTaskService(adapter, outbox)
        
        # Track memory usage over time
        process = psutil.Process()
        memory_samples = []
        
        # Run operations in batches
        for batch in range(10):
            # Perform batch of operations
            tasks = []
            for i in range(50):
                task_data = {"title": f"Memory Test {batch}_{i}"}
                tasks.append(service.create_task(task_data, use_outbox=False))
            
            await asyncio.gather(*tasks)
            
            # Sample memory usage
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_samples.append(memory_mb)
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Brief pause between batches
            await asyncio.sleep(0.1)
        
        # Analyze memory trend
        initial_memory = memory_samples[0]
        final_memory = memory_samples[-1]
        max_memory = max(memory_samples)
        
        # Memory growth should be bounded
        memory_growth = final_memory - initial_memory
        peak_growth = max_memory - initial_memory
        
        assert memory_growth < 20, f"Memory growth too high: {memory_growth:.2f}MB"
        assert peak_growth < 30, f"Peak memory usage too high: {peak_growth:.2f}MB"
    
    @pytest.mark.asyncio
    async def test_error_rate_under_stress(self):
        """Test error rate remains acceptable under stress"""
        # Create service with mixed success/failure
        adapter = Mock(spec=ClickUpAdapter)
        
        call_count = 0
        def sometimes_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            # 10% failure rate
            if call_count % 10 == 0:
                raise Exception("Simulated failure")
            
            return {"id": f"stress-{call_count}", "title": "Success"}
        
        adapter.create_task.side_effect = sometimes_fail
        
        outbox = Mock(spec=OutboxManager)
        service = EnhancedTaskService(adapter, outbox)
        
        # Run stress test
        total_operations = 500
        tasks = []
        
        for i in range(total_operations):
            task_data = {"title": f"Error Rate Test {i}"}
            tasks.append(service.create_task(task_data, use_outbox=False))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze error rate
        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]
        
        error_rate = len(failed) / total_operations
        success_rate = len(successful) / total_operations
        
        # Error rate should match expectation (10% ± 2%)
        assert 0.08 <= error_rate <= 0.12, f"Unexpected error rate: {error_rate:.3f}"
        assert success_rate >= 0.88, f"Success rate too low: {success_rate:.3f}"


if __name__ == "__main__":
    # Run performance tests independently
    pytest.main([__file__, "-v", "-m", "performance"])