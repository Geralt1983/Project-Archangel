import hmac
import hashlib
import httpx
from datetime import datetime, timezone
from .base import ProviderAdapter
from ..utils.retry import retry_with_backoff, RetryConfig, RateLimitError, ServerError
from app.utils.idempotency import make_idempotency_key

CLICKUP_API = "https://api.clickup.com/api/v2"

def _to_epoch_ms(iso: str | None) -> int | None:
    if not iso:
        return None
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)

class ClickUpAdapter(ProviderAdapter):
    name = "clickup"

    def __init__(self, token: str, team_id: str, list_id: str, webhook_secret: str):
        self.token = token
        self.team_id = team_id
        self.list_id = list_id
        self.webhook_secret = webhook_secret
        self.client = httpx.Client(timeout=20.0, headers={"Authorization": token})
        
        # Enhanced retry configuration for ClickUp
        self.retry_config = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=60.0,
            jitter=True,
            retryable_exceptions=(RateLimitError, ServerError, httpx.RequestError, httpx.TimeoutException)
        )

    @retry_with_backoff()  # Use default config from decorator
    def create_task(self, task):
        payload = {
            "name": task["title"],
            "description": task.get("description", ""),
            "due_date": _to_epoch_ms(task.get("deadline")),
            "tags": task.get("labels", []),
            "priority": self._map_priority(task.get("priority", 3)),
            "assignees": [task.get("assignee")] if task.get("assignee") else []
        }
        r = self._make_request("POST", f"{CLICKUP_API}/list/{self.list_id}/task", json=payload, idempotent=True)
        return r.json()
    
    @retry_with_backoff()
    def get_task(self, external_id: str):
        """Get task by ClickUp task ID"""
        r = self._make_request("GET", f"{CLICKUP_API}/task/{external_id}")
        return r.json()
    
    @retry_with_backoff()
    def update_task(self, external_id: str, task_data: dict):
        """Update existing task"""
        payload = {}
        if "title" in task_data:
            payload["name"] = task_data["title"]
        if "description" in task_data:
            payload["description"] = task_data["description"]
        if "deadline" in task_data:
            payload["due_date"] = _to_epoch_ms(task_data["deadline"])
        if "priority" in task_data:
            payload["priority"] = self._map_priority(task_data["priority"])
        if "status" in task_data:
            payload["status"] = task_data["status"]
        
        r = self._make_request("PUT", f"{CLICKUP_API}/task/{external_id}", json=payload)
        return r.json()
    
    @retry_with_backoff()
    def delete_task(self, external_id: str):
        """Delete/archive task"""
        r = self._make_request("DELETE", f"{CLICKUP_API}/task/{external_id}")
        return r.status_code == 204
    
    @retry_with_backoff()
    def list_tasks(self, status_filter=None, assignee_filter=None):
        """List tasks in the configured list"""
        params = {}
        if status_filter:
            params["statuses[]"] = status_filter
        if assignee_filter:
            params["assignees[]"] = assignee_filter
            
        r = self._make_request("GET", f"{CLICKUP_API}/list/{self.list_id}/task", params=params)
        return r.json()
    
    def _map_priority(self, priority: int) -> int:
        """Map internal priority (1-5) to ClickUp priority (1-4)"""
        # Internal: 1=Low, 2=Normal, 3=Medium, 4=High, 5=Urgent
        # ClickUp: 1=Urgent, 2=High, 3=Normal, 4=Low
        priority_map = {1: 4, 2: 3, 3: 3, 4: 2, 5: 1}
        return priority_map.get(priority, 3)
    
    def _make_request(self, method: str, url: str, *, json: dict | None = None, headers: dict | None = None, idempotent: bool = False, **kwargs):
        """Centralized request method with error handling and optional idempotency header"""
        hdrs = headers.copy() if headers else {}
        if idempotent and json is not None:
            hdrs.setdefault("Idempotency-Key", make_idempotency_key(self.name, url, json))
        
        # Support both new signature and legacy kwargs
        if json is not None or not kwargs:
            response = self.client.request(method, url, json=json, headers=hdrs)
        else:
            response = self.client.request(method, url, headers=hdrs, **kwargs)
        
        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get("retry-after", 60))
            raise RateLimitError(retry_after)
        
        # Handle server errors
        if response.status_code >= 500:
            raise ServerError(response.status_code, response.text)
        
        # Handle client errors (don't retry these)
        response.raise_for_status()
        return response

    @retry_with_backoff()
    def create_subtasks(self, parent_external_id, subtasks):
        out = []
        for st in subtasks:
            payload = {
                "name": st["title"],
                "parent": parent_external_id
            }
            r = self._make_request("POST", f"{CLICKUP_API}/list/{self.list_id}/task", json=payload, idempotent=True)
            out.append(r.json())
        return out

    @retry_with_backoff()
    def add_checklist(self, external_id, items):
        # ClickUp supports checklists on tasks
        for it in items:
            # Create a checklist with a single item name
            # If you prefer one checklist with many items, first create checklist then items
            self._make_request("POST", f"{CLICKUP_API}/task/{external_id}/checklist", json={"name": it}, idempotent=True)

    @retry_with_backoff()
    def update_status(self, external_id, status):
        self._make_request("PUT", f"{CLICKUP_API}/task/{external_id}", json={"status": status})

    def verify_webhook(self, headers, raw_body):
        # ClickUp sends X Signature header with HMAC SHA256 hex of raw body using webhook secret
        # https docs: Webhook signature and Webhooks pages
        sig = headers.get("x-signature") or ""
        mac = hmac.new(self.webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, mac)

    @retry_with_backoff()
    def create_webhook(self, callback_url: str):
        payload = {
            "endpoint": callback_url,
            "events": ["taskCreated", "taskUpdated", "taskDeleted"],
            "secret": self.webhook_secret
        }
        r = self._make_request("POST", f"{CLICKUP_API}/team/{self.team_id}/webhook", json=payload, idempotent=True)
        return r.json()