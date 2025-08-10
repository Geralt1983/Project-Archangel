import os, hmac, hashlib, base64, httpx
from .base import ProviderAdapter

TD_API = "https://api.todoist.com/rest/v2"

class TodoistAdapter(ProviderAdapter):
    name = "todoist"

    def __init__(self, token: str, webhook_secret: str, project_id: str):
        self.token = token
        self.webhook_secret = webhook_secret
        self.project_id = project_id
        self.client = httpx.Client(timeout=20.0, headers={
            "Authorization": f"Bearer {token}"
        })

    def create_task(self, task):
        payload = {"content": task["title"], "description": task.get("description",""), "project_id": self.project_id}
        if task.get("deadline"):
            payload["due_datetime"] = task["deadline"]
        r = self.client.post(f"{TD_API}/tasks", json=payload)
        r.raise_for_status()
        return r.json()

    def create_subtasks(self, parent_external_id, subtasks):
        out = []
        for st in subtasks:
            r = self.client.post(f"{TD_API}/tasks", json={
                "content": st["title"], "parent_id": parent_external_id, "project_id": self.project_id
            })
            r.raise_for_status()
            out.append(r.json())
        return out

    def add_checklist(self, external_id, items):
        # Represent checklist as additional subtasks
        for it in items:
            self.client.post(f"{TD_API}/tasks", json={
                "content": it, "parent_id": external_id, "project_id": self.project_id
            })

    def update_status(self, external_id, status):
        # You can close a task when done
        if status == "done":
            self.client.post(f"{TD_API}/tasks/{external_id}/close")

    def verify_webhook(self, headers, raw_body):
        sig = headers.get("x-todoist-hmac-sha256","")
        mac = hmac.new(self.webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, mac)