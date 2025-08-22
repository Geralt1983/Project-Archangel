"""
Unit Tests for MCPBridge Integration
Tests the MCP Bridge class functionality, error handling, and configuration
"""

import pytest
import asyncio
import json
import yaml
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import httpx
from datetime import datetime, timezone

from app.integrations.mcp_bridge import (
    MCPBridge, 
    MCPBridgeError, 
    MCPServerUnavailableError
)
from app.providers.clickup import ClickUpAdapter
from app.utils.retry import RateLimitError, ServerError


class TestMCPBridgeConfiguration:
    """Test MCP Bridge configuration loading and validation"""
    
    @pytest.fixture
    def sample_config(self, tmp_path):
        """Create a sample configuration file for testing"""
        config_data = {
            "server": {
                "host": "127.0.0.1",
                "port": 3231,
                "endpoint": "/mcp",
                "connection_timeout": 10,
                "request_timeout": 30,
                "max_retries": 3
            },
            "features": {
                "enabled_tools": ["create_task", "get_task", "list_tasks"],
                "disabled_tools": ["delete_task"]
            },
            "integration": {
                "bridge_enabled": True,
                "fallback_to_adapter": True,
                "priority_mapping": {
                    "1": 4, "2": 3, "3": 3, "4": 2, "5": 1
                },
                "status_mapping": {
                    "open": "pending",
                    "in progress": "in_progress",
                    "done": "completed"
                }
            }
        }
        
        config_path = tmp_path / "test_mcp_config.yml"
        with open(config_path, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        return str(config_path)
    
    def test_config_loading_success(self, sample_config):
        """Test successful configuration loading"""
        bridge = MCPBridge(config_path=sample_config)
        
        assert bridge.config["server"]["host"] == "127.0.0.1"
        assert bridge.config["server"]["port"] == 3231
        assert "create_task" in bridge.config["features"]["enabled_tools"]
        assert "delete_task" in bridge.config["features"]["disabled_tools"]
    
    def test_config_loading_failure(self):
        """Test configuration loading with non-existent file"""
        with pytest.raises(MCPBridgeError, match="Failed to load MCP config"):
            MCPBridge(config_path="non_existent_config.yml")
    
    def test_config_loading_invalid_yaml(self, tmp_path):
        """Test configuration loading with invalid YAML"""
        invalid_config = tmp_path / "invalid_config.yml"
        with open(invalid_config, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        with pytest.raises(MCPBridgeError, match="Failed to load MCP config"):
            MCPBridge(config_path=str(invalid_config))


class TestMCPBridgeConnection:
    """Test MCP Bridge connection management"""
    
    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create mock configuration for testing"""
        config_data = {
            "server": {
                "host": "localhost",
                "port": 3231,
                "endpoint": "/mcp",
                "connection_timeout": 5,
                "request_timeout": 10,
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
        
        config_path = tmp_path / "mock_config.yml"
        with open(config_path, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        return str(config_path)
    
    @pytest.fixture
    def mock_clickup_adapter(self):
        """Create mock ClickUp adapter for testing"""
        adapter = Mock(spec=ClickUpAdapter)
        adapter.create_task.return_value = {"id": "clickup-123", "title": "Test Task"}
        adapter.get_task.return_value = {"id": "clickup-123", "title": "Test Task"}
        adapter.update_task.return_value = {"id": "clickup-123", "title": "Updated Task"}
        adapter.list_tasks.return_value = [{"id": "clickup-123", "title": "Test Task"}]
        return adapter
    
    @pytest.mark.asyncio
    async def test_connection_success(self, mock_config, mock_clickup_adapter):
        """Test successful connection to MCP server"""
        bridge = MCPBridge(config_path=mock_config, clickup_adapter=mock_clickup_adapter)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock successful health check
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            
            await bridge.connect()
            
            assert bridge.client is not None
            assert bridge._server_available is True
            mock_client.get.assert_called_once_with("/health", timeout=5.0)
    
    @pytest.mark.asyncio
    async def test_connection_health_check_failure(self, mock_config, mock_clickup_adapter):
        """Test connection with health check failure"""
        bridge = MCPBridge(config_path=mock_config, clickup_adapter=mock_clickup_adapter)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock failed health check
            mock_response = Mock()
            mock_response.status_code = 500
            mock_client.get.return_value = mock_response
            
            await bridge.connect()
            
            assert bridge.client is not None
            assert bridge._server_available is False
    
    @pytest.mark.asyncio
    async def test_connection_network_error(self, mock_config, mock_clickup_adapter):
        """Test connection with network error"""
        bridge = MCPBridge(config_path=mock_config, clickup_adapter=mock_clickup_adapter)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock network error
            mock_client.get.side_effect = httpx.RequestError("Connection failed")
            
            await bridge.connect()
            
            assert bridge.client is not None
            assert bridge._server_available is False
    
    @pytest.mark.asyncio
    async def test_disconnect(self, mock_config, mock_clickup_adapter):
        """Test disconnection from MCP server"""
        bridge = MCPBridge(config_path=mock_config, clickup_adapter=mock_clickup_adapter)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            bridge.client = mock_client
            
            await bridge.disconnect()
            
            mock_client.aclose.assert_called_once()
            assert bridge.client is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_config, mock_clickup_adapter):
        """Test using MCPBridge as async context manager"""
        bridge = MCPBridge(config_path=mock_config, clickup_adapter=mock_clickup_adapter)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock successful health check
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            
            async with bridge as b:
                assert b is bridge
                assert bridge.client is not None
            
            mock_client.aclose.assert_called_once()


class TestMCPBridgeTaskOperations:
    """Test MCP Bridge task operations"""
    
    @pytest.fixture
    def configured_bridge(self, tmp_path):
        """Create a configured MCP bridge for testing"""
        config_data = {
            "server": {
                "host": "localhost",
                "port": 3231,
                "endpoint": "/mcp",
                "max_retries": 2
            },
            "features": {
                "enabled_tools": ["create_task", "get_task", "update_task", "list_tasks", "search_tasks"],
                "disabled_tools": []
            },
            "integration": {
                "bridge_enabled": True,
                "fallback_to_adapter": True,
                "priority_mapping": {"1": 4, "2": 3, "3": 3, "4": 2, "5": 1},
                "status_mapping": {
                    "open": "pending",
                    "in progress": "in_progress",
                    "done": "completed"
                }
            }
        }
        
        config_path = tmp_path / "bridge_config.yml"
        with open(config_path, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        adapter = Mock(spec=ClickUpAdapter)
        adapter.create_task.return_value = {"id": "adapter-123", "title": "Adapter Task"}
        adapter.get_task.return_value = {"id": "adapter-123", "title": "Adapter Task"}
        adapter.update_task.return_value = {"id": "adapter-123", "title": "Updated Adapter Task"}
        adapter.list_tasks.return_value = [{"id": "adapter-123", "title": "Adapter Task"}]
        
        bridge = MCPBridge(config_path=str(config_path), clickup_adapter=adapter)
        bridge._server_available = True
        bridge.client = AsyncMock()
        
        return bridge
    
    @pytest.mark.asyncio
    async def test_create_task_via_mcp(self, configured_bridge):
        """Test task creation via MCP server"""
        task_data = {
            "title": "Test Task",
            "description": "Test description",
            "deadline": "2024-12-31T23:59:59Z",
            "priority": 4
        }
        
        # Mock MCP response
        mcp_response = {
            "result": {
                "content": {
                    "id": "mcp-123",
                    "name": "Test Task",
                    "description": "Test description", 
                    "due_date": "2024-12-31T23:59:59Z",
                    "priority": 2
                }
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mcp_response
        configured_bridge.client.post.return_value = mock_response
        
        result = await configured_bridge.create_task(task_data)
        
        assert result["external_id"] == "mcp-123"
        assert result["title"] == "Test Task"
        assert result["description"] == "Test description"
        configured_bridge.client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_task_fallback_to_adapter(self, configured_bridge):
        """Test task creation fallback to adapter when MCP fails"""
        task_data = {"title": "Test Task", "description": "Test description"}
        
        # Mock MCP server unavailable
        configured_bridge.client.post.side_effect = httpx.RequestError("Server unavailable")
        
        result = await configured_bridge.create_task(task_data)
        
        # Should fallback to adapter
        assert result["id"] == "adapter-123"
        assert result["title"] == "Adapter Task"
        configured_bridge.clickup_adapter.create_task.assert_called_once_with(task_data)
    
    @pytest.mark.asyncio
    async def test_get_task_via_mcp(self, configured_bridge):
        """Test task retrieval via MCP server"""
        task_id = "test-task-123"
        
        # Mock MCP response
        mcp_response = {
            "result": {
                "content": {
                    "id": "mcp-123",
                    "name": "Retrieved Task",
                    "status": "open"
                }
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mcp_response
        configured_bridge.client.post.return_value = mock_response
        
        result = await configured_bridge.get_task(task_id)
        
        assert result["external_id"] == "mcp-123"
        assert result["title"] == "Retrieved Task"
        assert result["status"] == "pending"  # Mapped from "open"
    
    @pytest.mark.asyncio
    async def test_update_task_via_mcp(self, configured_bridge):
        """Test task update via MCP server"""
        task_id = "test-task-123"
        update_data = {"title": "Updated Task", "priority": 5}
        
        # Mock MCP response
        mcp_response = {
            "result": {
                "content": {
                    "id": "mcp-123",
                    "name": "Updated Task",
                    "priority": 1
                }
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mcp_response
        configured_bridge.client.post.return_value = mock_response
        
        result = await configured_bridge.update_task(task_id, update_data)
        
        assert result["external_id"] == "mcp-123"
        assert result["title"] == "Updated Task"
        assert result["priority"] == 5  # Reverse mapped from 1
    
    @pytest.mark.asyncio
    async def test_list_tasks_via_mcp(self, configured_bridge):
        """Test task listing via MCP server"""
        filters = {"status_filter": "open"}
        
        # Mock MCP response
        mcp_response = {
            "result": {
                "content": {
                    "tasks": [
                        {"id": "mcp-1", "name": "Task 1", "status": "open"},
                        {"id": "mcp-2", "name": "Task 2", "status": "in progress"}
                    ]
                }
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mcp_response
        configured_bridge.client.post.return_value = mock_response
        
        result = await configured_bridge.list_tasks(filters)
        
        assert len(result) == 2
        assert result[0]["external_id"] == "mcp-1"
        assert result[0]["title"] == "Task 1"
        assert result[1]["status"] == "in_progress"  # Mapped from "in progress"
    
    @pytest.mark.asyncio
    async def test_search_tasks_mcp_only(self, configured_bridge):
        """Test task search (MCP-only feature)"""
        query = "urgent tasks"
        filters = {"priority": "high"}
        
        # Mock MCP response
        mcp_response = {
            "result": {
                "content": [
                    {"id": "mcp-urgent-1", "name": "Urgent Task 1", "priority": 1},
                    {"id": "mcp-urgent-2", "name": "Urgent Task 2", "priority": 1}
                ]
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mcp_response
        configured_bridge.client.post.return_value = mock_response
        
        result = await configured_bridge.search_tasks(query, filters)
        
        assert len(result) == 2
        assert "Urgent Task 1" in result[0]["title"]
        assert result[0]["priority"] == 5  # Reverse mapped from 1
    
    @pytest.mark.asyncio
    async def test_search_tasks_mcp_unavailable(self, configured_bridge):
        """Test search tasks when MCP is unavailable"""
        configured_bridge._server_available = False
        
        with pytest.raises(MCPBridgeError, match="Search functionality requires MCP server"):
            await configured_bridge.search_tasks("test query")


class TestMCPBridgeErrorHandling:
    """Test MCP Bridge error handling and retry logic"""
    
    @pytest.fixture
    def bridge_with_retry(self, tmp_path):
        """Create bridge configured with retry settings"""
        config_data = {
            "server": {
                "host": "localhost",
                "port": 3231,
                "endpoint": "/mcp",
                "max_retries": 3
            },
            "features": {
                "enabled_tools": ["create_task"],
                "disabled_tools": []
            },
            "integration": {"bridge_enabled": True, "fallback_to_adapter": True}
        }
        
        config_path = tmp_path / "retry_config.yml"
        with open(config_path, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        bridge = MCPBridge(config_path=str(config_path))
        bridge._server_available = True
        bridge.client = AsyncMock()
        
        return bridge
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, bridge_with_retry):
        """Test handling of rate limit errors"""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": "60"}
        bridge_with_retry.client.post.return_value = mock_response
        
        with pytest.raises(RateLimitError):
            await bridge_with_retry._mcp_request("create_task", {"title": "Test"})
    
    @pytest.mark.asyncio
    async def test_server_error_handling(self, bridge_with_retry):
        """Test handling of server errors"""
        # Mock server error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        bridge_with_retry.client.post.return_value = mock_response
        
        with pytest.raises(ServerError):
            await bridge_with_retry._mcp_request("create_task", {"title": "Test"})
    
    @pytest.mark.asyncio
    async def test_request_error_handling(self, bridge_with_retry):
        """Test handling of request errors"""
        # Mock network error
        bridge_with_retry.client.post.side_effect = httpx.RequestError("Network error")
        
        with pytest.raises(MCPServerUnavailableError, match="MCP server request failed"):
            await bridge_with_retry._mcp_request("create_task", {"title": "Test"})
    
    @pytest.mark.asyncio
    async def test_should_use_mcp_decision_logic(self, bridge_with_retry):
        """Test decision logic for when to use MCP vs adapter"""
        # Bridge enabled, server available, tool enabled
        assert await bridge_with_retry._should_use_mcp("create_task") is True
        
        # Server unavailable
        bridge_with_retry._server_available = False
        assert await bridge_with_retry._should_use_mcp("create_task") is False
        
        # Tool disabled
        bridge_with_retry._server_available = True
        bridge_with_retry.config["features"]["disabled_tools"] = ["create_task"]
        assert await bridge_with_retry._should_use_mcp("create_task") is False
        
        # Bridge disabled
        bridge_with_retry.config["integration"]["bridge_enabled"] = False
        assert await bridge_with_retry._should_use_mcp("create_task") is False


class TestMCPBridgeDataMapping:
    """Test data mapping between Project Archangel and MCP formats"""
    
    @pytest.fixture
    def bridge_for_mapping(self, tmp_path):
        """Create bridge for testing data mapping"""
        config_data = {
            "server": {"host": "localhost", "port": 3231, "endpoint": "/mcp"},
            "features": {"enabled_tools": [], "disabled_tools": []},
            "integration": {
                "bridge_enabled": True,
                "priority_mapping": {"1": 4, "2": 3, "3": 3, "4": 2, "5": 1},
                "status_mapping": {
                    "open": "pending",
                    "in progress": "in_progress",
                    "done": "completed"
                }
            }
        }
        
        config_path = tmp_path / "mapping_config.yml"
        with open(config_path, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        return MCPBridge(config_path=str(config_path))
    
    def test_map_task_to_mcp(self, bridge_for_mapping):
        """Test mapping Project Archangel task to MCP format"""
        archangel_task = {
            "title": "Test Task",
            "description": "Test description",
            "deadline": "2024-12-31T23:59:59Z",
            "labels": ["urgent", "client-work"],
            "assignee": "john.doe@example.com",
            "priority": 4
        }
        
        mcp_task = bridge_for_mapping._map_task_to_mcp(archangel_task)
        
        assert mcp_task["name"] == "Test Task"
        assert mcp_task["description"] == "Test description"
        assert mcp_task["due_date"] == "2024-12-31T23:59:59Z"
        assert mcp_task["tags"] == ["urgent", "client-work"]
        assert mcp_task["assignees"] == ["john.doe@example.com"]
        assert mcp_task["priority"] == 2  # Mapped from 4 to 2
    
    def test_map_task_from_mcp(self, bridge_for_mapping):
        """Test mapping MCP task to Project Archangel format"""
        mcp_task = {
            "id": "mcp-123",
            "name": "MCP Task",
            "description": "MCP description",
            "due_date": "2024-12-31T23:59:59Z",
            "tags": ["development", "feature"],
            "assignees": ["jane.doe@example.com", "john.doe@example.com"],
            "priority": 1,
            "status": "in progress"
        }
        
        archangel_task = bridge_for_mapping._map_task_from_mcp(mcp_task)
        
        assert archangel_task["external_id"] == "mcp-123"
        assert archangel_task["title"] == "MCP Task"
        assert archangel_task["description"] == "MCP description"
        assert archangel_task["deadline"] == "2024-12-31T23:59:59Z"
        assert archangel_task["labels"] == ["development", "feature"]
        assert archangel_task["assignee"] == "jane.doe@example.com"  # First assignee
        assert archangel_task["priority"] == 5  # Reverse mapped from 1 to 5
        assert archangel_task["status"] == "in_progress"  # Mapped from "in progress"
    
    def test_map_task_with_missing_fields(self, bridge_for_mapping):
        """Test mapping with missing optional fields"""
        minimal_task = {"title": "Minimal Task"}
        
        mcp_task = bridge_for_mapping._map_task_to_mcp(minimal_task)
        assert mcp_task["name"] == "Minimal Task"
        assert "description" not in mcp_task
        assert "priority" not in mcp_task
        
        archangel_task = bridge_for_mapping._map_task_from_mcp({"name": "Minimal MCP Task"})
        assert archangel_task["title"] == "Minimal MCP Task"
        assert "external_id" not in archangel_task
        assert "priority" not in archangel_task


class TestMCPBridgeStatus:
    """Test MCP Bridge status and health monitoring"""
    
    @pytest.fixture
    def status_bridge(self, tmp_path):
        """Create bridge for status testing"""
        config_data = {
            "server": {"host": "test-host", "port": 1234, "endpoint": "/mcp"},
            "features": {
                "enabled_tools": ["create_task", "get_task"],
                "disabled_tools": ["delete_task"]
            },
            "integration": {"bridge_enabled": True, "fallback_to_adapter": True}
        }
        
        config_path = tmp_path / "status_config.yml"
        with open(config_path, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        adapter = Mock(spec=ClickUpAdapter)
        bridge = MCPBridge(config_path=str(config_path), clickup_adapter=adapter)
        
        return bridge
    
    @pytest.mark.asyncio
    async def test_get_server_status(self, status_bridge):
        """Test getting server status information"""
        # Mock health check
        status_bridge._server_available = True
        status_bridge._last_health_check = datetime.now(timezone.utc)
        
        with patch.object(status_bridge, '_health_check', return_value=True):
            status = await status_bridge.get_server_status()
        
        assert status["server_available"] is True
        assert status["server_url"] == "http://test-host:1234"
        assert "create_task" in status["enabled_tools"]
        assert status["fallback_enabled"] is True
        assert status["adapter_available"] is True
        assert status["last_health_check"] is not None
    
    @pytest.mark.asyncio
    async def test_health_check_timeout_update(self, status_bridge):
        """Test health check with timeout logic"""
        status_bridge.client = AsyncMock()
        status_bridge._server_available = False
        status_bridge._last_health_check = None
        
        # Mock successful health check
        mock_response = Mock()
        mock_response.status_code = 200
        status_bridge.client.get.return_value = mock_response
        
        # First check
        result = await status_bridge._health_check()
        assert result is True
        assert status_bridge._server_available is True
        assert status_bridge._last_health_check is not None
        
        # Second check should use cached result without calling server
        with patch.object(status_bridge.client, 'get') as mock_get:
            await status_bridge._should_use_mcp("create_task")
            mock_get.assert_not_called()  # Should use cached health check