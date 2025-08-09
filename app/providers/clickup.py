import hmac
import hashlib
import time
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from .base import ProviderAdapter
from ..models import Task, Subtask

CLICKUP_API = "https://api.clickup.com/api/v2"

class ClickUpAdapter(ProviderAdapter):
    """ClickUp provider adapter."""
    
    name = "clickup"
    
    def __init__(self, token: str, team_id: str, list_id: str, webhook_secret: str):
        self.token = token
        self.team_id = team_id
        self.list_id = list_id
        self.webhook_secret = webhook_secret
        self.client = httpx.Client(
            timeout=20.0,
            headers={"Authorization": self.token, "Content-Type": "application/json"}
        )
    
    def create_task(self, task: Task) -> Dict[str, Any]:
        """Create a task in ClickUp."""
        payload = {
            "name": task.title,
            "description": task.description or "",
            "tags": task.labels,
            "priority": self._map_importance_to_priority(task.importance),
        }
        
        if task.deadline:
            payload["due_date"] = self._datetime_to_ms(task.deadline)
        
        if task.effort_hours:
            # ClickUp time estimates are in milliseconds
            payload["time_estimate"] = int(task.effort_hours * 3600 * 1000)
        
        response = self._make_request("POST", f"/list/{self.list_id}/task", payload)
        return response
    
    def create_subtasks(self, parent_external_id: str, subtasks: List[Subtask]) -> List[Dict[str, Any]]:
        """Create subtasks under a parent task."""
        created = []
        
        for subtask in subtasks:
            payload = {
                "name": subtask.title,
                "parent": parent_external_id
            }
            
            if subtask.effort_hours:
                payload["time_estimate"] = int(subtask.effort_hours * 3600 * 1000)
            
            if subtask.deadline:
                payload["due_date"] = self._datetime_to_ms(subtask.deadline)
            
            try:
                response = self._make_request("POST", f"/list/{self.list_id}/task", payload)
                created.append(response)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    self._handle_rate_limit(e.response)
                    response = self._make_request("POST", f"/list/{self.list_id}/task", payload)
                    created.append(response)
                else:
                    raise
        
        return created
    
    def add_checklist(self, external_id: str, items: List[str]) -> None:
        """Add checklist to a task."""
        if not items:
            return
            
        # Create a checklist
        checklist_payload = {"name": "Task Checklist"}
        checklist_response = self._make_request(
            "POST", f"/task/{external_id}/checklist", checklist_payload
        )
        checklist_id = checklist_response["checklist"]["id"]
        
        # Add items to the checklist
        for item in items:
            item_payload = {"name": item}
            self._make_request(
                "POST", f"/checklist/{checklist_id}/checklist_item", item_payload
            )
    
    def update_status(self, external_id: str, status: str) -> None:
        """Update task status."""
        payload = {"status": self._map_status_to_clickup(status)}
        self._make_request("PUT", f"/task/{external_id}", payload)
    
    def get_task(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Get task details from ClickUp."""
        try:
            return self._make_request("GET", f"/task/{external_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    def verify_webhook(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        """Verify ClickUp webhook signature."""
        signature = headers.get("x-signature", "")
        if not signature:
            return False
        
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            raw_body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to ClickUp API with error handling."""
        url = f"{CLICKUP_API}{endpoint}"
        
        if method == "GET":
            response = self.client.get(url)
        elif method == "POST":
            response = self.client.post(url, json=data)
        elif method == "PUT":
            response = self.client.put(url, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    def _handle_rate_limit(self, response: httpx.Response) -> None:
        """Handle rate limiting with exponential backoff."""
        retry_after = float(response.headers.get("Retry-After", "1"))
        # Cap wait time at 5 seconds
        wait_time = min(5.0, retry_after)
        time.sleep(wait_time)
    
    def _datetime_to_ms(self, dt: datetime) -> int:
        """Convert datetime to epoch milliseconds."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    
    def _map_importance_to_priority(self, importance: int) -> int:
        """Map importance (1-5) to ClickUp priority (1-4)."""
        # ClickUp: 1=Urgent, 2=High, 3=Normal, 4=Low
        mapping = {5: 1, 4: 2, 3: 3, 2: 4, 1: 4}
        return mapping.get(importance, 3)
    
    def _map_status_to_clickup(self, status: str) -> str:
        """Map internal status to ClickUp status."""
        mapping = {
            "new": "Open",
            "triaged": "to do", 
            "in_progress": "in progress",
            "blocked": "blocked",
            "done": "complete"
        }
        return mapping.get(status, "Open")