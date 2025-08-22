"""
Unit Tests for EnhancedTaskService
Tests the Enhanced Task Service functionality, MCP integration, and outbox coordination
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone

from app.services.enhanced_tasks import EnhancedTaskService
from app.integrations.mcp_bridge import MCPBridge, MCPBridgeError, MCPServerUnavailableError
from app.providers.clickup import ClickUpAdapter
from app.utils.outbox import OutboxManager


class TestEnhancedTaskServiceInitialization:
    """Test Enhanced Task Service initialization and setup"""
    
    @pytest.fixture
    def mock_clickup_adapter(self):
        """Create mock ClickUp adapter"""
        adapter = Mock(spec=ClickUpAdapter)
        adapter.create_task.return_value = {"id": "clickup-123", "title": "Test Task"}
        adapter.get_task.return_value = {"id": "clickup-123", "title": "Test Task"}
        adapter.update_task.return_value = {"id": "clickup-123", "title": "Updated Task"}
        adapter.list_tasks.return_value = [{"id": "clickup-123", "title": "Test Task"}]
        return adapter
    
    @pytest.fixture
    def mock_outbox_manager(self):
        """Create mock outbox manager"""
        outbox = Mock(spec=OutboxManager)
        outbox.enqueue.return_value = "operation-id-123"
        return outbox
    
    def test_service_initialization(self, mock_clickup_adapter, mock_outbox_manager):
        """Test basic service initialization"""
        service = EnhancedTaskService(mock_clickup_adapter, mock_outbox_manager)
        
        assert service.clickup_adapter is mock_clickup_adapter
        assert service.outbox_manager is mock_outbox_manager
        assert service.mcp_bridge is None
    
    @pytest.mark.asyncio
    async def test_mcp_initialization_success(self, mock_clickup_adapter, mock_outbox_manager):
        """Test successful MCP bridge initialization"""
        service = EnhancedTaskService(mock_clickup_adapter, mock_outbox_manager)
        
        with patch('app.services.enhanced_tasks.MCPBridge') as mock_bridge_class:
            mock_bridge = AsyncMock(spec=MCPBridge)
            mock_bridge_class.return_value = mock_bridge
            
            await service.initialize_mcp("test_config.yml")
            
            assert service.mcp_bridge is mock_bridge
            mock_bridge_class.assert_called_once_with("test_config.yml", mock_clickup_adapter)
            mock_bridge.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mcp_initialization_failure(self, mock_clickup_adapter, mock_outbox_manager):
        """Test MCP bridge initialization failure"""
        service = EnhancedTaskService(mock_clickup_adapter, mock_outbox_manager)
        
        with patch('app.services.enhanced_tasks.MCPBridge') as mock_bridge_class:
            mock_bridge_class.side_effect = Exception("MCP connection failed")
            
            # Should not raise exception, just log warning
            await service.initialize_mcp("invalid_config.yml")
            
            assert service.mcp_bridge is None
    
    @pytest.mark.asyncio
    async def test_service_close(self, mock_clickup_adapter, mock_outbox_manager):
        """Test service cleanup and close"""
        service = EnhancedTaskService(mock_clickup_adapter, mock_outbox_manager)
        
        # Setup mock MCP bridge
        mock_bridge = AsyncMock(spec=MCPBridge)
        service.mcp_bridge = mock_bridge
        
        await service.close()
        
        mock_bridge.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_clickup_adapter, mock_outbox_manager):
        """Test using service as async context manager"""
        service = EnhancedTaskService(mock_clickup_adapter, mock_outbox_manager)
        
        with patch.object(service, 'initialize_mcp', new_callable=AsyncMock) as mock_init:
            with patch.object(service, 'close', new_callable=AsyncMock) as mock_close:
                async with service as s:
                    assert s is service
                
                mock_init.assert_called_once()
                mock_close.assert_called_once()


class TestEnhancedTaskServiceOperations:
    """Test Enhanced Task Service core operations"""
    
    @pytest.fixture
    def service_with_mcp(self):
        """Create service with mocked MCP bridge"""
        adapter = Mock(spec=ClickUpAdapter)
        adapter.create_task.return_value = {"id": "adapter-123", "title": "Adapter Task"}
        adapter.get_task.return_value = {"id": "adapter-123", "title": "Adapter Task"}
        adapter.update_task.return_value = {"id": "adapter-123", "title": "Updated Adapter Task"}
        adapter.list_tasks.return_value = [{"id": "adapter-123", "title": "Adapter Task"}]
        
        outbox = Mock(spec=OutboxManager)
        outbox.enqueue.return_value = "operation-id-123"
        
        service = EnhancedTaskService(adapter, outbox)
        
        # Mock MCP bridge
        mock_bridge = AsyncMock(spec=MCPBridge)
        mock_bridge.create_task.return_value = {"external_id": "mcp-123", "title": "MCP Task"}
        mock_bridge.get_task.return_value = {"external_id": "mcp-123", "title": "MCP Task"}
        mock_bridge.update_task.return_value = {"external_id": "mcp-123", "title": "Updated MCP Task"}
        mock_bridge.list_tasks.return_value = [{"external_id": "mcp-123", "title": "MCP Task"}]
        service.mcp_bridge = mock_bridge
        
        return service
    
    @pytest.fixture
    def service_without_mcp(self):
        """Create service without MCP bridge (adapter only)"""
        adapter = Mock(spec=ClickUpAdapter)
        adapter.create_task.return_value = {"id": "adapter-123", "title": "Adapter Task"}
        adapter.get_task.return_value = {"id": "adapter-123", "title": "Adapter Task"}
        adapter.update_task.return_value = {"id": "adapter-123", "title": "Updated Adapter Task"}
        adapter.list_tasks.return_value = [{"id": "adapter-123", "title": "Adapter Task"}]
        
        outbox = Mock(spec=OutboxManager)
        outbox.enqueue.return_value = "operation-id-123"
        
        service = EnhancedTaskService(adapter, outbox)
        service.mcp_bridge = None
        
        return service
    
    @pytest.mark.asyncio
    async def test_create_task_via_mcp(self, service_with_mcp):
        """Test task creation via MCP bridge"""
        task_data = {
            "title": "New Task",
            "description": "Task description",
            "priority": 4
        }
        
        result = await service_with_mcp.create_task(task_data, use_outbox=True)
        
        assert result["external_id"] == "mcp-123"
        assert result["title"] == "MCP Task"
        
        # Verify MCP bridge was called
        service_with_mcp.mcp_bridge.create_task.assert_called_once_with(task_data)
        
        # Verify outbox entry was created
        service_with_mcp.outbox_manager.enqueue.assert_called_once()
        call_args = service_with_mcp.outbox_manager.enqueue.call_args
        assert call_args[1]["provider"] == "clickup"
        assert call_args[1]["operation_type"] == "create_task"
        assert call_args[1]["endpoint"] == "clickup/tasks"
    
    @pytest.mark.asyncio
    async def test_create_task_via_adapter(self, service_without_mcp):
        """Test task creation via adapter fallback"""
        task_data = {
            "title": "New Task",
            "description": "Task description",
            "priority": 4
        }
        
        result = await service_without_mcp.create_task(task_data, use_outbox=True)
        
        assert result["id"] == "adapter-123"
        assert result["title"] == "Adapter Task"
        
        # Verify adapter was called
        service_without_mcp.clickup_adapter.create_task.assert_called_once_with(task_data)
        
        # Verify outbox entry was created
        service_without_mcp.outbox_manager.enqueue.assert_called_once()
        call_args = service_without_mcp.outbox_manager.enqueue.call_args
        assert call_args[1]["provider"] == "clickup"
        assert call_args[1]["operation_type"] == "create_task"
    
    @pytest.mark.asyncio
    async def test_create_task_without_outbox(self, service_with_mcp):
        """Test task creation without outbox logging"""
        task_data = {"title": "No Outbox Task"}
        
        result = await service_with_mcp.create_task(task_data, use_outbox=False)
        
        assert result["external_id"] == "mcp-123"
        
        # Verify no outbox entry was created
        service_with_mcp.outbox_manager.enqueue.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_task_via_mcp(self, service_with_mcp):
        """Test task retrieval via MCP bridge"""
        task_id = "test-task-123"
        
        result = await service_with_mcp.get_task(task_id)
        
        assert result["external_id"] == "mcp-123"
        assert result["title"] == "MCP Task"
        
        service_with_mcp.mcp_bridge.get_task.assert_called_once_with(task_id)
    
    @pytest.mark.asyncio
    async def test_get_task_via_adapter(self, service_without_mcp):
        """Test task retrieval via adapter"""
        task_id = "test-task-123"
        
        result = await service_without_mcp.get_task(task_id)
        
        assert result["id"] == "adapter-123"
        assert result["title"] == "Adapter Task"
        
        service_without_mcp.clickup_adapter.get_task.assert_called_once_with(task_id)
    
    @pytest.mark.asyncio
    async def test_update_task_via_mcp(self, service_with_mcp):
        """Test task update via MCP bridge"""
        task_id = "test-task-123"
        update_data = {"title": "Updated Title", "priority": 5}
        
        result = await service_with_mcp.update_task(task_id, update_data, use_outbox=True)
        
        assert result["external_id"] == "mcp-123"
        assert result["title"] == "Updated MCP Task"
        
        # Verify MCP bridge was called
        service_with_mcp.mcp_bridge.update_task.assert_called_once_with(task_id, update_data)
        
        # Verify outbox entry was created
        service_with_mcp.outbox_manager.enqueue.assert_called_once()
        call_args = service_with_mcp.outbox_manager.enqueue.call_args
        assert call_args[1]["provider"] == "clickup"
        assert call_args[1]["operation_type"] == "update_task"
        assert call_args[1]["endpoint"] == f"clickup/tasks/{task_id}"
    
    @pytest.mark.asyncio
    async def test_list_tasks_via_mcp(self, service_with_mcp):
        """Test task listing via MCP bridge"""
        filters = {"status_filter": "open", "assignee_filter": "john@example.com"}
        
        result = await service_with_mcp.list_tasks(filters)
        
        assert len(result) == 1
        assert result[0]["external_id"] == "mcp-123"
        
        service_with_mcp.mcp_bridge.list_tasks.assert_called_once_with(filters)
    
    @pytest.mark.asyncio
    async def test_list_tasks_via_adapter(self, service_without_mcp):
        """Test task listing via adapter with filter conversion"""
        filters = {"status_filter": "open", "assignee_filter": "john@example.com"}
        
        result = await service_without_mcp.list_tasks(filters)
        
        assert len(result) == 1
        assert result[0]["id"] == "adapter-123"
        
        # Verify adapter was called with converted filters
        service_without_mcp.clickup_adapter.list_tasks.assert_called_once_with(
            "open", "john@example.com"
        )
    
    @pytest.mark.asyncio
    async def test_list_tasks_adapter_dict_response(self, service_without_mcp):
        """Test task listing when adapter returns dict with tasks key"""
        # Mock adapter to return dict format
        service_without_mcp.clickup_adapter.list_tasks.return_value = {
            "tasks": [{"id": "task-1"}, {"id": "task-2"}],
            "total": 2
        }
        
        result = await service_without_mcp.list_tasks()
        
        assert len(result) == 2
        assert result[0]["id"] == "task-1"
        assert result[1]["id"] == "task-2"


class TestEnhancedTaskServiceAdvancedFeatures:
    """Test Enhanced Task Service advanced MCP-only features"""
    
    @pytest.fixture
    def service_for_advanced(self):
        """Create service for testing advanced features"""
        adapter = Mock(spec=ClickUpAdapter)
        outbox = Mock(spec=OutboxManager)
        service = EnhancedTaskService(adapter, outbox)
        
        # Mock MCP bridge with advanced features
        mock_bridge = AsyncMock(spec=MCPBridge)
        mock_bridge.search_tasks.return_value = [
            {"external_id": "search-1", "title": "Found Task 1"},
            {"external_id": "search-2", "title": "Found Task 2"}
        ]
        mock_bridge.get_task.return_value = {"external_id": "task-123", "title": "Task"}
        mock_bridge._mcp_request.return_value = {"time_tracked": "2h 30m"}
        service.mcp_bridge = mock_bridge
        
        return service
    
    @pytest.mark.asyncio
    async def test_search_tasks_with_mcp(self, service_for_advanced):
        """Test AI-enhanced task search via MCP"""
        query = "urgent client tasks"
        filters = {"client": "acme-corp", "priority": "high"}
        
        result = await service_for_advanced.search_tasks(query, filters)
        
        assert len(result) == 2
        assert result[0]["title"] == "Found Task 1"
        assert result[1]["title"] == "Found Task 2"
        
        service_for_advanced.mcp_bridge.search_tasks.assert_called_once_with(query, filters)
    
    @pytest.mark.asyncio
    async def test_search_tasks_without_mcp(self, service_for_advanced):
        """Test search tasks when MCP is unavailable"""
        # Remove MCP bridge to simulate unavailable state
        service_for_advanced.mcp_bridge = None
        
        with pytest.raises(MCPBridgeError, match="Search functionality requires MCP server"):
            await service_for_advanced.search_tasks("test query")
    
    @pytest.mark.asyncio
    async def test_get_task_insights_with_mcp(self, service_for_advanced):
        """Test getting AI-powered task insights"""
        task_id = "task-123"
        
        # Mock different MCP requests for insights
        def mock_mcp_request(operation, args):
            if operation == "get_task_time_tracked":
                return {"total_time": "5h 30m", "this_week": "2h 15m"}
            elif operation == "get_task_comments":
                return [
                    {"id": "comment-1", "text": "First comment", "author": "john@example.com"},
                    {"id": "comment-2", "text": "Second comment", "author": "jane@example.com"}
                ]
            elif operation == "get_task_members":
                return [
                    {"id": "user-1", "email": "john@example.com", "role": "assignee"},
                    {"id": "user-2", "email": "jane@example.com", "role": "watcher"}
                ]
            return {}
        
        service_for_advanced.mcp_bridge._mcp_request.side_effect = mock_mcp_request
        
        result = await service_for_advanced.get_task_insights(task_id)
        
        assert "task" in result
        assert result["task"]["external_id"] == "task-123"
        
        assert "time_tracking" in result
        assert result["time_tracking"]["total_time"] == "5h 30m"
        
        assert "comments" in result
        assert len(result["comments"]) == 2
        assert result["comments"][0]["author"] == "john@example.com"
        
        assert "members" in result
        assert len(result["members"]) == 2
        assert result["members"][0]["role"] == "assignee"
    
    @pytest.mark.asyncio
    async def test_get_task_insights_partial_failure(self, service_for_advanced):
        """Test task insights with partial failures"""
        task_id = "task-123"
        
        # Mock some requests to fail
        def mock_mcp_request(operation, args):
            if operation == "get_task_time_tracked":
                raise Exception("Time tracking not available")
            elif operation == "get_task_comments":
                return [{"id": "comment-1", "text": "Only comment"}]
            elif operation == "get_task_members":
                raise Exception("Members not available")
            return {}
        
        service_for_advanced.mcp_bridge._mcp_request.side_effect = mock_mcp_request
        
        result = await service_for_advanced.get_task_insights(task_id)
        
        # Should have basic task info and partial data
        assert "task" in result
        assert result["time_tracking"] is None
        assert len(result["comments"]) == 1
        assert result["members"] == []
    
    @pytest.mark.asyncio
    async def test_get_task_insights_without_mcp(self, service_for_advanced):
        """Test task insights when MCP is unavailable"""
        # Remove MCP bridge to simulate unavailable state
        service_for_advanced.mcp_bridge = None
        
        with pytest.raises(MCPBridgeError, match="Task insights require MCP server"):
            await service_for_advanced.get_task_insights("task-123")


class TestEnhancedTaskServiceBulkOperations:
    """Test Enhanced Task Service bulk operations"""
    
    @pytest.fixture
    def service_for_bulk(self):
        """Create service for bulk operation testing"""
        adapter = Mock(spec=ClickUpAdapter)
        outbox = Mock(spec=OutboxManager)
        service = EnhancedTaskService(adapter, outbox)
        
        # Mock MCP bridge
        mock_bridge = AsyncMock(spec=MCPBridge)
        
        def mock_update_task(task_id, data):
            return {"external_id": task_id, "title": f"Updated {task_id}", **data}
        
        mock_bridge.update_task.side_effect = mock_update_task
        service.mcp_bridge = mock_bridge
        
        return service
    
    @pytest.mark.asyncio
    async def test_bulk_update_tasks_success(self, service_for_bulk):
        """Test successful bulk task updates"""
        updates = [
            {"task_id": "task-1", "data": {"title": "Updated Task 1", "priority": 4}},
            {"task_id": "task-2", "data": {"title": "Updated Task 2", "priority": 5}},
            {"task_id": "task-3", "data": {"title": "Updated Task 3", "priority": 3}}
        ]
        
        results = await service_for_bulk.bulk_update_tasks(updates, use_outbox=True)
        
        assert len(results) == 3
        
        # Check all succeeded
        for i, result in enumerate(results):
            assert result["success"] is True
            assert result["task_id"] == f"task-{i+1}"
            assert result["data"]["external_id"] == f"task-{i+1}"
        
        # Verify each update was called
        assert service_for_bulk.mcp_bridge.update_task.call_count == 3
        
        # Verify outbox entries
        assert service_for_bulk.outbox_manager.enqueue.call_count == 3
    
    @pytest.mark.asyncio
    async def test_bulk_update_tasks_partial_failure(self, service_for_bulk):
        """Test bulk updates with some failures"""
        updates = [
            {"task_id": "task-1", "data": {"title": "Updated Task 1"}},
            {"task_id": "task-2", "data": {"title": "Updated Task 2"}},
            {"task_id": "task-3", "data": {"title": "Updated Task 3"}}
        ]
        
        # Mock second update to fail
        def mock_update_with_failure(task_id, data):
            if task_id == "task-2":
                raise Exception("Update failed for task-2")
            return {"external_id": task_id, "title": f"Updated {task_id}", **data}
        
        service_for_bulk.mcp_bridge.update_task.side_effect = mock_update_with_failure
        
        results = await service_for_bulk.bulk_update_tasks(updates, use_outbox=True)
        
        assert len(results) == 3
        
        # Check success/failure pattern
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert results[1]["error"] == "Update failed for task-2"
        assert results[2]["success"] is True
        
        # Verify outbox entries only for successful updates
        assert service_for_bulk.outbox_manager.enqueue.call_count == 2
    
    @pytest.mark.asyncio
    async def test_bulk_update_tasks_without_outbox(self, service_for_bulk):
        """Test bulk updates without outbox logging"""
        updates = [{"task_id": "task-1", "data": {"title": "Updated Task 1"}}]
        
        results = await service_for_bulk.bulk_update_tasks(updates, use_outbox=False)
        
        assert len(results) == 1
        assert results[0]["success"] is True
        
        # Verify no outbox entries
        service_for_bulk.outbox_manager.enqueue.assert_not_called()


class TestEnhancedTaskServiceErrorHandling:
    """Test Enhanced Task Service error handling and resilience"""
    
    @pytest.fixture
    def service_with_failing_mcp(self):
        """Create service with MCP bridge that fails"""
        adapter = Mock(spec=ClickUpAdapter)
        adapter.create_task.return_value = {"id": "adapter-fallback", "title": "Fallback Task"}
        
        outbox = Mock(spec=OutboxManager)
        service = EnhancedTaskService(adapter, outbox)
        
        # Mock failing MCP bridge
        mock_bridge = AsyncMock(spec=MCPBridge)
        mock_bridge.create_task.side_effect = MCPServerUnavailableError("MCP server down")
        mock_bridge.get_task.side_effect = Exception("Network error")
        service.mcp_bridge = mock_bridge
        
        return service
    
    @pytest.mark.asyncio
    async def test_task_creation_error_handling(self, service_with_failing_mcp):
        """Test error handling during task creation"""
        task_data = {"title": "Test Task"}
        
        with pytest.raises(MCPServerUnavailableError):
            await service_with_failing_mcp.create_task(task_data)
    
    @pytest.mark.asyncio
    async def test_task_retrieval_error_handling(self, service_with_failing_mcp):
        """Test error handling during task retrieval"""
        task_id = "test-task-123"
        
        with pytest.raises(Exception, match="Network error"):
            await service_with_failing_mcp.get_task(task_id)
    
    @pytest.mark.asyncio
    async def test_service_status_with_mcp_error(self, service_with_failing_mcp):
        """Test service status when MCP has errors"""
        # Mock MCP bridge status to fail
        service_with_failing_mcp.mcp_bridge.get_server_status.side_effect = Exception("Status error")
        
        status = await service_with_failing_mcp.get_service_status()
        
        assert status["adapter_available"] is True
        assert status["outbox_available"] is True
        assert status["mcp_available"] is True
        assert "error" in status["mcp_status"]
        assert status["mcp_status"]["error"] == "Status error"


class TestEnhancedTaskServiceStatus:
    """Test Enhanced Task Service status and monitoring"""
    
    @pytest.fixture
    def service_for_status(self):
        """Create service for status testing"""
        adapter = Mock(spec=ClickUpAdapter)
        outbox = Mock(spec=OutboxManager)
        service = EnhancedTaskService(adapter, outbox)
        
        # Mock MCP bridge with status
        mock_bridge = AsyncMock(spec=MCPBridge)
        mock_bridge.get_server_status.return_value = {
            "server_available": True,
            "server_url": "http://localhost:3231",
            "enabled_tools": ["create_task", "get_task"],
            "fallback_enabled": True
        }
        service.mcp_bridge = mock_bridge
        
        return service
    
    @pytest.mark.asyncio
    async def test_get_service_status_with_mcp(self, service_for_status):
        """Test getting complete service status"""
        status = await service_for_status.get_service_status()
        
        assert status["adapter_available"] is True
        assert status["outbox_available"] is True
        assert status["mcp_available"] is True
        
        assert "mcp_status" in status
        assert status["mcp_status"]["server_available"] is True
        assert status["mcp_status"]["server_url"] == "http://localhost:3231"
    
    @pytest.mark.asyncio
    async def test_get_service_status_without_mcp(self, service_for_status):
        """Test getting service status without MCP"""
        # Remove MCP bridge to simulate unavailable state
        service_for_status.mcp_bridge = None
        
        status = await service_for_status.get_service_status()
        
        assert status["adapter_available"] is True
        assert status["outbox_available"] is True
        assert status["mcp_available"] is False
        assert "mcp_status" not in status
    
    @pytest.mark.asyncio
    async def test_get_service_status_missing_components(self):
        """Test service status with missing components"""
        service = EnhancedTaskService(None, None)
        
        status = await service.get_service_status()
        
        assert status["adapter_available"] is False
        assert status["outbox_available"] is False
        assert status["mcp_available"] is False