
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
