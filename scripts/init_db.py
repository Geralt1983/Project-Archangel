#!/usr/bin/env python3
"""
Database initialization script for Project Archangel
Creates all required tables and indexes
"""

import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from db_pg import get_conn, get_db_config

def init_database():
    """Initialize the database with all required tables"""
    
    print("🔄 Initializing Project Archangel database...")
    
    try:
        conn = get_conn()
        cursor = conn.cursor()
        
        # Get database type
        _, is_sqlite = get_db_config()
        
        if is_sqlite:
            print("📊 Using SQLite database")
            init_sqlite(cursor)
        else:
            print("📊 Using PostgreSQL database")
            init_postgresql(cursor)
        
        conn.commit()
        print("✅ Database initialization completed successfully!")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)

def init_sqlite(cursor):
    """Initialize SQLite database tables"""
    
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

def init_postgresql(cursor):
    """Initialize PostgreSQL database tables"""
    
    # Tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            client TEXT NOT NULL,
            project TEXT,
            task_type TEXT DEFAULT 'general',
            deadline TIMESTAMP,
            importance INTEGER DEFAULT 3,
            effort_hours DECIMAL(5,2) DEFAULT 1.0,
            labels JSONB,
            source TEXT DEFAULT 'api',
            meta JSONB,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            score DECIMAL(5,3),
            status TEXT DEFAULT 'pending',
            external_id TEXT,
            provider TEXT,
            checklist JSONB,
            subtasks JSONB,
            orchestration_meta JSONB
        )
    """)
    
    # Outbox table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outbox (
            id SERIAL PRIMARY KEY,
            operation_type TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            request JSONB NOT NULL,
            headers JSONB,
            idempotency_key TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            next_retry_at TIMESTAMP,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Events table (for webhook deduplication)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            delivery_id TEXT PRIMARY KEY,
            event_data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Task mapping table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_mapping (
            provider TEXT NOT NULL,
            external_id TEXT NOT NULL,
            internal_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    
    # Create JSONB indexes for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_labels ON tasks USING GIN (labels)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_meta ON tasks USING GIN (meta)")

if __name__ == "__main__":
    init_database()
