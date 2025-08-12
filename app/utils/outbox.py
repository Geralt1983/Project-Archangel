from __future__ import annotations
import json
import hashlib
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional, List, Dict, Any

from app.db_pg import get_db_config


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
    idempotency_key: str
    operation_type: str
    endpoint: str

    # Primary structured request/headers used by the outbox
    request: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, Any] = field(default_factory=dict)

    # Aliases used by some tests/tools (string body, attempts counters, alt timestamps)
    request_body: Optional[str] = None
    attempts: int = 0
    next_attempt: Optional[datetime] = None

    # Canonical fields used by the queue
    status: str = "pending"
    retry_count: int = 0
    next_retry_at: Optional[datetime] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        # If only request_body is provided, try to parse JSON into request
        if not self.request and self.request_body:
            try:
                self.request = json.loads(self.request_body)
            except Exception:
                # keep raw; worker/dispatch can decide how to handle
                self.request = {"_raw": self.request_body}

        # Keep aliases in sync
        if self.attempts and not self.retry_count:
            self.retry_count = self.attempts
        if self.next_attempt and not self.next_retry_at:
            self.next_retry_at = self.next_attempt


class OutboxManager:
    """
    Postgres-backed outbox with exactly-once intent via idempotency keys.
    conn_factory: callable that returns a live psycopg2 connection
    """
    def __init__(self, conn_factory: Callable):
        self.conn_factory = conn_factory
        self._lock = threading.Lock()

    # enqueue before making any external call
    def enqueue(self, operation_type: str, endpoint: str, request: Dict[str, Any],
                headers: Optional[Dict[str, Any]] = None, idempotency_key: Optional[str] = None) -> str:
        _, IS_SQLITE = get_db_config()
        conn = self.conn_factory()
        headers = headers or {}
        idem = idempotency_key or make_idempotency_key(operation_type, endpoint, request)
        c = conn.cursor()
        if IS_SQLITE:
            sql = """
            insert into outbox(operation_type, endpoint, request, headers, idempotency_key, status)
            values(?,?,?,?,?,'pending')
            on conflict (idempotency_key) do nothing
            """
        else:
            sql = """
            insert into outbox(operation_type, endpoint, request, headers, idempotency_key, status)
            values(%s,%s,%s::jsonb,%s::jsonb,%s,'pending')
            on conflict (idempotency_key) do nothing
            """
        c.execute(sql, (operation_type, endpoint, json.dumps(request), json.dumps(headers), idem))
        if IS_SQLITE:
            conn.commit()
        return idem

    def mark_inflight(self, ob_id: int):
        _, IS_SQLITE = get_db_config()
        conn = self.conn_factory()
        c = conn.cursor()
        now_fn = "datetime('now')" if IS_SQLITE else "now()"
        placeholder = "?" if IS_SQLITE else "%s"
        c.execute(f"update outbox set status='inflight', updated_at={now_fn} where id={placeholder}", (ob_id,))
        if IS_SQLITE:
            conn.commit()

    def mark_delivered(self, ob_id: int):
        _, IS_SQLITE = get_db_config()
        conn = self.conn_factory()
        c = conn.cursor()
        now_fn = "datetime('now')" if IS_SQLITE else "now()"
        placeholder = "?" if IS_SQLITE else "%s"
        c.execute(f"update outbox set status='delivered', updated_at={now_fn} where id={placeholder}", (ob_id,))
        if IS_SQLITE:
            conn.commit()

    def mark_failed(self, ob_id: int, retry_in_seconds: int, error: str):
        _, IS_SQLITE = get_db_config()
        conn = self.conn_factory()
        c = conn.cursor()
        s = max(0, int(retry_in_seconds))  # 0 => immediate eligibility
        next_at = _now() + timedelta(seconds=s)

        if IS_SQLITE:
            sql = """
            update outbox
               set status='failed',
                   retry_count=retry_count+1,
                   next_retry_at=?,
                   error=?,
                   updated_at=datetime('now')
             where id=?
            """
        else:
            sql = """
            update outbox
               set status='failed',
                   retry_count=retry_count+1,
                   next_retry_at=%s,
                   error=%s,
                   updated_at=now()
             where id=%s
            """
        params = (next_at, str(error)[:2000], ob_id)
        if IS_SQLITE:
            # for sqlite, must be string
            params = (next_at.strftime('%Y-%m-%d %H:%M:%S'), str(error)[:2000], ob_id)

        c.execute(sql, params)
        if IS_SQLITE:
            conn.commit()

    def dead_letter(self, ob_id: int, error: str):
        _, IS_SQLITE = get_db_config()
        conn = self.conn_factory()
        c = conn.cursor()
        now_fn = "datetime('now')" if IS_SQLITE else "now()"
        placeholder = "?" if IS_SQLITE else "%s"
        c.execute(f"update outbox set status='dead', error={placeholder}, updated_at={now_fn} where id={placeholder}", (error[:2000], ob_id))
        if IS_SQLITE:
            conn.commit()

    def pick_batch(self, limit: int = 10) -> List[OutboxOperation]:
        """Select ready items with row locking to avoid contention across workers."""
        # Note: for sqlite, this is not concurrent. The lock serializes workers.
        with self._lock:
            _, IS_SQLITE = get_db_config()
            conn = self.conn_factory()
            c = conn.cursor()

            if IS_SQLITE:
                sql = """
                select id, operation_type, endpoint, request, headers, idempotency_key, status, retry_count, next_retry_at, error
                from outbox
                where (status='pending' or (status='failed' and (next_retry_at is null or next_retry_at <= datetime('now'))))
            order by created_at asc
            limit ?
            """
            else:
                sql = """
                select id, operation_type, endpoint, request, headers, idempotency_key, status, retry_count, next_retry_at, error
                from outbox
                where (status='pending' or (status='failed' and (next_retry_at is null or next_retry_at <= now())))
                order by created_at asc
                for update skip locked
                limit %s
                """
            c.execute(sql, (limit,))
            rows = c.fetchall()
            ops: List[OutboxOperation] = []
            for r in rows:
                ops.append(OutboxOperation(
                    id=r[0],
                    operation_type=r[1],
                    endpoint=r[2],
                    request=json.loads(r[3]) if IS_SQLITE else r[3],
                    headers=json.loads(r[4]) if IS_SQLITE else r[4],
                    idempotency_key=r[5],
                    status=r[6],
                    retry_count=r[7],
                    next_retry_at=r[8],
                    error=r[9],
                ))
            # simple metric
            print(f"[metrics] outbox.pick_batch count={len(ops)}")
            return ops

    def get_stats(self) -> Dict[str, int]:
        conn = self.conn_factory()
        c = conn.cursor()
        c.execute("""
        select status, count(*) from outbox group by status
        """)
        out: Dict[str, int] = {}
        for status, count in c.fetchall():
            out[status] = int(count)
        return out