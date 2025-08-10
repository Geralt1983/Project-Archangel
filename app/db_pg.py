import os
import json
import threading
import psycopg2
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL")

_conn_lock = threading.Lock()
_conn = None  # lazy init


def _ensure_conn():
    """Create a singleton connection lazily."""
    global _conn
    if _conn is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set")
        _conn = psycopg2.connect(DATABASE_URL, application_name="orchestrator")
        _conn.autocommit = True
    return _conn


def get_conn():
    """Return a live psycopg2 connection, initializing if needed."""
    return _ensure_conn()


def init():
    """Create minimal tables used by outbox and events."""
    with _conn_lock:
        conn = _ensure_conn()
        with conn.cursor() as c:
            c.execute("""
            create table if not exists events(
              delivery_id text primary key,
              payload jsonb not null,
              created_at timestamptz not null default now()
            );
            """)
            c.execute("""
            create table if not exists outbox(
              id bigserial primary key,
              operation_type text not null,
              endpoint text not null,
              request jsonb not null,
              headers jsonb not null default '{}'::jsonb,
              idempotency_key text not null,
              status text not null, -- pending|inflight|delivered|failed|dead
              retry_count int not null default 0,
              next_retry_at timestamptz null,
              error text null,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now()
            );
            """)
            c.execute("""
            create unique index if not exists outbox_idem_ux
              on outbox(idempotency_key);
            """)
            c.execute("""
            create index if not exists outbox_status_next_idx
              on outbox(status, next_retry_at);
            """)


def upsert_event(delivery_id: str, event: dict):
    with _conn_lock:
        conn = _ensure_conn()
        with conn.cursor() as c:
            c.execute(
                "insert into events(delivery_id, payload) values(%s, %s::jsonb) on conflict do nothing",
                (delivery_id, json.dumps(event)),
            )


def seen_delivery(delivery_id: str) -> bool:
    conn = _ensure_conn()
    with conn.cursor() as c:
        c.execute("select 1 from events where delivery_id=%s", (delivery_id,))
        return c.fetchone() is not None


def dlq_put(provider: str, endpoint: str, request: dict, error: str):
    """If you have a separate DLQ table, wire it here. Keep for compatibility."""
    conn = _ensure_conn()
    with conn.cursor() as c:
        c.execute("""
        insert into outbox(operation_type, endpoint, request, headers, idempotency_key, status, error)
        values(%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s)
        """, ("dlq", endpoint, json.dumps(request), json.dumps({}), f"dlq:{endpoint}", "dead", error))