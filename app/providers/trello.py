import hmac
import hashlib
import httpx
from .base import ProviderAdapter

TRELLO_API = "https://api.trello.com/1"

class TrelloAdapter(ProviderAdapter):
    name = "trello"

    def __init__(self, key: str, token: str, webhook_secret: str, list_id: str):
        self.key = key
        self.token = token
        self.webhook_secret = webhook_secret
        self.list_id = list_id
        self.client = httpx.Client(timeout=20.0, params={"key": key, "token": token})

    def create_task(self, task):
        payload = {"idList": self.list_id, "name": task["title"], "desc": task.get("description","")}
        r = self.client.post(f"{TRELLO_API}/cards", data=payload)
        r.raise_for_status()
        return r.json()

    def create_subtasks(self, parent_external_id, subtasks):
        # As checklist items on the parent card
        ck = self.client.post(f"{TRELLO_API}/checklists", data={"idCard": parent_external_id, "name": "Subtasks"})
        ck.raise_for_status()
        cid = ck.json()["id"]
        created = []
        for st in subtasks:
            r = self.client.post(f"{TRELLO_API}/checklists/{cid}/checkItems", data={"name": st["title"]})
            r.raise_for_status()
            created.append(r.json())
        return created

    def add_checklist(self, external_id, items):
        ck = self.client.post(f"{TRELLO_API}/checklists", data={"idCard": external_id, "name": "Checklist"})
        ck.raise_for_status()
        cid = ck.json()["id"]
        for it in items:
            self.client.post(f"{TRELLO_API}/checklists/{cid}/checkItems", data={"name": it})

    def update_status(self, external_id, status):
        # Map to labels or card fields as you prefer. No op here.
        pass

    def verify_webhook(self, headers, raw_body):
        sig = headers.get("x-trello-webhook")
        if not sig:
            return False
        mac = hmac.new(self.webhook_secret.encode(), raw_body, hashlib.sha1).hexdigest()
        return hmac.compare_digest(sig, mac)
