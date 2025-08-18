import hashlib
import json
from typing import Any, Dict, Optional


def _stable_json(d: Dict[str, Any]) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def make_idempotency_key(provider: Optional[str], endpoint: str, payload: Dict[str, Any]) -> str:
    provider_part = (provider or "").strip()
    base = f"{provider_part}|{endpoint}|{_stable_json(payload)}" if provider_part else f"{endpoint}|{_stable_json(payload)}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
