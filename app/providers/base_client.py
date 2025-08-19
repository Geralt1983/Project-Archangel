from __future__ import annotations
import httpx
from typing import Any, Dict, Optional
from app.utils.retry import default_httpx_retryable, retry
from app.utils.idempotency import make_idempotency_key


class BaseHTTPClient:
    def __init__(self, provider: str, default_headers: Optional[Dict[str, str]] = None, timeout: float = 20.0):
        self.provider = provider
        self.client = httpx.Client(timeout=timeout, headers=default_headers or {})
        self.retry_if = default_httpx_retryable()

    def request(self, method: str, url: str, *, json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, idempotent: bool = False) -> httpx.Response:
        hdrs = headers.copy() if headers else {}
        if idempotent and json is not None:
            hdrs.setdefault("Idempotency-Key", make_idempotency_key(self.provider, url, json))

        def _do() -> httpx.Response:
            res = self.client.request(method, url, json=json, headers=hdrs)
            # Raise for non-2xx; retry_if will gate which errors retry
            res.raise_for_status()
            return res

        return retry(_do, max_tries=5, retry_if=self.retry_if, max_elapsed=60.0)
