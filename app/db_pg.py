import os
import json
import threading
import logging
from typing import Optional, Tuple, Any

# Configure logging
logger = logging.getLogger(__name__)

def get_db_config() -> Tuple[Optional[str], bool]:
    """
    Get database configuration from environment variables.
    
    Returns:
        Tuple of (database_url, is_sqlite_flag)
        
    Raises:
        ValueError: If DATABASE_URL format is invalid
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url and not (database_url.startswith("sqlite") or database_url.startswith("postgresql")):
        raise ValueError(f"Unsupported database URL format: {database_url}")
    
    is_sqlite = database_url and database_url.startswith("sqlite")
    return database_url, is_sqlite

_conn_lock = threading.Lock()
_conn: Optional[Any] = None  # lazy init

def _ensure_conn() -> Any:
    """
    Create a singleton database connection lazily.
    
    Returns:
        Database connection object (sqlite3.Connection or psycopg2.Connection)
        
    Raises:
        RuntimeError: If DATABASE_URL is not set
        ConnectionError: If database connection fails
        ImportError: If required database driver is not available
    """
    global _conn
    if _conn is None:
        with _conn_lock:  # Thread-safe initialization
            if _conn is None:  # Double-check locking pattern
                try:
                    DATABASE_URL, IS_SQLITE = get_db_config()
                    if not DATABASE_URL:
                        raise RuntimeError(
                            "DATABASE_URL is not set. Please configure your database connection."
                        )
                    
                    logger.info(f"Initializing {'SQLite' if IS_SQLITE else 'PostgreSQL'} database connection")
                    
                    if IS_SQLITE:
                        import sqlite3
                        db_api = sqlite3
                        path = DATABASE_URL.replace("sqlite:///", "")
                        _conn = db_api.connect(path, check_same_thread=False)
                        _conn.row_factory = db_api.Row
                        logger.info(f"SQLite connection established: {path}")
                    else:
                        try:
                            import psycopg2 as pg
                        except ImportError:
                            try:
                                import psycopg2_binary as pg
                            except ImportError:
                                raise ImportError(
                                    "PostgreSQL driver not found. Install psycopg2 or psycopg2-binary"
                                )
                        
                        _conn = pg.connect(DATABASE_URL, application_name="project-archangel")
                        _conn.autocommit = True
                        logger.info("PostgreSQL connection established")
                        
                except Exception as e:
                    logger.error(f"Database connection failed: {e}")
                    raise ConnectionError(f"Failed to connect to database: {e}") from e
    
    return _conn

def placeholder(n: int = 1) -> str:
    """
    Generate database-specific placeholder string for parameterized queries.
    
    Args:
        n: Number of placeholders to generate
        
    Returns:
        Comma-separated placeholder string
        
    Raises:
        ValueError: If n is less than 1
    """
    if n < 1:
        raise ValueError("Number of placeholders must be at least 1")
        
    _, IS_SQLITE = get_db_config()
    if IS_SQLITE:
        return ",".join(["?"] * n)
    return ",".join(["%s"] * n)


def get_conn() -> Any:
    """
    Return a live database connection, initializing if needed.
    
    Returns:
        Database connection object
        
    Raises:
        ConnectionError: If database connection fails
    """
    try:
        return _ensure_conn()
    except Exception as e:
        logger.error(f"Failed to get database connection: {e}")
        raise


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
            
            # Provider configuration table for SQLite
            c.execute("""
            create table if not exists providers(
              id text primary key,
              name text not null,
              type text not null, -- 'clickup', 'trello', 'todoist'
              config text not null, -- JSON as text for SQLite
              health_status text not null default 'active',
              active_tasks integer not null default 0,
              wip_limit integer not null default 10,
              created_at text not null default (datetime('now')),
              updated_at text not null default (datetime('now'))
            );
            """)
            
            # Task routing history for analytics (SQLite)
            c.execute("""
            create table if not exists task_routing_history(
              id integer primary key autoincrement,
              task_id text not null,
              provider_id text not null,
              score real not null,
              routing_reason text,
              routed_at text not null default (datetime('now'))
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
            
            # Provider configuration table
            c.execute("""
            create table if not exists providers(
              id text primary key,
              name text not null,
              type text not null, -- 'clickup', 'trello', 'todoist'
              config jsonb not null,
              health_status text not null default 'active',
              active_tasks integer not null default 0,
              wip_limit integer not null default 10,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now()
            );
            """)
            
            # Task routing history for analytics
            c.execute("""
            create table if not exists task_routing_history(
              id bigserial primary key,
              task_id text not null,
              provider_id text not null,
              score real not null,
              routing_reason text,
              routed_at timestamptz not null default now()
            );
            """)

        # Create indexes for outbox table
        c.execute("create unique index if not exists outbox_idem_ux on outbox(idempotency_key);")
        c.execute("create index if not exists outbox_status_next_idx on outbox(status, next_retry_at);")
        
        # Create indexes for provider management
        c.execute("create index if not exists providers_type_idx on providers(type);")
        c.execute("create index if not exists providers_health_idx on providers(health_status);")
        
        # Create indexes for task routing history
        c.execute("create index if not exists task_routing_task_idx on task_routing_history(task_id);")
        c.execute("create index if not exists task_routing_provider_idx on task_routing_history(provider_id);")
        c.execute("create index if not exists task_routing_time_idx on task_routing_history(routed_at);")
        
        # Additional helpful indexes for tasks lookups and filtering  
        c.execute("create index if not exists tasks_provider_ext_idx on tasks(provider, external_id);")
        c.execute("create index if not exists tasks_status_idx on tasks(status);")


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