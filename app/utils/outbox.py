from __future__ import annotations
import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional, List, Dict, Any


def _now():
    return datetime.now(timezone.utc)


def _canon_json(d: Dict[str, Any]) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def make_idempotency_key(operation_type: str, endpoint: str, request: Dict[str, Any]) -> str:
    base = f"{operation_type}|{endpoint}|{_canon_json(request)}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


@dataclass
class OutboxOperation:
    id: int
    operation_type: str
    endpoint: str
    request: Dict[str, Any]
    headers: Dict[str, Any]
    idempotency_key: str
    status: str
    retry_count: int
    next_retry_at: Optional[datetime]
    error: Optional[str]


class OutboxManager:
    """
    Postgres-backed outbox with exactly-once intent via idempotency keys.
    conn_factory: callable that returns a live psycopg2 connection
    """
    def __init__(self, conn_factory: Callable):
        self.conn_factory = conn_factory

    # enqueue before making any external call
    def enqueue(self, operation_type: str, endpoint: str, request: Dict[str, Any],
                headers: Optional[Dict[str, Any]] = None, idempotency_key: Optional[str] = None) -> str:
        conn = self.conn_factory()
        headers = headers or {}
        idem = idempotency_key or make_idempotency_key(operation_type, endpoint, request)
        with conn.cursor() as c:
            c.execute("""
            insert into outbox(operation_type, endpoint, request, headers, idempotency_key, status)
            values(%s,%s,%s::jsonb,%s::jsonb,%s,'pending')
            on conflict (idempotency_key) do nothing
            """, (operation_type, endpoint, json.dumps(request), json.dumps(headers), idem))
        return idem

    def mark_inflight(self, ob_id: int):
        conn = self.conn_factory()
        with conn.cursor() as c:
            c.execute("update outbox set status='inflight', updated_at=now() where id=%s", (ob_id,))

    def mark_delivered(self, ob_id: int):
        conn = self.conn_factory()
        with conn.cursor() as c:
            c.execute("update outbox set status='delivered', updated_at=now() where id=%s", (ob_id,))

    def mark_failed(self, ob_id: int, retry_in_seconds: int, error: str):
        conn = self.conn_factory()
        with conn.cursor() as c:
            next_at = _now() + timedelta(seconds=max(1, retry_in_seconds))
            c.execute("""
            update outbox set status='failed', retry_count=retry_count+1, next_retry_at=%s, error=%s, updated_at=now()
            where id=%s
            """, (next_at, error[:2000], ob_id))

    def dead_letter(self, ob_id: int, error: str):
        conn = self.conn_factory()
        with conn.cursor() as c:
            c.execute("update outbox set status='dead', error=%s, updated_at=now() where id=%s", (error[:2000], ob_id))

    def pick_batch(self, limit: int = 10) -> List[OutboxOperation]:
        """Select ready items with row locking to avoid contention across workers."""
        conn = self.conn_factory()
        with conn.cursor() as c:
            c.execute("""
            select id, operation_type, endpoint, request, headers, idempotency_key, status, retry_count, next_retry_at, error
            from outbox
            where (status='pending' or (status='failed' and (next_retry_at is null or next_retry_at <= now())))
            order by created_at asc
            for update skip locked
            limit %s
            """, (limit,))
            rows = c.fetchall()
            ops: List[OutboxOperation] = []
            for r in rows:
                ops.append(OutboxOperation(
                    id=r[0],
                    operation_type=r[1],
                    endpoint=r[2],
                    request=r[3],
                    headers=r[4],
                    idempotency_key=r[5],
                    status=r[6],
                    retry_count=r[7],
                    next_retry_at=r[8],
                    error=r[9],
                ))
            return ops

    def get_stats(self) -> Dict[str, int]:
        conn = self.conn_factory()
        with conn.cursor() as c:
            c.execute("""
            select status, count(*) from outbox group by status
            """)
            out: Dict[str, int] = {}
            for status, count in c.fetchall():
                out[status] = int(count)
            return out