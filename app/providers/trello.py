import hmac
import hashlib
import httpx
from .base import ProviderAdapter
from app.utils.idempotency import make_idempotency_key

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
        # Add idempotency header (provider may ignore; safe by default)
        idem = make_idempotency_key(self.name, f"{TRELLO_API}/cards", {"idList": self.list_id, "name": task["title"]})
        r = self.client.post(f"{TRELLO_API}/cards", data=payload, headers={"Idempotency-Key": idem})
        r.raise_for_status()
        return r.json()

    def create_subtasks(self, parent_external_id, subtasks):
        # As checklist items on the parent card
        idem_ck = make_idempotency_key(self.name, f"{TRELLO_API}/checklists", {"idCard": parent_external_id, "name": "Subtasks"})
        ck = self.client.post(f"{TRELLO_API}/checklists", data={"idCard": parent_external_id, "name": "Subtasks"}, headers={"Idempotency-Key": idem_ck})
        ck.raise_for_status()
        cid = ck.json()["id"]
        created = []
        for st in subtasks:
            idem_it = make_idempotency_key(self.name, f"{TRELLO_API}/checklists/{cid}/checkItems", {"name": st["title"]})
            r = self.client.post(f"{TRELLO_API}/checklists/{cid}/checkItems", data={"name": st["title"]}, headers={"Idempotency-Key": idem_it})
            r.raise_for_status()
            created.append(r.json())
        return created

    def add_checklist(self, external_id, items):
        idem_ck = make_idempotency_key(self.name, f"{TRELLO_API}/checklists", {"idCard": external_id, "name": "Checklist"})
        ck = self.client.post(f"{TRELLO_API}/checklists", data={"idCard": external_id, "name": "Checklist"}, headers={"Idempotency-Key": idem_ck})
        ck.raise_for_status()
        cid = ck.json()["id"]
        for it in items:
            idem_it = make_idempotency_key(self.name, f"{TRELLO_API}/checklists/{cid}/checkItems", {"name": it})
            self.client.post(f"{TRELLO_API}/checklists/{cid}/checkItems", data={"name": it}, headers={"Idempotency-Key": idem_it})

    def update_status(self, external_id, status):
        # Map to labels or card fields as you prefer. No op here.
        pass

    def verify_webhook(self, headers, raw_body):
        sig = headers.get("x-trello-webhook")
        if not sig:
            return False
        mac = hmac.new(self.webhook_secret.encode(), raw_body, hashlib.sha1).hexdigest()
        return hmac.compare_digest(sig, mac)
