import os, hmac, hashlib, httpx
from datetime import datetime, timezone
from .base import ProviderAdapter

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

    def create_task(self, task):
        payload = {
            "name": task["title"],
            "description": task.get("description", ""),
            "due_date": _to_epoch_ms(task.get("deadline")),
            "tags": task.get("labels", []),
        }
        r = self.client.post(f"{CLICKUP_API}/list/{self.list_id}/task", json=payload)
        r.raise_for_status()
        return r.json()

    def create_subtasks(self, parent_external_id, subtasks):
        out = []
        for st in subtasks:
            payload = {
                "name": st["title"],
                "parent": parent_external_id
            }
            r = self.client.post(f"{CLICKUP_API}/list/{self.list_id}/task", json=payload)
            if r.status_code == 429:
                self._backoff(r)
                r = self.client.post(f"{CLICKUP_API}/list/{self.list_id}/task", json=payload)
            r.raise_for_status()
            out.append(r.json())
        return out

    def add_checklist(self, external_id, items):
        # ClickUp supports checklists on tasks
        for it in items:
            # Create a checklist with a single item name
            # If you prefer one checklist with many items, first create checklist then items
            self.client.post(f"{CLICKUP_API}/task/{external_id}/checklist", json={"name": it})

    def update_status(self, external_id, status):
        self.client.put(f"{CLICKUP_API}/task/{external_id}", json={"status": status})

    def verify_webhook(self, headers, raw_body):
        # ClickUp sends X Signature header with HMAC SHA256 hex of raw body using webhook secret
        # https docs: Webhook signature and Webhooks pages
        sig = headers.get("x-signature") or ""
        mac = hmac.new(self.webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, mac)

    def create_webhook(self, callback_url: str):
        payload = {
            "endpoint": callback_url,
            "events": ["taskCreated", "taskUpdated", "taskDeleted"],
            "secret": self.webhook_secret
        }
        r = self.client.post(f"{CLICKUP_API}/team/{self.team_id}/webhook", json=payload)
        r.raise_for_status()
        return r.json()

    def _backoff(self, resp):
        import time, random
        retry_after = float(resp.headers.get("Retry-After", "1"))
        time.sleep(min(5.0, retry_after) + random.random())