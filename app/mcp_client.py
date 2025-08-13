import os
import httpx

BASE = os.getenv("SERENA_BASE_URL", "")
KEY = os.getenv("SERENA_API_KEY", "")
TO = float(os.getenv("SERENA_TIMEOUT_SECONDS","20"))

def _client():
    return httpx.Client(base_url=BASE, timeout=TO, headers={"Authorization": f"Bearer {KEY}"} )

def triage_call(envelope: dict) -> dict | None:
    if not BASE: return None
    with _client() as c:
        r = c.post("/v1/triage", json=envelope)
        if r.status_code == 200:
            return r.json()
        return None

def rebalance_call(payload: dict) -> dict | None:
    if not BASE: return None
    with _client() as c:
        r = c.post("/v1/rebalance", json=payload)
        if r.status_code == 200:
            return r.json()
        return None