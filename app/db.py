import os
import json
import threading
from pathlib import Path

_SQL_DIR = Path(__file__).parent / "sql"

def _get_sql(name: str) -> str:
    return (_SQL_DIR / f"{name}.sql").read_text()

def get_db_config():
    database_url = os.getenv("DATABASE_URL")
    is_sqlite = database_url and database_url.startswith("sqlite")
    return database_url, is_sqlite

_conn_lock = threading.Lock()
_conn = None

def _ensure_conn():
    global _conn
    if _conn is None:
        DATABASE_URL, IS_SQLITE = get_db_config()
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set")

        if IS_SQLITE:
            import sqlite3
            path = DATABASE_URL.replace("sqlite:///", "")
            _conn = sqlite3.connect(path, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
        else:
            try:
                import psycopg2 as pg
            except ImportError:
                import psycopg2_binary as pg
            _conn = pg.connect(DATABASE_URL, application_name="orchestrator")
            _conn.autocommit = True
    return _conn

def placeholder(n=1):
    _, IS_SQLITE = get_db_config()
    if IS_SQLITE:
        return ",".join(["?"] * n)
    return ",".join(["%s"] * n)

def get_conn():
    return _ensure_conn()

def init():
    _, IS_SQLITE = get_db_config()
    with _conn_lock:
        conn = _ensure_conn()
        c = conn.cursor()

        sql_file = "init_sqlite" if IS_SQLITE else "init_pg"
        sql_script = _get_sql(sql_file)

        # Execute script statement by statement
        for statement in sql_script.split(';'):
            if statement.strip():
                c.execute(statement)

        if IS_SQLITE:
            conn.commit()

def upsert_event(delivery_id: str, event: dict):
    _, IS_SQLITE = get_db_config()
    with _conn_lock:
        conn = _ensure_conn()
        c = conn.cursor()
        sql = "insert into events(delivery_id, payload) values(?, ?) on conflict(delivery_id) do nothing" if IS_SQLITE \
            else "insert into events(delivery_id, payload) values(%s, %s::jsonb) on conflict do nothing"
        c.execute(sql, (delivery_id, json.dumps(event)))
        if IS_SQLITE:
            conn.commit()

def seen_delivery(delivery_id: str) -> bool:
    _, IS_SQLITE = get_db_config()
    conn = _ensure_conn()
    sql = _get_sql("seen_delivery")
    if not IS_SQLITE:
        sql = sql.replace("?", "%s")

    c = conn.cursor()
    c.execute(sql, (delivery_id,))
    return c.fetchone() is not None

def save_task(task: dict):
    _, IS_SQLITE = get_db_config()
    with _conn_lock:
        conn = _ensure_conn()
        c = conn.cursor()

        sql_file = "save_task_sqlite" if IS_SQLITE else "save_task_pg"
        sql = _get_sql(sql_file)

        params = (
            task["id"],
            task.get("external_id"),
            task.get("provider", "clickup"),
            json.dumps(task),
            task.get("score", 0.0),
            task.get("status", "triaged"),
            task.get("client", ""),
            task["created_at"],
        )

        # The SQLite version does not need all the parameters, but the placeholder count is correct.
        if IS_SQLITE:
            pass

        c.execute(sql, params)
        if IS_SQLITE:
            conn.commit()

def fetch_open_tasks() -> list[dict]:
    _, IS_SQLITE = get_db_config()
    conn = _ensure_conn()
    c = conn.cursor()
    c.execute("select payload from tasks where status != 'done'")
    return [json.loads(r[0]) if IS_SQLITE else r[0] for r in c.fetchall()]

def touch_task(task_id: str):
    _, IS_SQLITE = get_db_config()
    with _conn_lock:
        conn = _ensure_conn()
        c = conn.cursor()
        now_fn = "datetime('now')" if IS_SQLITE else "now()"
        c.execute(f"update tasks set updated_at = {now_fn} where id = {placeholder()}", (task_id,))
        if IS_SQLITE:
            conn.commit()

def map_upsert(provider: str, external_id: str, internal_id: str):
    with _conn_lock:
        conn = _ensure_conn()
        c = conn.cursor()
        sql = f"update tasks set external_id = {placeholder()} where id = {placeholder()} and provider = {placeholder()}"
        c.execute(sql, (external_id, internal_id, provider))
        if IS_SQLITE:
            conn.commit()

def map_get_internal(provider: str, external_id: str) -> str | None:
    conn = _ensure_conn()
    c = conn.cursor()
    sql = f"select id from tasks where provider = {placeholder()} and external_id = {placeholder()}"
    c.execute(sql, (provider, external_id))
    result = c.fetchone()
    return result[0] if result else None

def dlq_put(provider: str, endpoint: str, request: dict, error: str):
    _, IS_SQLITE = get_db_config()
    conn = _ensure_conn()
    c = conn.cursor()
    if IS_SQLITE:
        sql = "insert into outbox(operation_type, endpoint, request, headers, idempotency_key, status, error) values(?,?,?,?,?,?,?)"
    else:
        sql = "insert into outbox(operation_type, endpoint, request, headers, idempotency_key, status, error) values(%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s)"

    c.execute(sql, ("dlq", endpoint, json.dumps(request), json.dumps({}), f"dlq:{endpoint}", "dead", error))
    if IS_SQLITE:
        conn.commit()

def outbox_cleanup(retain_days: int = 7, max_rows: int = 10000):
    _, IS_SQLITE = get_db_config()
    conn = _ensure_conn()
    c = conn.cursor()
    if IS_SQLITE:
        c.execute(f"delete from outbox where status='delivered' and created_at < date('now', '-{retain_days} days') limit {max_rows}")
    else:
        c.execute(f"delete from outbox where status='delivered' and created_at < now() - ('{retain_days}' || ' days')::interval limit {max_rows}")
    if IS_SQLITE:
        conn.commit()
