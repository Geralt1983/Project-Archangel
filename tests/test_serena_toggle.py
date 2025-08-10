import os
from app.triage_serena import triage_with_serena

def test_fallback_when_disabled(monkeypatch):
    monkeypatch.setenv("SERENA_ENABLED","false")
    t = triage_with_serena({"title":"hello","client":"acme"}, "clickup")
    assert "serena_meta" not in t
    assert "score" in t