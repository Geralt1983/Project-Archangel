import os, sqlite3, json, threading, time
from contextlib import contextmanager

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

_lock = threading.Lock()

def _conn():
    # Simple sqlite only for MVP. Swap to Postgres by replacing this module.
    path = DB_URL.replace("sqlite:///", "")
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

_conn_singleton = _conn()

def init():
    c = _conn_singleton.cursor()
    c.execute("""create table if not exists tasks(
        id text primary key,
        external_id text,
        provider text,
        payload text,
        score real,
        status text,
        client text,
        created_at text
    )""")
    c.execute("""create table if not exists events(
        delivery_id text primary key,
        payload text,
        created_at integer
    )""")
    _conn_singleton.commit()

def save_task(task: dict):
    with _lock:
        _conn_singleton.execute(
            "insert or replace into tasks(id, external_id, provider, payload, score, status, client, created_at) values(?,?,?,?,?,?,?,?)",
            (task["id"], task.get("external_id"), task.get("provider", "clickup"),
             json.dumps(task), task.get("score", 0.0), "triaged", task.get("client",""),
             task["created_at"])
        )
        _conn_singleton.commit()

def fetch_open_tasks():
    cur = _conn_singleton.execute("select payload from tasks where status!='done'")
    return [json.loads(r[0]) for r in cur.fetchall()]

def upsert_event(delivery_id: str, event: dict):
    with _lock:
        _conn_singleton.execute(
            "insert or ignore into events(delivery_id, payload, created_at) values(?,?,?)",
            (delivery_id, json.dumps(event), int(time.time()))
        )
        _conn_singleton.commit()

def seen_delivery(delivery_id: str) -> bool:
    cur = _conn_singleton.execute("select 1 from events where delivery_id=?", (delivery_id,))
    return cur.fetchone() is not None

init()