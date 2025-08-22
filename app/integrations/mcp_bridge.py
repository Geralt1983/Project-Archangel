"""
MCP Bridge Integration Layer
Coordinates between Project Archangel and ClickUp MCP Server
"""

import asyncio
import httpx
import yaml
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime, timezone
import structlog
from app.utils.retry import retry_with_backoff, RetryConfig, RateLimitError, ServerError
from app.providers.clickup import ClickUpAdapter

logger = structlog.get_logger(__name__)

class MCPBridgeError(Exception):
    """Base exception for MCP Bridge operations"""
    pass

class MCPServerUnavailableError(MCPBridgeError):
    """Raised when MCP server is unavailable"""
    pass

class MCPBridge:
    """
    Bridge between Project Archangel and ClickUp MCP Server
    Provides unified interface for AI-enhanced task operations
    """
    
    def __init__(self, config_path: str = "config/mcp_server.yml", clickup_adapter: Optional[ClickUpAdapter] = None):
        self.config = self._load_config(config_path)
        self.clickup_adapter = clickup_adapter
        self.client = None
        self._server_available = False
        self._last_health_check = None
        self._health_check_lock = asyncio.Lock()
        
        # Initialize retry configuration
        self.retry_config = RetryConfig(
            max_tries=self.config.get("server", {}).get("max_retries", 3),
            base_delay=1.0,
            max_delay=30.0,
            jitter=0.3,
        )
        
        # Setup structured logging
        self.logger = logger.bind(
            component="mcp_bridge",
            server=f"{self.config['server']['host']}:{self.config['server']['port']}"
        )
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load MCP server configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            raise MCPBridgeError(f"Failed to load MCP config from {config_path}: {e}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self):
        """Establish connection to MCP server"""
        server_config = self.config["server"]
        base_url = f"http://{server_config['host']}:{server_config['port']}"
        
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(
                connect=server_config.get("connection_timeout", 10),
                read=server_config.get("request_timeout", 30),
                write=server_config.get("request_timeout", 30),
                pool=server_config.get("request_timeout", 30)
            )
        )
        
        # Perform initial health check
        await self._health_check()
        
        self.logger.info("MCP Bridge connected", server_available=self._server_available)
    
    async def disconnect(self):
        """Close connection to MCP server"""
        if self.client:
            await self.client.aclose()
            self.client = None
        
        self.logger.info("MCP Bridge disconnected")
    
    @retry_with_backoff()
    async def _health_check(self) -> bool:
        """Check if MCP server is available and responding"""
        if not self.client:
            self._server_available = False
            return False
        
        try:
            # Try to ping the MCP server endpoint
            response = await self.client.get("/health", timeout=5.0)
            self._server_available = response.status_code == 200
            self._last_health_check = datetime.now(timezone.utc)
            
            if self._server_available:
                self.logger.debug("MCP server health check passed")
            else:
                self.logger.warning("MCP server health check failed", 
                                  status_code=response.status_code)
            
            return self._server_available
            
        except Exception as e:
            self._server_available = False
            self.logger.warning("MCP server health check failed", error=str(e))
            return False
    
    async def _should_use_mcp(self, operation: str) -> bool:
        """Determine if operation should use MCP server or fallback to adapter"""
        if not self.config.get("integration", {}).get("bridge_enabled", True):
            return False
        
        if not self._server_available:
            # Try health check if it's been a while (with lock to prevent race conditions)
            async with self._health_check_lock:
                if (not self._last_health_check or 
                    (datetime.now(timezone.utc) - self._last_health_check).seconds > 60):
                    await self._health_check()
        
        if not self._server_available:
            return False
        
        # Check if operation is in enabled tools
        enabled_tools = self.config.get("features", {}).get("enabled_tools", [])
        disabled_tools = self.config.get("features", {}).get("disabled_tools", [])
        
        return operation in enabled_tools and operation not in disabled_tools
    
    @retry_with_backoff()
    async def _mcp_request(self, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to MCP server"""
        if not self.client:
            raise MCPServerUnavailableError("MCP client not connected")
        
        endpoint = self.config["server"]["endpoint"]
        payload = {
            "method": "tools/call",
            "params": {
                "name": tool,
                "arguments": arguments
            }
        }
        
        try:
            response = await self.client.post(endpoint, json=payload)
            
            if response.status_code == 429:
                retry_after = int(response.headers.get("retry-after", 60))
                raise RateLimitError(retry_after)
            
            if response.status_code >= 500:
                raise ServerError(response.status_code, response.text)
            
            if 400 <= response.status_code < 500:
                self.logger.warning("MCP client error", 
                                  tool=tool, 
                                  status_code=response.status_code,
                                  response_text=response.text[:200])
            
            response.raise_for_status()
            result = response.json()
            
            # Extract result content from MCP response format
            if "result" in result and "content" in result["result"]:
                return result["result"]["content"]
            
            return result
            
        except httpx.RequestError as e:
            self.logger.error("MCP request failed", tool=tool, error=str(e))
            raise MCPServerUnavailableError(f"MCP server request failed: {e}")
    
    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create task using MCP server or fallback to adapter"""
        operation = "create_task"
        
        if await self._should_use_mcp(operation):
            try:
                # Map Project Archangel task format to MCP format
                mcp_task = self._map_task_to_mcp(task_data)
                result = await self._mcp_request(operation, mcp_task)
                
                self.logger.info("Task created via MCP", task_id=result.get("id"))
                return self._map_task_from_mcp(result)
                
            except (MCPServerUnavailableError, ServerError) as e:
                self.logger.warning("MCP create_task failed, falling back to adapter", error=str(e))
                if self.clickup_adapter and self.config.get("integration", {}).get("fallback_to_adapter", True):
                    return self.clickup_adapter.create_task(task_data)
                raise
        
        # Use existing adapter
        if not self.clickup_adapter:
            raise MCPBridgeError("No ClickUp adapter available for fallback")
        
        return self.clickup_adapter.create_task(task_data)
    
    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task using MCP server or fallback to adapter"""
        operation = "get_task"
        
        if await self._should_use_mcp(operation):
            try:
                result = await self._mcp_request(operation, {"task_id": task_id})
                return self._map_task_from_mcp(result)
                
            except (MCPServerUnavailableError, ServerError) as e:
                self.logger.warning("MCP get_task failed, falling back to adapter", error=str(e))
                if self.clickup_adapter and self.config.get("integration", {}).get("fallback_to_adapter", True):
                    return self.clickup_adapter.get_task(task_id)
                raise
        
        if not self.clickup_adapter:
            raise MCPBridgeError("No ClickUp adapter available for fallback")
        
        return self.clickup_adapter.get_task(task_id)
    
    async def update_task(self, task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update task using MCP server or fallback to adapter"""
        operation = "update_task"
        
        if await self._should_use_mcp(operation):
            try:
                mcp_data = self._map_task_to_mcp(task_data)
                mcp_data["task_id"] = task_id
                result = await self._mcp_request(operation, mcp_data)
                
                self.logger.info("Task updated via MCP", task_id=task_id)
                return self._map_task_from_mcp(result)
                
            except (MCPServerUnavailableError, ServerError) as e:
                self.logger.warning("MCP update_task failed, falling back to adapter", error=str(e))
                if self.clickup_adapter and self.config.get("integration", {}).get("fallback_to_adapter", True):
                    return self.clickup_adapter.update_task(task_id, task_data)
                raise
        
        if not self.clickup_adapter:
            raise MCPBridgeError("No ClickUp adapter available for fallback")
        
        return self.clickup_adapter.update_task(task_id, task_data)
    
    async def list_tasks(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List tasks using MCP server or fallback to adapter"""
        operation = "list_tasks"
        
        if await self._should_use_mcp(operation):
            try:
                arguments = filters or {}
                result = await self._mcp_request(operation, arguments)
                
                # Handle different result formats
                if isinstance(result, dict) and "tasks" in result:
                    tasks = result["tasks"]
                elif isinstance(result, list):
                    tasks = result
                else:
                    tasks = [result] if result else []
                
                return [self._map_task_from_mcp(task) for task in tasks]
                
            except (MCPServerUnavailableError, ServerError) as e:
                self.logger.warning("MCP list_tasks failed, falling back to adapter", error=str(e))
                if self.clickup_adapter and self.config.get("integration", {}).get("fallback_to_adapter", True):
                    return self.clickup_adapter.list_tasks(
                        status_filter=filters.get("status_filter") if filters else None,
                        assignee_filter=filters.get("assignee_filter") if filters else None
                    )
                raise
        
        if not self.clickup_adapter:
            raise MCPBridgeError("No ClickUp adapter available for fallback")
        
        result = self.clickup_adapter.list_tasks(
            status_filter=filters.get("status_filter") if filters else None,
            assignee_filter=filters.get("assignee_filter") if filters else None
        )
        
        # Convert adapter result to consistent format
        if isinstance(result, dict) and "tasks" in result:
            return result["tasks"]
        return result if isinstance(result, list) else []
    
    async def search_tasks(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search tasks using MCP server (no adapter fallback for this advanced feature)"""
        operation = "search_tasks"
        
        if not await self._should_use_mcp(operation):
            raise MCPBridgeError("Search functionality requires MCP server")
        
        arguments = {"query": query}
        if filters:
            arguments.update(filters)
        
        result = await self._mcp_request(operation, arguments)
        
        # Handle different result formats
        if isinstance(result, dict) and "tasks" in result:
            tasks = result["tasks"]
        elif isinstance(result, list):
            tasks = result
        else:
            tasks = [result] if result else []
        
        return [self._map_task_from_mcp(task) for task in tasks]
    
    def _map_task_to_mcp(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Project Archangel task format to MCP format"""
        mcp_task = {}
        
        # Direct field mappings
        field_mappings = {
            "title": "name",
            "description": "description", 
            "deadline": "due_date",
            "labels": "tags",
            "assignee": "assignees"
        }
        
        for archangel_field, mcp_field in field_mappings.items():
            if archangel_field in task_data:
                value = task_data[archangel_field]
                if archangel_field == "assignee" and value:
                    # Convert single assignee to list
                    mcp_task[mcp_field] = [value] if not isinstance(value, list) else value
                else:
                    mcp_task[mcp_field] = value
        
        # Priority mapping
        if "priority" in task_data:
            priority_mapping = self.config.get("integration", {}).get("priority_mapping", {})
            mcp_task["priority"] = priority_mapping.get(str(task_data["priority"]), task_data["priority"])
        
        return mcp_task
    
    def _map_task_from_mcp(self, mcp_task: Dict[str, Any]) -> Dict[str, Any]:
        """Map MCP task format to Project Archangel format"""
        archangel_task = {}
        
        # Direct field mappings (reverse)
        field_mappings = {
            "name": "title",
            "description": "description",
            "due_date": "deadline", 
            "tags": "labels",
            "assignees": "assignee"
        }
        
        for mcp_field, archangel_field in field_mappings.items():
            if mcp_field in mcp_task:
                value = mcp_task[mcp_field]
                if mcp_field == "assignees" and isinstance(value, list) and value:
                    # Convert assignee list to single assignee (take first)
                    archangel_task[archangel_field] = value[0]
                else:
                    archangel_task[archangel_field] = value
        
        # Reverse priority mapping
        if "priority" in mcp_task:
            priority_mapping = self.config.get("integration", {}).get("priority_mapping", {})
            # Create reverse mapping with integer conversion
            reverse_mapping = {v: int(k) for k, v in priority_mapping.items()}
            archangel_task["priority"] = reverse_mapping.get(mcp_task["priority"], mcp_task["priority"])
        
        # Preserve ClickUp-specific fields
        if "id" in mcp_task:
            archangel_task["external_id"] = mcp_task["id"]
        if "status" in mcp_task:
            status_mapping = self.config.get("integration", {}).get("status_mapping", {})
            archangel_task["status"] = status_mapping.get(mcp_task["status"], mcp_task["status"])
        
        return archangel_task
    
    async def get_server_status(self) -> Dict[str, Any]:
        """Get MCP server status and health information"""
        await self._health_check()
        
        return {
            "server_available": self._server_available,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "server_url": f"http://{self.config['server']['host']}:{self.config['server']['port']}",
            "enabled_tools": self.config.get("features", {}).get("enabled_tools", []),
            "fallback_enabled": self.config.get("integration", {}).get("fallback_to_adapter", True),
            "adapter_available": self.clickup_adapter is not None
        }