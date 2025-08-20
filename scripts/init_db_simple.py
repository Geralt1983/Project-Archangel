#!/usr/bin/env python3
"""
Simple database initialization script for Project Archangel
Creates all required tables and indexes without importing app modules
"""

import os
import sqlite3
import sys
from pathlib import Path

def get_db_url():
    """Get database URL from environment or use default"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        database_url = "sqlite:///./project_archangel.db"
        print("No DATABASE_URL configured, using default SQLite database")
    return database_url

def init_database():
    """Initialize the database with all required tables"""

    print("🔄 Initializing Project Archangel database...")

    try:
        db_url = get_db_url()
        
        if db_url.startswith("sqlite"):
            print("📊 Using SQLite database")
            init_sqlite(db_url)
        else:
            print("📊 Using PostgreSQL database")
            print("PostgreSQL initialization requires full app dependencies")
            print("Please use the main init_db.py script for PostgreSQL")
            sys.exit(1)

        print("✅ Database initialization completed successfully!")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)

def init_sqlite(db_url):
    """Initialize SQLite database tables"""
    
    # Extract database path from URL
    db_path = db_url.replace("sqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]  # Remove ./ prefix
    
    print(f"Creating database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            client TEXT NOT NULL,
            project TEXT,
            task_type TEXT DEFAULT 'general',
            deadline TEXT,
            importance INTEGER DEFAULT 3,
            effort_hours REAL DEFAULT 1.0,
            labels TEXT,
            source TEXT DEFAULT 'api',
            meta TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            score REAL,
            status TEXT DEFAULT 'pending',
            external_id TEXT,
            provider TEXT,
            checklist TEXT,
            subtasks TEXT,
            orchestration_meta TEXT
        )
    """)

    # Outbox table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_type TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            request TEXT NOT NULL,
            headers TEXT,
            idempotency_key TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            next_retry_at TEXT,
            error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Events table (for webhook deduplication)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            delivery_id TEXT PRIMARY KEY,
            event_data TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Task mapping table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_mapping (
            provider TEXT NOT NULL,
            external_id TEXT NOT NULL,
            internal_id TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (provider, external_id)
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_client ON tasks(client)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_provider ON tasks(provider)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_outbox_next_retry ON outbox(next_retry_at)")

    conn.commit()
    conn.close()
    
    print(f"✅ SQLite database initialized at: {db_path}")

if __name__ == "__main__":
    init_database()
