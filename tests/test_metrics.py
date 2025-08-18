from fastapi.testclient import TestClient
from app.api import app

def test_healthz_and_metrics():
    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

    m = client.get("/metrics")
    assert m.status_code == 200
    assert m.headers.get("content-type", "").startswith("text/plain")
