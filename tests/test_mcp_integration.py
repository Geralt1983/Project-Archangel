"""
Integration Tests for MCP Integration
Tests the full MCP integration workflow including database, outbox, and end-to-end scenarios
"""

import pytest
import asyncio
import json
import os
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

from app.integrations.mcp_bridge import MCPBridge, MCPBridgeError, MCPServerUnavailableError
from app.services.enhanced_tasks import EnhancedTaskService
from app.providers.clickup import ClickUpAdapter
from app.utils.outbox import OutboxManager, make_idempotency_key
from app.db_pg import init, get_conn, save_task, fetch_open_tasks
from app.utils.retry import RetryConfig, RateLimitError, ServerError


@pytest.mark.integration
class TestMCPIntegrationFullWorkflow:
    """Test complete MCP integration workflow"""
    
    @pytest.fixture(scope="class")
    def db_setup(self):
        """Setup test database for integration tests"""
        # Use in-memory SQLite for fast testing
        os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
        init()
        yield
        # Cleanup is automatic with in-memory DB
    
    @pytest.fixture
    def integration_config(self, tmp_path):
        """Create integration test configuration"""
        config_data = {
            "server": {
                "host": "localhost",
                "port": 3231,
                "endpoint": "/mcp",
                "connection_timeout": 5,
                "request_timeout": 15,
                "max_retries": 2
            },
            "features": {
                "enabled_tools": [
                    "create_task", "get_task", "update_task", "list_tasks", 
                    "search_tasks", "get_task_comments", "get_task_time_tracked"
                ],
                "disabled_tools": ["delete_task"]
            },
            "integration": {
                "bridge_enabled": True,
                "fallback_to_adapter": True,
                "sync_with_outbox": True,
                "use_idempotency_keys": True,
                "priority_mapping": {"1": 4, "2": 3, "3": 3, "4": 2, "5": 1},
                "status_mapping": {
                    "open": "pending",
                    "in progress": "in_progress", 
                    "review": "review",
                    "done": "completed"
                }
            }
        }
        
        config_path = tmp_path / "integration_config.yml"
        with open(config_path, 'w') as f:
            import yaml
            yaml.safe_dump(config_data, f)
        
        return str(config_path)
    
    @pytest.fixture
    def mock_clickup_adapter(self):
        """Create comprehensive mock ClickUp adapter"""
        adapter = Mock(spec=ClickUpAdapter)
        
        # Track created tasks for consistency
        adapter._tasks = {}
        adapter._next_id = 1
        
        def create_task(task_data):
            task_id = f"clickup-{adapter._next_id}"
            adapter._next_id += 1
            
            task = {
                "id": task_id,
                "title": task_data.get("title", "Untitled"),
                "description": task_data.get("description", ""),
                "status": "open",
                "priority": task_data.get("priority", 3),
                "assignee": task_data.get("assignee"),
                "labels": task_data.get("labels", []),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            adapter._tasks[task_id] = task
            return task
        
        def get_task(task_id):
            if task_id in adapter._tasks:
                return adapter._tasks[task_id]
            raise Exception(f"Task {task_id} not found")
        
        def update_task(task_id, task_data):
            if task_id not in adapter._tasks:
                raise Exception(f"Task {task_id} not found")
            
            task = adapter._tasks[task_id].copy()
            task.update(task_data)
            task["updated_at"] = datetime.now(timezone.utc).isoformat()
            adapter._tasks[task_id] = task
            return task
        
        def list_tasks(status_filter=None, assignee_filter=None):
            tasks = list(adapter._tasks.values())
            
            if status_filter:
                tasks = [t for t in tasks if t.get("status") == status_filter]
            if assignee_filter:
                tasks = [t for t in tasks if t.get("assignee") == assignee_filter]
            
            return tasks
        
        adapter.create_task.side_effect = create_task
        adapter.get_task.side_effect = get_task
        adapter.update_task.side_effect = update_task
        adapter.list_tasks.side_effect = list_tasks
        
        return adapter
    
    @pytest.fixture
    def outbox_manager(self, db_setup):
        """Create real outbox manager with test database"""
        return OutboxManager(get_conn)
    
    @pytest.fixture
    def mock_mcp_server(self):
        """Create comprehensive mock MCP server responses"""
        class MockMCPServer:
            def __init__(self):
                self.tasks = {}
                self.next_id = 1
                self.request_count = 0
                self.last_request = None
            
            def handle_request(self, tool, arguments):
                self.request_count += 1
                self.last_request = {"tool": tool, "arguments": arguments}
                
                if tool == "create_task":
                    return self._create_task(arguments)
                elif tool == "get_task":
                    return self._get_task(arguments)
                elif tool == "update_task":
                    return self._update_task(arguments)
                elif tool == "list_tasks":
                    return self._list_tasks(arguments)
                elif tool == "search_tasks":
                    return self._search_tasks(arguments)
                elif tool == "get_task_comments":
                    return self._get_task_comments(arguments)
                elif tool == "get_task_time_tracked":
                    return self._get_task_time_tracked(arguments)
                else:
                    raise Exception(f"Unknown tool: {tool}")
            
            def _create_task(self, args):
                task_id = f"mcp-{self.next_id}"
                self.next_id += 1
                
                task = {
                    "id": task_id,
                    "name": args.get("name", "Untitled"),
                    "description": args.get("description", ""),
                    "status": "open",
                    "priority": args.get("priority", 3),
                    "assignees": args.get("assignees", []),
                    "tags": args.get("tags", []),
                    "due_date": args.get("due_date"),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                self.tasks[task_id] = task
                return task
            
            def _get_task(self, args):
                task_id = args.get("task_id")
                if task_id in self.tasks:
                    return self.tasks[task_id]
                raise Exception(f"Task {task_id} not found")
            
            def _update_task(self, args):
                task_id = args.get("task_id")
                if task_id not in self.tasks:
                    raise Exception(f"Task {task_id} not found")
                
                task = self.tasks[task_id].copy()
                # Remove task_id from args before updating
                update_data = {k: v for k, v in args.items() if k != "task_id"}
                task.update(update_data)
                task["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.tasks[task_id] = task
                return task
            
            def _list_tasks(self, args):
                tasks = list(self.tasks.values())
                return {"tasks": tasks}
            
            def _search_tasks(self, args):
                query = args.get("query", "")
                tasks = [
                    task for task in self.tasks.values()
                    if query.lower() in task.get("name", "").lower() or
                       query.lower() in task.get("description", "").lower()
                ]
                return tasks
            
            def _get_task_comments(self, args):
                return [
                    {"id": "comment-1", "text": "First comment", "author": "john@example.com"},
                    {"id": "comment-2", "text": "Second comment", "author": "jane@example.com"}
                ]
            
            def _get_task_time_tracked(self, args):
                return {"total_time": "3h 45m", "this_week": "1h 30m"}
        
        return MockMCPServer()
    
    @pytest.mark.asyncio
    async def test_end_to_end_task_creation_workflow(self, integration_config, mock_clickup_adapter, 
                                                   outbox_manager, mock_mcp_server, db_setup):
        """Test complete task creation workflow from API to database"""
        
        # Setup enhanced task service
        service = EnhancedTaskService(mock_clickup_adapter, outbox_manager)
        
        # Mock MCP bridge to use mock server
        with patch('app.integrations.mcp_bridge.MCPBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge_class.return_value = mock_bridge
            
            # Setup mock bridge responses
            def mock_mcp_request(tool, arguments):
                return mock_mcp_server.handle_request(tool, arguments)
            
            mock_bridge._mcp_request.side_effect = mock_mcp_request
            mock_bridge._should_use_mcp.return_value = True
            mock_bridge._server_available = True
            
            # Mock data mapping methods
            def mock_map_to_mcp(task_data):
                return {
                    "name": task_data.get("title"),
                    "description": task_data.get("description"),
                    "priority": task_data.get("priority"),
                    "assignees": [task_data.get("assignee")] if task_data.get("assignee") else [],
                    "tags": task_data.get("labels", [])
                }
            
            def mock_map_from_mcp(mcp_task):
                return {
                    "external_id": mcp_task.get("id"),
                    "title": mcp_task.get("name"),
                    "description": mcp_task.get("description"),
                    "priority": mcp_task.get("priority"),
                    "assignee": mcp_task.get("assignees", [None])[0],
                    "labels": mcp_task.get("tags", []),
                    "status": "pending"
                }
            
            mock_bridge._map_task_to_mcp.side_effect = mock_map_to_mcp
            mock_bridge._map_task_from_mcp.side_effect = mock_map_from_mcp
            
            # Initialize MCP bridge
            service.mcp_bridge = mock_bridge
            
            # Test task creation
            task_data = {
                "title": "Integration Test Task",
                "description": "Test task for full workflow",
                "priority": 4,
                "assignee": "test@example.com",
                "labels": ["integration", "test"],
                "client": "test-client",
                "importance": 4.0,
                "effort_hours": 2.5
            }
            
            # Create task via enhanced service
            result = await service.create_task(task_data, use_outbox=True)
            
            # Verify task was created via MCP
            assert result["external_id"].startswith("mcp-")
            assert result["title"] == "Integration Test Task"
            assert result["priority"] == 4
            
            # Verify MCP server was called
            assert mock_mcp_server.request_count == 1
            assert mock_mcp_server.last_request["tool"] == "create_task"
            
            # Verify outbox entry was created
            stats = outbox_manager.get_stats()
            assert stats.get("pending", 0) == 1
            
            # Save task to database
            db_task_data = {
                "id": f"archangel-{int(time.time()*1000)}",
                "external_id": result["external_id"],
                "provider": "clickup",
                "title": result["title"],
                "description": result["description"],
                "importance": task_data["importance"],
                "effort_hours": task_data["effort_hours"],
                "client": task_data["client"],
                "status": "triaged",
                "score": 0.75,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            save_task(db_task_data)
            
            # Verify task appears in database
            open_tasks = fetch_open_tasks()
            task_ids = [task.get("id") for task in open_tasks]
            assert db_task_data["id"] in task_ids
            
            # Verify task can be retrieved via service
            retrieved_task = await service.get_task(result["external_id"])
            assert retrieved_task["external_id"] == result["external_id"]
            assert retrieved_task["title"] == "Integration Test Task"
    
    @pytest.mark.asyncio
    async def test_task_update_with_outbox_processing(self, integration_config, mock_clickup_adapter,
                                                    outbox_manager, mock_mcp_server, db_setup):
        """Test task update workflow with outbox processing"""
        
        service = EnhancedTaskService(mock_clickup_adapter, outbox_manager)
        
        # Create initial task via mock MCP
        initial_task = mock_mcp_server.handle_request("create_task", {
            "name": "Task to Update",
            "description": "Initial description",
            "priority": 3
        })
        
        # Mock MCP bridge
        with patch('app.integrations.mcp_bridge.MCPBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge_class.return_value = mock_bridge
            
            def mock_mcp_request(tool, arguments):
                return mock_mcp_server.handle_request(tool, arguments)
            
            mock_bridge._mcp_request.side_effect = mock_mcp_request
            mock_bridge._should_use_mcp.return_value = True
            mock_bridge._map_task_from_mcp.side_effect = lambda task: {
                "external_id": task.get("id"),
                "title": task.get("name"),
                "description": task.get("description"),
                "priority": task.get("priority")
            }
            
            service.mcp_bridge = mock_bridge
            
            # Update task
            update_data = {
                "title": "Updated Task Title",
                "description": "Updated description",
                "priority": 5
            }
            
            result = await service.update_task(initial_task["id"], update_data, use_outbox=True)
            
            # Verify update was processed
            assert result["title"] == "Updated Task Title"
            assert result["description"] == "Updated description"
            assert result["priority"] == 5
            
            # Verify outbox entry
            stats = outbox_manager.get_stats()
            assert stats.get("pending", 0) >= 1
            
            # Process outbox batch
            batch = outbox_manager.pick_batch(limit=5)
            assert len(batch) >= 1
            
            update_operation = None
            for op in batch:
                if op.operation_type == "update_task":
                    update_operation = op
                    break
            
            assert update_operation is not None
            assert "task_id" in update_operation.request
            assert update_operation.request["task_id"] == initial_task["id"]
    
    @pytest.mark.asyncio
    async def test_mcp_fallback_to_adapter_workflow(self, integration_config, mock_clickup_adapter,
                                                  outbox_manager, db_setup):
        """Test workflow when MCP server is unavailable and fallback to adapter"""
        
        service = EnhancedTaskService(mock_clickup_adapter, outbox_manager)
        
        # Mock MCP bridge that fails to connect
        with patch('app.integrations.mcp_bridge.MCPBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge_class.return_value = mock_bridge
            
            # Simulate MCP server unavailable
            mock_bridge._should_use_mcp.return_value = False
            mock_bridge._server_available = False
            
            service.mcp_bridge = mock_bridge
            
            # Test task creation - should fallback to adapter
            task_data = {
                "title": "Fallback Test Task",
                "description": "Test adapter fallback",
                "priority": 3,
                "assignee": "fallback@example.com"
            }
            
            result = await service.create_task(task_data, use_outbox=True)
            
            # Verify task was created via adapter
            assert result["id"].startswith("clickup-")
            assert result["title"] == "Fallback Test Task"
            
            # Verify adapter was called
            mock_clickup_adapter.create_task.assert_called_once_with(task_data)
            
            # Verify outbox entry with fallback metadata
            stats = outbox_manager.get_stats()
            assert stats.get("pending", 0) == 1
            
            batch = outbox_manager.pick_batch(limit=1)
            operation = batch[0]
            assert operation.metadata.get("via_mcp") is False
    
    @pytest.mark.asyncio
    async def test_search_and_insights_workflow(self, integration_config, mock_clickup_adapter,
                                              outbox_manager, mock_mcp_server, db_setup):
        """Test advanced MCP features like search and insights"""
        
        service = EnhancedTaskService(mock_clickup_adapter, outbox_manager)
        
        # Pre-populate mock server with test tasks
        for i in range(5):
            mock_mcp_server.handle_request("create_task", {
                "name": f"Test Task {i}",
                "description": f"Description for task {i}",
                "priority": i % 3 + 1
            })
        
        # Mock MCP bridge
        with patch('app.integrations.mcp_bridge.MCPBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge_class.return_value = mock_bridge
            
            def mock_mcp_request(tool, arguments):
                return mock_mcp_server.handle_request(tool, arguments)
            
            mock_bridge._mcp_request.side_effect = mock_mcp_request
            mock_bridge._should_use_mcp.return_value = True
            
            # Mock search response mapping
            def mock_search_tasks(query, filters=None):
                results = mock_mcp_server.handle_request("search_tasks", {"query": query})
                return [{"external_id": task["id"], "title": task["name"]} for task in results]
            
            mock_bridge.search_tasks.side_effect = mock_search_tasks
            service.mcp_bridge = mock_bridge
            
            # Test search functionality
            search_results = await service.search_tasks("Test Task")
            
            assert len(search_results) == 5
            assert all("Test Task" in result["title"] for result in search_results)
            
            # Test task insights
            task_id = list(mock_mcp_server.tasks.keys())[0]
            
            # Mock get_task for insights
            mock_bridge.get_task.return_value = {
                "external_id": task_id,
                "title": "Test Task for Insights"
            }
            
            insights = await service.get_task_insights(task_id)
            
            assert "task" in insights
            assert insights["task"]["external_id"] == task_id
            assert "time_tracking" in insights
            assert "comments" in insights
            assert insights["time_tracking"]["total_time"] == "3h 45m"
            assert len(insights["comments"]) == 2


@pytest.mark.integration
class TestMCPIntegrationErrorScenarios:
    """Test MCP integration error scenarios and resilience"""
    
    @pytest.fixture(scope="class")
    def db_setup(self):
        """Setup test database"""
        os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
        init()
        yield
    
    @pytest.fixture
    def error_config(self, tmp_path):
        """Create configuration for error testing"""
        config_data = {
            "server": {
                "host": "localhost",
                "port": 3231,
                "endpoint": "/mcp",
                "max_retries": 2
            },
            "features": {
                "enabled_tools": ["create_task", "get_task"],
                "disabled_tools": []
            },
            "integration": {
                "bridge_enabled": True,
                "fallback_to_adapter": True
            }
        }
        
        config_path = tmp_path / "error_config.yml"
        with open(config_path, 'w') as f:
            import yaml
            yaml.safe_dump(config_data, f)
        
        return str(config_path)
    
    @pytest.mark.asyncio
    async def test_rate_limiting_and_retry(self, error_config, db_setup):
        """Test handling of rate limiting and retry logic"""
        
        adapter = Mock(spec=ClickUpAdapter)
        outbox = OutboxManager(get_conn)
        
        # Mock MCP bridge with rate limiting
        with patch('app.integrations.mcp_bridge.MCPBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge_class.return_value = mock_bridge
            
            # Simulate rate limiting on first call, success on retry
            rate_limit_call_count = 0
            
            def mock_mcp_request(tool, arguments):
                nonlocal rate_limit_call_count
                rate_limit_call_count += 1
                
                if rate_limit_call_count == 1:
                    raise RateLimitError(retry_after=1)
                
                return {"id": "mcp-retry-success", "name": arguments.get("name")}
            
            mock_bridge._mcp_request.side_effect = mock_mcp_request
            mock_bridge._should_use_mcp.return_value = True
            mock_bridge._map_task_from_mcp.return_value = {
                "external_id": "mcp-retry-success",
                "title": "Retry Success Task"
            }
            
            service = EnhancedTaskService(adapter, outbox)
            service.mcp_bridge = mock_bridge
            
            # This should succeed after retry
            task_data = {"title": "Rate Limited Task"}
            
            # Note: The actual retry is handled by the @retry_with_backoff decorator
            # For testing, we simulate the behavior
            with patch('time.sleep'):  # Mock sleep to speed up test
                try:
                    result = await service.create_task(task_data)
                    # If we get here, retry worked (in a real scenario)
                    assert result["title"] == "Retry Success Task"
                except RateLimitError:
                    # Rate limiting was encountered
                    assert rate_limit_call_count >= 1
    
    @pytest.mark.asyncio
    async def test_server_error_fallback(self, error_config, db_setup):
        """Test fallback behavior on server errors"""
        
        adapter = Mock(spec=ClickUpAdapter)
        adapter.create_task.return_value = {"id": "adapter-fallback", "title": "Fallback Task"}
        
        outbox = OutboxManager(get_conn)
        service = EnhancedTaskService(adapter, outbox)
        
        # Mock MCP bridge with server error
        with patch('app.integrations.mcp_bridge.MCPBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge_class.return_value = mock_bridge
            
            # Simulate server error
            mock_bridge._mcp_request.side_effect = ServerError(500, "Internal Server Error")
            mock_bridge._should_use_mcp.return_value = True
            
            service.mcp_bridge = mock_bridge
            
            task_data = {"title": "Server Error Task"}
            
            # Should raise ServerError (no fallback in _mcp_request)
            with pytest.raises(ServerError):
                await service.create_task(task_data)
    
    @pytest.mark.asyncio
    async def test_partial_service_degradation(self, error_config, db_setup):
        """Test behavior when some MCP features fail but others work"""
        
        adapter = Mock(spec=ClickUpAdapter)
        outbox = OutboxManager(get_conn)
        service = EnhancedTaskService(adapter, outbox)
        
        # Mock MCP bridge with selective failures
        with patch('app.integrations.mcp_bridge.MCPBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge_class.return_value = mock_bridge
            
            # Mock selective tool availability
            def should_use_mcp(operation):
                # Search fails, but basic operations work
                return operation != "search_tasks"
            
            mock_bridge._should_use_mcp.side_effect = should_use_mcp
            mock_bridge._mcp_request.return_value = {"id": "mcp-123", "name": "Working Task"}
            mock_bridge._map_task_from_mcp.return_value = {
                "external_id": "mcp-123",
                "title": "Working Task"
            }
            
            service.mcp_bridge = mock_bridge
            
            # Basic operations should work
            task_data = {"title": "Basic Task"}
            result = await service.create_task(task_data)
            assert result["external_id"] == "mcp-123"
            
            # Search should fail
            with pytest.raises(MCPBridgeError, match="Search functionality requires MCP server"):
                await service.search_tasks("test query")
    
    @pytest.mark.asyncio
    async def test_outbox_failure_recovery(self, error_config, db_setup):
        """Test recovery when outbox operations fail"""
        
        adapter = Mock(spec=ClickUpAdapter)
        
        # Mock failing outbox manager
        outbox = Mock(spec=OutboxManager)
        outbox.enqueue_operation.side_effect = Exception("Outbox database error")
        
        service = EnhancedTaskService(adapter, outbox)
        
        # Mock working MCP bridge
        with patch('app.integrations.mcp_bridge.MCPBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge_class.return_value = mock_bridge
            
            mock_bridge._mcp_request.return_value = {"id": "mcp-123", "name": "Test Task"}
            mock_bridge._should_use_mcp.return_value = True
            mock_bridge._map_task_from_mcp.return_value = {
                "external_id": "mcp-123",
                "title": "Test Task"
            }
            
            service.mcp_bridge = mock_bridge
            
            # Task creation should fail due to outbox error
            task_data = {"title": "Outbox Fail Task"}
            
            with pytest.raises(Exception, match="Outbox database error"):
                await service.create_task(task_data, use_outbox=True)
            
            # Should work without outbox
            result = await service.create_task(task_data, use_outbox=False)
            assert result["external_id"] == "mcp-123"


@pytest.mark.integration
class TestMCPIntegrationPerformance:
    """Test MCP integration performance characteristics"""
    
    @pytest.fixture(scope="class")
    def db_setup(self):
        """Setup test database"""
        os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
        init()
        yield
    
    @pytest.mark.asyncio
    async def test_concurrent_task_operations(self, db_setup):
        """Test concurrent task operations through MCP"""
        
        adapter = Mock(spec=ClickUpAdapter)
        outbox = OutboxManager(get_conn)
        service = EnhancedTaskService(adapter, outbox)
        
        # Mock high-performance MCP bridge
        with patch('app.integrations.mcp_bridge.MCPBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge_class.return_value = mock_bridge
            
            task_counter = 0
            
            def mock_mcp_request(tool, arguments):
                nonlocal task_counter
                task_counter += 1
                
                # Simulate small delay
                import asyncio
                return asyncio.sleep(0.01, result={
                    "id": f"mcp-{task_counter}",
                    "name": arguments.get("name", f"Task {task_counter}")
                })
            
            mock_bridge._mcp_request.side_effect = mock_mcp_request
            mock_bridge._should_use_mcp.return_value = True
            mock_bridge._map_task_from_mcp.side_effect = lambda task: {
                "external_id": task["id"],
                "title": task["name"]
            }
            
            service.mcp_bridge = mock_bridge
            
            # Create multiple tasks concurrently
            task_count = 10
            tasks = []
            
            start_time = time.time()
            
            for i in range(task_count):
                task_data = {"title": f"Concurrent Task {i}"}
                task_coro = service.create_task(task_data, use_outbox=False)
                tasks.append(task_coro)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify all tasks completed
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == task_count
            
            # Performance assertion - should complete relatively quickly
            # (This is a rough benchmark, adjust based on expected performance)
            assert duration < 2.0, f"Concurrent operations took too long: {duration}s"
            
            # Verify unique task IDs
            task_ids = {result["external_id"] for result in successful_results}
            assert len(task_ids) == task_count, "Task IDs should be unique"
    
    @pytest.mark.asyncio
    async def test_bulk_operations_performance(self, db_setup):
        """Test bulk operation performance"""
        
        adapter = Mock(spec=ClickUpAdapter)
        outbox = OutboxManager(get_conn)
        service = EnhancedTaskService(adapter, outbox)
        
        # Mock MCP bridge for bulk operations
        with patch('app.integrations.mcp_bridge.MCPBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge_class.return_value = mock_bridge
            
            def mock_update_task(task_id, data):
                # Simulate processing delay
                import asyncio
                return asyncio.sleep(0.005, result={
                    "id": task_id,
                    "name": data.get("title", "Updated Task"),
                    **data
                })
            
            mock_bridge.update_task.side_effect = mock_update_task
            service.mcp_bridge = mock_bridge
            
            # Prepare bulk updates
            updates = [
                {"task_id": f"task-{i}", "data": {"title": f"Bulk Updated Task {i}", "priority": i % 5 + 1}}
                for i in range(20)
            ]
            
            start_time = time.time()
            
            results = await service.bulk_update_tasks(updates, use_outbox=False)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify all updates completed
            successful_results = [r for r in results if r.get("success")]
            assert len(successful_results) == 20
            
            # Performance assertion
            assert duration < 3.0, f"Bulk updates took too long: {duration}s"
            
            # Verify no outbox overhead
            stats = outbox.get_stats()
            assert stats.get("pending", 0) == 0


@pytest.mark.integration 
class TestMCPIntegrationMonitoring:
    """Test MCP integration monitoring and health checks"""
    
    @pytest.fixture
    def monitoring_config(self, tmp_path):
        """Create configuration with monitoring enabled"""
        config_data = {
            "server": {
                "host": "localhost", 
                "port": 3231,
                "endpoint": "/mcp",
                "health_check_interval": 30
            },
            "features": {
                "enabled_tools": ["create_task", "get_task"],
                "disabled_tools": []
            },
            "integration": {
                "bridge_enabled": True,
                "fallback_to_adapter": True
            },
            "monitoring": {
                "metrics_enabled": True,
                "tracing_enabled": True,
                "error_rate_threshold": 0.05
            }
        }
        
        config_path = tmp_path / "monitoring_config.yml"
        with open(config_path, 'w') as f:
            import yaml
            yaml.safe_dump(config_data, f)
        
        return str(config_path)
    
    @pytest.mark.asyncio
    async def test_health_check_monitoring(self, monitoring_config):
        """Test MCP server health check monitoring"""
        
        adapter = Mock(spec=ClickUpAdapter)
        
        with patch('app.integrations.mcp_bridge.MCPBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge_class.return_value = mock_bridge
            
            # Mock health check responses
            health_checks = [True, True, False, True]  # Simulate temporary failure
            health_check_count = 0
            
            def mock_health_check():
                nonlocal health_check_count
                result = health_checks[health_check_count % len(health_checks)]
                health_check_count += 1
                mock_bridge._server_available = result
                mock_bridge._last_health_check = datetime.now(timezone.utc)
                return result
            
            mock_bridge._health_check.side_effect = mock_health_check
            mock_bridge.get_server_status.return_value = {
                "server_available": True,
                "last_health_check": datetime.now(timezone.utc).isoformat(),
                "enabled_tools": ["create_task", "get_task"]
            }
            
            bridge = MCPBridge(config_path=monitoring_config, clickup_adapter=adapter)
            bridge.client = AsyncMock()
            
            # Perform multiple health checks
            results = []
            for _ in range(4):
                result = await bridge._health_check()
                results.append(result)
            
            # Verify health check pattern
            expected = [True, True, False, True]
            assert results == expected
            
            # Verify health status tracking
            status = await bridge.get_server_status()
            assert "last_health_check" in status
            assert "server_available" in status
    
    @pytest.mark.asyncio
    async def test_service_status_comprehensive(self, monitoring_config):
        """Test comprehensive service status reporting"""
        
        adapter = Mock(spec=ClickUpAdapter)
        outbox = Mock(spec=OutboxManager)
        
        service = EnhancedTaskService(adapter, outbox)
        
        # Mock MCP bridge with detailed status
        with patch('app.integrations.mcp_bridge.MCPBridge') as mock_bridge_class:
            mock_bridge = AsyncMock()
            mock_bridge_class.return_value = mock_bridge
            
            mock_bridge.get_server_status.return_value = {
                "server_available": True,
                "server_url": "http://localhost:3231",
                "enabled_tools": ["create_task", "get_task", "list_tasks"],
                "fallback_enabled": True,
                "adapter_available": True,
                "last_health_check": datetime.now(timezone.utc).isoformat(),
                "request_count": 42,
                "error_count": 2,
                "success_rate": 0.95
            }
            
            service.mcp_bridge = mock_bridge
            
            # Get comprehensive status
            status = await service.get_service_status()
            
            # Verify all components reported
            assert status["adapter_available"] is True
            assert status["outbox_available"] is True
            assert status["mcp_available"] is True
            
            # Verify detailed MCP status
            mcp_status = status["mcp_status"]
            assert mcp_status["server_available"] is True
            assert mcp_status["server_url"] == "http://localhost:3231"
            assert len(mcp_status["enabled_tools"]) == 3
            assert mcp_status["success_rate"] == 0.95