import hmac
import hashlib
import base64
from app.providers.todoist import TodoistAdapter

class DummyResponse:
    def __init__(self, json_data=None):
        self._json = json_data or {}
    def raise_for_status(self):
        pass
    def json(self):
        return self._json

class DummyClient:
    def __init__(self):
        self.last_request = None
    def post(self, url, json):
        self.last_request = {"url": url, "json": json}
        return DummyResponse({"id": "1"})


def test_create_task_includes_deadline_and_priority():
    adapter = TodoistAdapter("token", "secret", "proj")
    adapter.client = DummyClient()
    task = {
        "title": "Test",
        "description": "Desc",
        "deadline": "2025-01-01T00:00:00Z",
        "priority": 4,
    }
    adapter.create_task(task)
    sent = adapter.client.last_request["json"]
    assert sent["due_datetime"] == "2025-01-01T00:00:00Z"
    assert sent["priority"] == 4


def test_verify_webhook_uses_base64():
    secret = "secret"
    body = b"{}"
    adapter = TodoistAdapter("token", secret, "proj")
    sig = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    assert adapter.verify_webhook({"x-todoist-hmac-sha256": sig}, body)
    assert not adapter.verify_webhook({"x-todoist-hmac-sha256": "wrong"}, body)
