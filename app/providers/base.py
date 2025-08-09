from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models import Task, Subtask

class ProviderAdapter(ABC):
    """Abstract base class for project management provider adapters."""
    
    name: str
    
    @abstractmethod
    def create_task(self, task: Task) -> Dict[str, Any]:
        """Create a task in the provider and return the created task data."""
        raise NotImplementedError
    
    @abstractmethod
    def create_subtasks(self, parent_external_id: str, subtasks: List[Subtask]) -> List[Dict[str, Any]]:
        """Create subtasks under a parent task."""
        raise NotImplementedError
    
    @abstractmethod
    def add_checklist(self, external_id: str, items: List[str]) -> None:
        """Add checklist items to a task."""
        raise NotImplementedError
    
    @abstractmethod
    def update_status(self, external_id: str, status: str) -> None:
        """Update task status."""
        raise NotImplementedError
    
    @abstractmethod
    def get_task(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task details from provider."""
        raise NotImplementedError
    
    @abstractmethod
    def verify_webhook(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        """Verify webhook signature."""
        raise NotImplementedError
    
    def supports_subtasks(self) -> bool:
        """Return True if provider supports native subtasks."""
        return True
    
    def supports_checklists(self) -> bool:
        """Return True if provider supports native checklists."""
        return True