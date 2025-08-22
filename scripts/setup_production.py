#!/usr/bin/env python3
"""
Production Setup Helper for Render + Supabase
"""

import os
import sys

def print_setup_instructions():
    """Print step-by-step setup instructions"""
    
    print("🚀 Project Archangel - Production Setup Guide")
    print("=" * 60)
    print()
    
    print("📋 STEP 1: Upgrade Render to Starter Plan ($7/month)")
    print("-" * 40)
    print("1. Go to: https://dashboard.render.com")
    print("2. Select your 'project-archangel-api' service")
    print("3. Click 'Settings' tab")
    print("4. Under 'Instance Type', select 'Starter' ($7/month)")
    print("5. Click 'Save Changes'")
    print()
    
    print("🗄️ STEP 2: Set up Supabase (Free PostgreSQL)")
    print("-" * 40)
    print("1. Go to: https://supabase.com")
    print("2. Sign up and create new project")
    print("3. Project name: 'project-archangel'")
    print("4. Choose region closest to your Render region")
    print("5. SAVE YOUR DATABASE PASSWORD!")
    print()
    
    print("🔗 STEP 3: Connect Render to Supabase")
    print("-" * 40)
    print("1. In Supabase: Settings → Database → Connection string → URI")
    print("2. Copy the PostgreSQL connection string")
    print("3. In Render: Environment tab")
    print("4. Update DATABASE_URL with Supabase connection string")
    print()
    
    print("📊 STEP 4: Initialize Database Tables")
    print("-" * 40)
    print("After Render redeploys with new DATABASE_URL:")
    print()
    print("Option A - Via API:")
    print("curl -X POST https://project-archangel-api.onrender.com/init/database")
    print()
    print("Option B - Via Supabase SQL Editor:")
    print("Copy and run the SQL from scripts/schema.sql")
    print()
    
    print("✅ STEP 5: Verify Everything Works")
    print("-" * 40)
    print("Test commands:")
    print()
    print("# Check health")
    print("curl https://project-archangel-api.onrender.com/health")
    print()
    print("# Create test task")
    print("""curl -X POST https://project-archangel-api.onrender.com/tasks/intake?provider=clickup \\
  -H "Content-Type: application/json" \\
  -d '{"title":"Production test","client":"test"}'""")
    print()
    
    print("🎉 Done! Your app will now:")
    print("-" * 40)
    print("✅ Stay online 24/7 (no cold starts)")
    print("✅ Keep all data persistent in PostgreSQL")
    print("✅ Handle production workloads reliably")
    print("✅ Scale as needed")
    print()
    
    print("💡 Tips:")
    print("-" * 40)
    print("• Monitor usage in Supabase dashboard")
    print("• Set up backups in Supabase (automatic)")
    print("• Consider adding custom domain in Render")
    print("• Enable Render's auto-deploy from GitHub")
    print()

def generate_schema_sql():
    """Generate PostgreSQL schema for Supabase"""
    
    schema = """
-- Project Archangel PostgreSQL Schema for Supabase

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    client TEXT NOT NULL,
    project TEXT,
    task_type TEXT DEFAULT 'general',
    deadline TIMESTAMPTZ,
    importance INTEGER DEFAULT 3,
    effort_hours DECIMAL(5,2) DEFAULT 1.0,
    labels JSONB DEFAULT '[]'::jsonb,
    source TEXT DEFAULT 'api',
    meta JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    score DECIMAL(5,3),
    status TEXT DEFAULT 'pending',
    external_id TEXT,
    provider TEXT,
    checklist JSONB DEFAULT '[]'::jsonb,
    subtasks JSONB DEFAULT '[]'::jsonb,
    orchestration_meta JSONB DEFAULT '{}'::jsonb
);

-- Outbox table for reliable message delivery
CREATE TABLE IF NOT EXISTS outbox (
    id SERIAL PRIMARY KEY,
    operation_type TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    request JSONB NOT NULL,
    headers JSONB DEFAULT '{}'::jsonb,
    idempotency_key TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Events table for webhook deduplication
CREATE TABLE IF NOT EXISTS events (
    delivery_id TEXT PRIMARY KEY,
    event_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Task mapping table
CREATE TABLE IF NOT EXISTS task_mapping (
    provider TEXT NOT NULL,
    external_id TEXT NOT NULL,
    internal_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (provider, external_id)
);

-- Swarm memory table for AI coordination
CREATE TABLE IF NOT EXISTS swarm_memory (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    task_id TEXT,
    memory_type TEXT NOT NULL,
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tasks_client ON tasks(client);
CREATE INDEX IF NOT EXISTS idx_tasks_provider ON tasks(provider);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status);
CREATE INDEX IF NOT EXISTS idx_outbox_next_retry ON outbox(next_retry_at);
CREATE INDEX IF NOT EXISTS idx_swarm_memory_session ON swarm_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_swarm_memory_task ON swarm_memory(task_id);

-- JSONB indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_tasks_labels ON tasks USING GIN (labels);
CREATE INDEX IF NOT EXISTS idx_tasks_meta ON tasks USING GIN (meta);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_outbox_updated_at BEFORE UPDATE ON outbox
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""
    
    # Save schema to file
    with open("scripts/schema.sql", "w") as f:
        f.write(schema)
    
    print("✅ Generated scripts/schema.sql")
    print("   You can run this in Supabase SQL Editor")

if __name__ == "__main__":
    print_setup_instructions()
    
    if "--generate-schema" in sys.argv:
        generate_schema_sql()
    else:
        print("💡 Run with --generate-schema to create SQL file")
