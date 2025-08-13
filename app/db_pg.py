import os
import json
import threading

def get_db_config():
    database_url = os.getenv("DATABASE_URL")
    is_sqlite = database_url and database_url.startswith("sqlite")
    return database_url, is_sqlite

_conn_lock = threading.Lock()
_conn = None  # lazy init

def _ensure_conn():
    """Create a singleton connection lazily."""
    global _conn
    if _conn is None:
        DATABASE_URL, IS_SQLITE = get_db_config()
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set")

        if IS_SQLITE:
            import sqlite3
            db_api = sqlite3
            path = DATABASE_URL.replace("sqlite:///", "")
            _conn = db_api.connect(path, check_same_thread=False)
            _conn.row_factory = db_api.Row
        else:
            try:
                import psycopg2 as pg
            except ImportError:
                import psycopg2_binary as pg
            db_api = pg
            _conn = db_api.connect(DATABASE_URL, application_name="orchestrator")
            _conn.autocommit = True
    return _conn

def placeholder(n=1):
    _, IS_SQLITE = get_db_config()
    if IS_SQLITE:
        return ",".join(["?"] * n)
    return ",".join(["%s"] * n)


def get_conn():
    """Return a live psycopg2 connection, initializing if needed."""
    return _ensure_conn()


def init():
    """Create minimal tables used by outbox and events."""
    _, IS_SQLITE = get_db_config()
    with _conn_lock:
        conn = _ensure_conn()
        c = conn.cursor()
        if IS_SQLITE:
            c.execute("""
            create table if not exists events(
                  delivery_id text primary key,
                  payload text not null,
                  created_at text not null default (datetime('now'))
            );
            """)
            c.execute("""
            create table if not exists tasks(
                id text primary key,
                external_id text,
                provider text,
                payload text,
                score real,
                status text,
                client text,
                created_at text default (datetime('now')),
                updated_at text default (datetime('now'))
            );
            """)
            c.execute("""
            create table if not exists outbox(
              id integer primary key autoincrement,
              operation_type text not null,
              endpoint text not null,
              request text not null,
              headers text not null default '{}',
              idempotency_key text not null,
              status text not null, -- pending|inflight|delivered|failed|dead
              retry_count int not null default 0,
              next_retry_at text null,
              error text null,
              created_at text not null default (datetime('now')),
              updated_at text not null default (datetime('now'))
            );
            """)
        else:
            c.execute("""
            create table if not exists events(
              delivery_id text primary key,
              payload jsonb not null,
              created_at timestamptz not null default now()
            );
            """)
            c.execute("""
            create table if not exists tasks(
                id text primary key,
                external_id text,
                provider text,
                payload jsonb,
                score real,
                status text,
                client text,
                created_at timestamptz default now(),
                updated_at timestamptz default now()
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

        c.execute("create unique index if not exists outbox_idem_ux on outbox(idempotency_key);")
        c.execute("create index if not exists outbox_status_next_idx on outbox(status, next_retry_at);")


def upsert_event(delivery_id: str, event: dict):
    _, IS_SQLITE = get_db_config()
    with _conn_lock:
        conn = _ensure_conn()
        c = conn.cursor()
        sql = "insert into events(delivery_id, payload) values(?, ?) on conflict(delivery_id) do nothing" if IS_SQLITE \
            else "insert into events(delivery_id, payload) values(%s, %s::jsonb) on conflict do nothing"
        c.execute(sql, (delivery_id, json.dumps(event)))


def seen_delivery(delivery_id: str) -> bool:
    conn = _ensure_conn()
    c = conn.cursor()
    c.execute(f"select 1 from events where delivery_id={placeholder()}", (delivery_id,))
    return c.fetchone() is not None


def save_task(task: dict):
    """Saves a task, replacing it if it already exists."""
    _, IS_SQLITE = get_db_config()
    with _conn_lock:
        conn = _ensure_conn()
        c = conn.cursor()
        if IS_SQLITE:
            sql = """
                insert or replace into tasks(id, external_id, provider, payload, score, status, client, created_at, updated_at)
                    values(?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """
        else:
            sql = """
                insert into tasks(id, external_id, provider, payload, score, status, client, created_at, updated_at)
                values(%s, %s, %s, %s::jsonb, %s, %s, %s, %s, now())
                on conflict(id) do update set
                    external_id = excluded.external_id,
                    provider = excluded.provider,
                    payload = excluded.payload,
                    score = excluded.score,
                    status = excluded.status,
                    client = excluded.client,
                    updated_at = now()
            """
        c.execute(
            sql,
            (
                task["id"],
                task.get("external_id"),
                task.get("provider", "clickup"),
                json.dumps(task),
                task.get("score", 0.0),
                task.get("status", "triaged"),
                task.get("client", ""),
                task["created_at"],
            ),
        )

def fetch_open_tasks() -> list[dict]:
    """Fetches all tasks that are not in 'done' status."""
    _, IS_SQLITE = get_db_config()
    conn = _ensure_conn()
    c = conn.cursor()
    c.execute("select payload from tasks where status != 'done'")
    # for sqlite, we need to json.loads, for pg, it's automatic
    return [json.loads(r[0]) if IS_SQLITE else r[0] for r in c.fetchall()]

def touch_task(task_id: str):
    """Updates the updated_at timestamp for a task."""
    _, IS_SQLITE = get_db_config()
    with _conn_lock:
        conn = _ensure_conn()
        c = conn.cursor()
        now_fn = "datetime('now')" if IS_SQLITE else "now()"
        c.execute(f"update tasks set updated_at = {now_fn} where id = {placeholder()}", (task_id,))

def map_upsert(provider: str, external_id: str, internal_id: str):
    """Maps an external provider ID to an internal task ID."""
    with _conn_lock:
        conn = _ensure_conn()
        c = conn.cursor()
        sql = f"update tasks set external_id = {placeholder()} where id = {placeholder()} and provider = {placeholder()}"
        c.execute(sql, (external_id, internal_id, provider))

def map_get_internal(provider: str, external_id: str) -> str | None:
    """Gets the internal task ID for a given external provider ID."""
    conn = _ensure_conn()
    c = conn.cursor()
    sql = f"select id from tasks where provider = {placeholder()} and external_id = {placeholder()}"
    c.execute(sql, (provider, external_id))
    result = c.fetchone()
    return result[0] if result else None


def dlq_put(provider: str, endpoint: str, request: dict, error: str):
    """If you have a separate DLQ table, wire it here. Keep for compatibility."""
    _, IS_SQLITE = get_db_config()
    conn = _ensure_conn()
    c = conn.cursor()
    if IS_SQLITE:
        sql = "insert into outbox(operation_type, endpoint, request, headers, idempotency_key, status, error) values(?,?,?,?,?,?,?)"
    else:
        sql = "insert into outbox(operation_type, endpoint, request, headers, idempotency_key, status, error) values(%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s)"

    c.execute(sql, ("dlq", endpoint, json.dumps(request), json.dumps({}), f"dlq:{endpoint}", "dead", error))


def outbox_cleanup(retain_days: int = 7, max_rows: int = 10000):
    """Delete delivered rows older than N days, keep table lean in dev."""
    _, IS_SQLITE = get_db_config()
    conn = _ensure_conn()
    c = conn.cursor()
    if IS_SQLITE:
        # SQLite doesn't support interval math like postgres
        c.execute(f"delete from outbox where status='delivered' and created_at < date('now', '-{retain_days} days') limit {max_rows}")
    else:
        c.execute(f"delete from outbox where status='delivered' and created_at < now() - ('{retain_days}' || ' days')::interval limit {max_rows}")