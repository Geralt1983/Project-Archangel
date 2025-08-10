import os, json, time, threading, psycopg2
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL")

_conn_lock = threading.Lock()
_conn = None

def _ensure_conn():
    """FIX: Lazy connection initialization to avoid import-time failures"""
    global _conn
    if _conn is None:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required")
        _conn = psycopg2.connect(DATABASE_URL, application_name="orchestrator")
        _conn.autocommit = True
        init_tables()
    return _conn

def init_tables():
    """Initialize database tables"""
    conn = _ensure_conn()
    with conn.cursor() as c:
        c.execute("""
        create table if not exists tasks(
          id text primary key,
          external_id text,
          provider text,
          payload jsonb not null,
          score double precision,
          status text,
          client text,
          created_at timestamptz
        );
        alter table if exists tasks add column if not exists updated_at timestamptz;
        create table if not exists events(
          delivery_id text primary key,
          payload jsonb not null,
          created_at timestamptz default now()
        );
        create table if not exists dlq(
          id bigserial primary key,
          provider text,
          endpoint text,
          request jsonb,
          error text,
          created_at timestamptz default now()
        );
        create table if not exists task_map(
          provider text not null,
          external_id text not null,
          internal_id text not null,
          primary key (provider, external_id)
        );
        create index if not exists ix_task_map_internal on task_map(internal_id);
        """)

def init():
    """Legacy init function - now just ensures tables are created"""
    init_tables()

def save_task(task: dict):
    conn = _ensure_conn()
    with _conn_lock, conn.cursor() as c:
        c.execute("""
        insert into tasks(id, external_id, provider, payload, score, status, client, created_at, updated_at)
        values(%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s)
        on conflict (id) do update set
          external_id=excluded.external_id,
          provider=excluded.provider,
          payload=excluded.payload,
          score=excluded.score,
          status=excluded.status,
          client=excluded.client,
          updated_at=excluded.updated_at
        """, (
            task["id"], task.get("external_id"), task.get("provider","clickup"),
            json.dumps(task), task.get("score",0.0), "triaged", task.get("client",""),
            task["created_at"], task.get("updated_at", task["created_at"])
        ))

def touch_task(task_id: str, when: str):
    conn = _ensure_conn()
    with conn.cursor() as c:
        c.execute("update tasks set updated_at = %s where id = %s", (when, task_id))

def map_upsert(provider: str, external_id: str, internal_id: str):
    conn = _ensure_conn()
    with _conn_lock, conn.cursor() as c:
        c.execute("""
        insert into task_map(provider, external_id, internal_id)
        values(%s,%s,%s)
        on conflict (provider, external_id) do update
        set internal_id=excluded.internal_id
        """, (provider, external_id, internal_id))

def map_get_internal(provider: str, external_id: str) -> str | None:
    conn = _ensure_conn()
    with conn.cursor() as c:
        c.execute("select internal_id from task_map where provider=%s and external_id=%s",
                  (provider, external_id))
        row = c.fetchone()
        return row[0] if row else None

def map_get_external(provider: str, internal_id: str) -> str | None:
    conn = _ensure_conn()
    with conn.cursor() as c:
        c.execute("select external_id from task_map where provider=%s and internal_id=%s",
                  (provider, internal_id))
        row = c.fetchone()
        return row[0] if row else None

def fetch_open_tasks():
    conn = _ensure_conn()
    with conn.cursor() as c:
        c.execute("select payload from tasks where coalesce(status,'') != 'done'")
        return [r[0] for r in c.fetchall()]

def upsert_event(delivery_id: str, event: dict):
    conn = _ensure_conn()
    with _conn_lock, conn.cursor() as c:
        c.execute("insert into events(delivery_id, payload) values(%s,%s::jsonb) on conflict do nothing",
                  (delivery_id, json.dumps(event)))

def seen_delivery(delivery_id: str) -> bool:
    conn = _ensure_conn()
    with conn.cursor() as c:
        c.execute("select 1 from events where delivery_id=%s", (delivery_id,))
        return c.fetchone() is not None

def dlq_put(provider: str, endpoint: str, request: dict, error: str):
    conn = _ensure_conn()
    with _conn_lock, conn.cursor() as c:
        c.execute("insert into dlq(provider, endpoint, request, error) values(%s,%s,%s::jsonb,%s)",
                  (provider, endpoint, json.dumps(request), error))