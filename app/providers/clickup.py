import os, hmac, hashlib, httpx
from datetime import datetime, timezone
from .base import ProviderAdapter
from ..utils.retry import retry_with_backoff, RetryConfig, RateLimitError, ServerError

CLICKUP_API = "https://api.clickup.com/api/v2"

def _to_epoch_ms(iso: str | None) -> int | None:
    if not iso: return None
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
        }
        r = self._make_request("POST", f"{CLICKUP_API}/list/{self.list_id}/task", json=payload)
        return r.json()
    
    def _make_request(self, method: str, url: str, **kwargs):
        """Centralized request method with error handling"""
        response = self.client.request(method, url, **kwargs)
        
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
            r = self._make_request("POST", f"{CLICKUP_API}/list/{self.list_id}/task", json=payload)
            out.append(r.json())
        return out

    @retry_with_backoff()
    def add_checklist(self, external_id, items):
        # ClickUp supports checklists on tasks
        for it in items:
            # Create a checklist with a single item name
            # If you prefer one checklist with many items, first create checklist then items
            self._make_request("POST", f"{CLICKUP_API}/task/{external_id}/checklist", json={"name": it})

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
        r = self._make_request("POST", f"{CLICKUP_API}/team/{self.team_id}/webhook", json=payload)
        return r.json()