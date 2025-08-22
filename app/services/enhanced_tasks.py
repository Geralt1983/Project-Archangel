"""
Enhanced Task Service
Combines existing CRUD operations with MCP-powered AI features
"""

from typing import Dict, List, Optional, Any
import structlog
from app.integrations.mcp_bridge import MCPBridge, MCPBridgeError
from app.providers.clickup import ClickUpAdapter
from app.utils.outbox import OutboxManager

logger = structlog.get_logger(__name__)

class EnhancedTaskService:
    """
    Enhanced task service that provides AI-powered task operations
    through MCP integration while maintaining compatibility with existing systems
    """
    
    def __init__(self, clickup_adapter: ClickUpAdapter, outbox_manager: OutboxManager):
        self.clickup_adapter = clickup_adapter
        self.outbox_manager = outbox_manager
        self.mcp_bridge = None
        self.logger = logger.bind(component="enhanced_task_service")
    
    async def initialize_mcp(self, config_path: str = "config/mcp_server.yml"):
        """Initialize MCP bridge connection"""
        try:
            self.mcp_bridge = MCPBridge(config_path, self.clickup_adapter)
            await self.mcp_bridge.connect()
            self.logger.info("MCP bridge initialized successfully")
        except Exception as e:
            self.logger.warning("Failed to initialize MCP bridge", error=str(e))
            # Continue without MCP - service will use adapter only
    
    async def close(self):
        """Close MCP bridge connection"""
        if self.mcp_bridge:
            await self.mcp_bridge.disconnect()
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize_mcp()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def create_task(self, task_data: Dict[str, Any], use_outbox: bool = True) -> Dict[str, Any]:
        """
        Create task using enhanced capabilities when available
        
        Args:
            task_data: Task information
            use_outbox: Whether to use outbox pattern for reliability
            
        Returns:
            Created task data
        """
        try:
            if self.mcp_bridge:
                # Use MCP bridge for enhanced creation
                result = await self.mcp_bridge.create_task(task_data)
                
                # Log to outbox if enabled
                if use_outbox:
                    self.outbox_manager.enqueue(
                        operation_type="create_task",
                        endpoint=f"clickup/tasks",
                        request=task_data,
                        provider="clickup"
                    )
                
                self.logger.info("Task created via enhanced service", 
                               task_id=result.get("external_id"), via_mcp=True)
                return result
            
            else:
                # Fallback to direct adapter
                result = self.clickup_adapter.create_task(task_data)
                
                if use_outbox:
                    self.outbox_manager.enqueue(
                        operation_type="create_task",
                        endpoint="clickup/tasks",
                        request=task_data,
                        provider="clickup"
                    )
                
                self.logger.info("Task created via adapter fallback", 
                               task_id=result.get("id"), via_mcp=False)
                return result
                
        except Exception as e:
            self.logger.error("Task creation failed", error=str(e))
            raise
    
    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task using enhanced capabilities when available"""
        try:
            if self.mcp_bridge:
                result = await self.mcp_bridge.get_task(task_id)
                self.logger.debug("Task retrieved via MCP", task_id=task_id)
                return result
            else:
                result = self.clickup_adapter.get_task(task_id)
                self.logger.debug("Task retrieved via adapter", task_id=task_id)
                return result
                
        except Exception as e:
            self.logger.error("Task retrieval failed", task_id=task_id, error=str(e))
            raise
    
    async def update_task(self, task_id: str, task_data: Dict[str, Any], use_outbox: bool = True) -> Dict[str, Any]:
        """Update task using enhanced capabilities when available"""
        try:
            if self.mcp_bridge:
                result = await self.mcp_bridge.update_task(task_id, task_data)
                
                if use_outbox:
                    self.outbox_manager.enqueue(
                        operation_type="update_task",
                        endpoint=f"clickup/tasks/{task_id}",
                        request=task_data,
                        provider="clickup"
                    )
                
                self.logger.info("Task updated via enhanced service", task_id=task_id, via_mcp=True)
                return result
            
            else:
                result = self.clickup_adapter.update_task(task_id, task_data)
                
                if use_outbox:
                    self.outbox_manager.enqueue(
                        operation_type="update_task",
                        endpoint=f"clickup/tasks/{task_id}",
                        request=task_data,
                        provider="clickup"
                    )
                
                self.logger.info("Task updated via adapter fallback", task_id=task_id, via_mcp=False)
                return result
                
        except Exception as e:
            self.logger.error("Task update failed", task_id=task_id, error=str(e))
            raise
    
    async def list_tasks(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List tasks using enhanced capabilities when available"""
        try:
            if self.mcp_bridge:
                result = await self.mcp_bridge.list_tasks(filters)
                self.logger.debug("Tasks listed via MCP", count=len(result))
                return result
            else:
                # Convert filters to adapter format
                status_filter = filters.get("status_filter") if filters else None
                assignee_filter = filters.get("assignee_filter") if filters else None
                
                result = self.clickup_adapter.list_tasks(status_filter, assignee_filter)
                
                # Normalize adapter result
                if isinstance(result, dict) and "tasks" in result:
                    tasks = result["tasks"]
                else:
                    tasks = result if isinstance(result, list) else []
                
                self.logger.debug("Tasks listed via adapter", count=len(tasks))
                return tasks
                
        except Exception as e:
            self.logger.error("Task listing failed", error=str(e))
            raise
    
    async def search_tasks(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search tasks using AI-enhanced capabilities (MCP only feature)
        
        Args:
            query: Search query string
            filters: Additional search filters
            
        Returns:
            List of matching tasks
            
        Raises:
            MCPBridgeError: If MCP is not available
        """
        if not self.mcp_bridge:
            raise MCPBridgeError("Search functionality requires MCP server integration")
        
        try:
            result = await self.mcp_bridge.search_tasks(query, filters)
            self.logger.info("Tasks searched via MCP", query=query, count=len(result))
            return result
            
        except Exception as e:
            self.logger.error("Task search failed", query=query, error=str(e))
            raise
    
    async def get_task_insights(self, task_id: str) -> Dict[str, Any]:
        """
        Get AI-powered insights about a task (MCP only feature)
        
        Returns task analytics, time tracking, comments, and related tasks
        """
        if not self.mcp_bridge:
            raise MCPBridgeError("Task insights require MCP server integration")
        
        insights = {}
        
        try:
            # Get basic task info
            task = await self.mcp_bridge.get_task(task_id)
            insights["task"] = task
            
            # Get time tracking data if available
            try:
                time_data = await self.mcp_bridge._mcp_request("get_task_time_tracked", {"task_id": task_id})
                insights["time_tracking"] = time_data
            except Exception:
                insights["time_tracking"] = None
            
            # Get comments if available
            try:
                comments = await self.mcp_bridge._mcp_request("get_task_comments", {"task_id": task_id})
                insights["comments"] = comments
            except Exception:
                insights["comments"] = []
            
            # Get task members if available
            try:
                members = await self.mcp_bridge._mcp_request("get_task_members", {"task_id": task_id})
                insights["members"] = members
            except Exception:
                insights["members"] = []
            
            self.logger.info("Task insights generated", task_id=task_id)
            return insights
            
        except Exception as e:
            self.logger.error("Task insights generation failed", task_id=task_id, error=str(e))
            raise
    
    async def bulk_update_tasks(self, updates: List[Dict[str, Any]], use_outbox: bool = True) -> List[Dict[str, Any]]:
        """
        Perform bulk task updates with enhanced error handling
        
        Args:
            updates: List of {"task_id": str, "data": dict} updates
            use_outbox: Whether to use outbox pattern
            
        Returns:
            List of update results
        """
        results = []
        errors = []
        
        for update in updates:
            try:
                task_id = update["task_id"]
                data = update["data"]
                
                result = await self.update_task(task_id, data, use_outbox)
                results.append({"task_id": task_id, "success": True, "data": result})
                
            except Exception as e:
                error_info = {"task_id": update.get("task_id"), "success": False, "error": str(e)}
                errors.append(error_info)
                results.append(error_info)
        
        if errors:
            self.logger.warning("Bulk update completed with errors", 
                              total=len(updates), errors=len(errors))
        else:
            self.logger.info("Bulk update completed successfully", total=len(updates))
        
        return results
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get status of enhanced task service components"""
        status = {
            "adapter_available": self.clickup_adapter is not None,
            "outbox_available": self.outbox_manager is not None,
            "mcp_available": self.mcp_bridge is not None
        }
        
        if self.mcp_bridge:
            try:
                mcp_status = await self.mcp_bridge.get_server_status()
                status["mcp_status"] = mcp_status
            except Exception as e:
                status["mcp_status"] = {"error": str(e)}
        
        return status