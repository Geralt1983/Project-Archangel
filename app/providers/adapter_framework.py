"""
Provider Adapter Framework - Unified interface for task management providers
Supports webhook and polling-based providers with standardized orchestration integration.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, AsyncIterator
from dataclasses import dataclass, asdict, field
from enum import Enum

class ProviderType(Enum):
    WEBHOOK = "webhook"
    POLLING = "polling"
    HYBRID = "hybrid"

class TaskOperation(Enum):
    CREATE = "create"
    UPDATE = "update" 
    DELETE = "delete"
    COMPLETE = "complete"
    ASSIGN = "assign"

@dataclass
class ProviderCapabilities:
    """Defines what operations a provider supports"""
    can_create: bool = True
    can_update: bool = True
    can_delete: bool = True
    can_assign: bool = True
    can_add_subtasks: bool = True
    can_add_checklist: bool = True
    can_set_priority: bool = True
    can_set_deadline: bool = True
    supports_webhooks: bool = False
    supports_polling: bool = True
    supports_real_time: bool = False
    max_batch_size: int = 50
    rate_limit_per_minute: int = 100

@dataclass
class StandardTask:
    """Standardized task format across all providers"""
    id: str
    external_id: Optional[str]
    title: str
    description: str
    status: str
    priority: Optional[str]
    assignee: Optional[str]
    client: str
    provider: str
    created_at: datetime
    updated_at: Optional[datetime]
    deadline: Optional[datetime]
    effort_hours: float
    labels: List[str] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)
    checklist: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert datetimes to ISO strings
        for field in ['created_at', 'updated_at', 'deadline']:
            if result[field]:
                result[field] = result[field].isoformat() if isinstance(result[field], datetime) else result[field]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StandardTask':
        """Create from dictionary with datetime parsing"""
        # Parse datetime fields
        for field in ['created_at', 'updated_at', 'deadline']:
            if data.get(field):
                if isinstance(data[field], str):
                    data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
        
        return cls(**data)

@dataclass
class ProviderEvent:
    """Standardized event from providers"""
    event_id: str
    provider: str
    event_type: TaskOperation
    task_id: str
    task_data: StandardTask
    timestamp: datetime
    raw_payload: Dict[str, Any]
    
class ProviderAdapter(ABC):
    """Abstract base class for all provider adapters"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"provider.{name}")
        self._event_handlers: List[Callable[[ProviderEvent], None]] = []
        self._rate_limiter = RateLimiter(self.capabilities.rate_limit_per_minute)
        
    @property 
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities"""
        pass
        
    @property
    @abstractmethod 
    def provider_type(self) -> ProviderType:
        """Return provider type (webhook, polling, etc.)"""
        pass
        
    # Core CRUD operations
    @abstractmethod
    async def create_task(self, task: StandardTask) -> StandardTask:
        """Create task in provider system"""
        pass
        
    @abstractmethod
    async def get_task(self, external_id: str) -> Optional[StandardTask]:
        """Get task by external ID"""
        pass
        
    @abstractmethod
    async def update_task(self, external_id: str, updates: Dict[str, Any]) -> StandardTask:
        """Update existing task"""
        pass
        
    @abstractmethod
    async def delete_task(self, external_id: str) -> bool:
        """Delete task"""
        pass
        
    # Batch operations
    async def get_tasks(self, limit: int = 100, offset: int = 0) -> List[StandardTask]:
        """Get multiple tasks (default implementation)"""
        # Default implementation for providers without native batch support
        tasks = []
        # This would be implemented by each provider
        return tasks
        
    async def batch_update(self, updates: List[Dict[str, Any]]) -> List[StandardTask]:
        """Batch update tasks"""
        results = []
        for update in updates[:self.capabilities.max_batch_size]:
            try:
                result = await self.update_task(update['external_id'], update['data'])
                results.append(result)
            except Exception as e:
                self.logger.error(f"Batch update failed for {update['external_id']}: {e}")
        return results
        
    # Webhook support
    async def verify_webhook(self, headers: Dict[str, str], body: bytes) -> bool:
        """Verify webhook signature"""
        if not self.capabilities.supports_webhooks:
            return False
        return self._verify_webhook_signature(headers, body)
        
    @abstractmethod
    def _verify_webhook_signature(self, headers: Dict[str, str], body: bytes) -> bool:
        """Provider-specific webhook verification"""
        pass
        
    async def process_webhook(self, headers: Dict[str, str], payload: Dict[str, Any]) -> Optional[ProviderEvent]:
        """Process incoming webhook"""
        try:
            event = self._parse_webhook_event(headers, payload)
            if event:
                await self._dispatch_event(event)
            return event
        except Exception as e:
            self.logger.error(f"Webhook processing failed: {e}")
            return None
            
    @abstractmethod
    def _parse_webhook_event(self, headers: Dict[str, str], payload: Dict[str, Any]) -> Optional[ProviderEvent]:
        """Parse provider-specific webhook payload"""
        pass
        
    # Polling support
    async def poll_for_updates(self, since: Optional[datetime] = None) -> AsyncIterator[ProviderEvent]:
        """Poll for task updates"""
        if not self.capabilities.supports_polling:
            return
            
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=1)
            
        async for event in self._poll_implementation(since):
            await self._dispatch_event(event)
            yield event
            
    @abstractmethod
    async def _poll_implementation(self, since: datetime) -> AsyncIterator[ProviderEvent]:
        """Provider-specific polling implementation"""
        pass
        
    # Event handling
    def add_event_handler(self, handler: Callable[[ProviderEvent], None]):
        """Add event handler for provider events"""
        self._event_handlers.append(handler)
        
    async def _dispatch_event(self, event: ProviderEvent):
        """Dispatch event to all handlers"""
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                self.logger.error(f"Event handler failed: {e}")
                
    # Utility methods
    async def test_connection(self) -> Dict[str, Any]:
        """Test provider connection and return status"""
        try:
            # Try a simple operation
            tasks = await self.get_tasks(limit=1)
            return {
                'status': 'connected',
                'provider': self.name,
                'capabilities': asdict(self.capabilities),
                'test_task_count': len(tasks)
            }
        except Exception as e:
            return {
                'status': 'error',
                'provider': self.name,
                'error': str(e)
            }
            
    async def get_provider_stats(self) -> Dict[str, Any]:
        """Get provider statistics"""
        try:
            tasks = await self.get_tasks(limit=1000)  # Sample
            return {
                'provider': self.name,
                'total_tasks': len(tasks),
                'by_status': self._count_by_status(tasks),
                'by_client': self._count_by_client(tasks),
                'rate_limit_remaining': self._rate_limiter.remaining_quota()
            }
        except Exception as e:
            return {
                'provider': self.name,
                'error': str(e)
            }
            
    def _count_by_status(self, tasks: List[StandardTask]) -> Dict[str, int]:
        """Count tasks by status"""
        counts = {}
        for task in tasks:
            counts[task.status] = counts.get(task.status, 0) + 1
        return counts
        
    def _count_by_client(self, tasks: List[StandardTask]) -> Dict[str, int]:
        """Count tasks by client"""
        counts = {}
        for task in tasks:
            counts[task.client] = counts.get(task.client, 0) + 1
        return counts

class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.requests: List[datetime] = []
        
    async def acquire(self):
        """Acquire rate limit slot"""
        now = datetime.now()
        # Clean old requests
        cutoff = now - timedelta(minutes=1)
        self.requests = [req for req in self.requests if req > cutoff]
        
        if len(self.requests) >= self.requests_per_minute:
            # Wait until we can make another request
            oldest = self.requests[0]
            wait_time = 60 - (now - oldest).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                
        self.requests.append(now)
        
    def remaining_quota(self) -> int:
        """Get remaining requests in current minute"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        recent_requests = [req for req in self.requests if req > cutoff]
        return max(0, self.requests_per_minute - len(recent_requests))

class ProviderManager:
    """Manages multiple provider adapters"""
    
    def __init__(self):
        self.providers: Dict[str, ProviderAdapter] = {}
        self.logger = logging.getLogger("provider_manager")
        
    def register_provider(self, adapter: ProviderAdapter):
        """Register a provider adapter"""
        self.providers[adapter.name] = adapter
        self.logger.info(f"Registered provider: {adapter.name}")
        
    def get_provider(self, name: str) -> Optional[ProviderAdapter]:
        """Get provider by name"""
        return self.providers.get(name)
        
    async def get_all_tasks(self) -> List[StandardTask]:
        """Get tasks from all providers"""
        all_tasks = []
        for provider in self.providers.values():
            try:
                tasks = await provider.get_tasks()
                all_tasks.extend(tasks)
            except Exception as e:
                self.logger.error(f"Failed to get tasks from {provider.name}: {e}")
        return all_tasks
        
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all providers"""
        results = {}
        for name, provider in self.providers.items():
            results[name] = await provider.test_connection()
        return results
        
    async def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics from all providers"""
        stats = {}
        for name, provider in self.providers.items():
            stats[name] = await provider.get_provider_stats()
        return {
            'providers': stats,
            'total_providers': len(self.providers),
            'active_providers': len([s for s in stats.values() if s.get('status') != 'error'])
        }

# Enhanced adapter implementations for existing providers
class EnhancedClickUpAdapter(ProviderAdapter):
    """Enhanced ClickUp adapter using the new framework"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("clickup", config)
        self.token = config.get("token", "")
        self.team_id = config.get("team_id", "")
        self.list_id = config.get("list_id", "")
        self.webhook_secret = config.get("webhook_secret", "")
        
    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            can_create=True,
            can_update=True, 
            can_delete=True,
            can_assign=True,
            can_add_subtasks=True,
            can_add_checklist=True,
            can_set_priority=True,
            can_set_deadline=True,
            supports_webhooks=True,
            supports_polling=True,
            max_batch_size=100,
            rate_limit_per_minute=100
        )
        
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.HYBRID
        
    async def create_task(self, task: StandardTask) -> StandardTask:
        """Create task in ClickUp"""
        # Implementation would call ClickUp API
        # For now, return the task with an external ID
        task.external_id = f"cu_{task.id}"
        return task
        
    async def get_task(self, external_id: str) -> Optional[StandardTask]:
        """Get task from ClickUp"""
        # Implementation would call ClickUp API
        return None
        
    async def update_task(self, external_id: str, updates: Dict[str, Any]) -> StandardTask:
        """Update task in ClickUp"""
        # Implementation would call ClickUp API
        pass
        
    async def delete_task(self, external_id: str) -> bool:
        """Delete task in ClickUp"""
        # Implementation would call ClickUp API
        return True
        
    def _verify_webhook_signature(self, headers: Dict[str, str], body: bytes) -> bool:
        """Verify ClickUp webhook signature"""
        import hmac
        import hashlib
        
        signature = headers.get("x-signature", "")
        if not signature or not self.webhook_secret:
            return False
            
        expected = hmac.new(
            self.webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
        
    def _parse_webhook_event(self, headers: Dict[str, str], payload: Dict[str, Any]) -> Optional[ProviderEvent]:
        """Parse ClickUp webhook event"""
        event_type = payload.get("event")
        task_data = payload.get("task", {})
        
        if not event_type or not task_data:
            return None
            
        # Convert ClickUp task to StandardTask
        standard_task = self._convert_clickup_task(task_data)
        
        # Map ClickUp event types to standard operations
        operation_map = {
            "taskCreated": TaskOperation.CREATE,
            "taskUpdated": TaskOperation.UPDATE,
            "taskDeleted": TaskOperation.DELETE,
            "taskStatusUpdated": TaskOperation.UPDATE
        }
        
        operation = operation_map.get(event_type, TaskOperation.UPDATE)
        
        return ProviderEvent(
            event_id=payload.get("event_id", ""),
            provider=self.name,
            event_type=operation,
            task_id=standard_task.id,
            task_data=standard_task,
            timestamp=datetime.now(timezone.utc),
            raw_payload=payload
        )
        
    def _convert_clickup_task(self, clickup_task: Dict[str, Any]) -> StandardTask:
        """Convert ClickUp task format to StandardTask"""
        return StandardTask(
            id=clickup_task.get("id", ""),
            external_id=clickup_task.get("id", ""),
            title=clickup_task.get("name", ""),
            description=clickup_task.get("description", ""),
            status=clickup_task.get("status", {}).get("status", "open"),
            priority=clickup_task.get("priority", {}).get("priority") if clickup_task.get("priority") else None,
            assignee=clickup_task.get("assignees", [{}])[0].get("username") if clickup_task.get("assignees") else None,
            client="",  # Would be extracted from custom fields
            provider=self.name,
            created_at=datetime.fromtimestamp(int(clickup_task.get("date_created", 0)) / 1000, timezone.utc),
            updated_at=datetime.fromtimestamp(int(clickup_task.get("date_updated", 0)) / 1000, timezone.utc) if clickup_task.get("date_updated") else None,
            deadline=datetime.fromtimestamp(int(clickup_task.get("due_date", 0)) / 1000, timezone.utc) if clickup_task.get("due_date") else None,
            effort_hours=1.0,  # Would be extracted from custom fields
            labels=clickup_task.get("tags", []),
            subtasks=[],  # Would be populated from subtasks
            checklist=[],  # Would be populated from checklists
            metadata=clickup_task
        )
        
    async def _poll_implementation(self, since: datetime) -> AsyncIterator[ProviderEvent]:
        """Poll ClickUp for task updates"""
        # Implementation would poll ClickUp API for tasks updated since timestamp
        # This is a placeholder
        return
        yield  # This makes it a generator

# Factory for creating provider adapters
def create_provider_adapter(provider_name: str, config: Dict[str, Any]) -> Optional[ProviderAdapter]:
    """Factory function to create provider adapters"""
    adapters = {
        "clickup": EnhancedClickUpAdapter,
        # Add other providers as they are implemented
    }
    
    adapter_class = adapters.get(provider_name)
    if adapter_class:
        return adapter_class(config)
    return None