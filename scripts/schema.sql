
-- Project Archangel PostgreSQL Schema for Supabase

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL CHECK (LENGTH(title) > 0),
    description TEXT,
    client TEXT NOT NULL CHECK (LENGTH(client) > 0),
    project TEXT,
    task_type TEXT DEFAULT 'general' CHECK (task_type IN ('general', 'bug', 'feature', 'maintenance', 'research')),
    deadline TIMESTAMPTZ,
    importance INTEGER DEFAULT 3 CHECK (importance >= 1 AND importance <= 5),
    effort_hours DECIMAL(5,2) DEFAULT 1.0 CHECK (effort_hours > 0 AND effort_hours <= 999.99),
    labels JSONB DEFAULT '[]'::jsonb,
    source TEXT DEFAULT 'api' CHECK (source IN ('api', 'clickup', 'trello', 'todoist', 'manual')),
    meta JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    score DECIMAL(5,3) CHECK (score IS NULL OR (score >= 0 AND score <= 1)),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled', 'blocked')),
    external_id TEXT,
    provider TEXT CHECK (provider IS NULL OR provider IN ('clickup', 'trello', 'todoist')),
    checklist JSONB DEFAULT '[]'::jsonb,
    subtasks JSONB DEFAULT '[]'::jsonb,
    orchestration_meta JSONB DEFAULT '{}'::jsonb,
    CHECK (deadline IS NULL OR deadline > created_at),
    CHECK (updated_at >= created_at)
);

-- Outbox table for reliable message delivery
CREATE TABLE IF NOT EXISTS outbox (
    id SERIAL PRIMARY KEY,
    operation_type TEXT NOT NULL CHECK (LENGTH(operation_type) > 0),
    endpoint TEXT NOT NULL CHECK (LENGTH(endpoint) > 0),
    request JSONB NOT NULL,
    headers JSONB DEFAULT '{}'::jsonb,
    idempotency_key TEXT UNIQUE NOT NULL CHECK (LENGTH(idempotency_key) > 0),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'dead_letter')),
    retry_count INTEGER DEFAULT 0 CHECK (retry_count >= 0 AND retry_count <= 10),
    next_retry_at TIMESTAMPTZ,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    provider TEXT CHECK (provider IS NULL OR provider IN ('clickup', 'trello', 'todoist')),
    CHECK (updated_at >= created_at),
    CHECK (next_retry_at IS NULL OR next_retry_at > created_at)
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
    session_id TEXT NOT NULL CHECK (LENGTH(session_id) > 0),
    task_id TEXT,
    memory_type TEXT NOT NULL CHECK (memory_type IN ('pre_task', 'post_edit', 'notify', 'post_task', 'decision_trace')),
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

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_tasks_status_deadline ON tasks(status, deadline) WHERE deadline IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_client_status ON tasks(client, status);
CREATE INDEX IF NOT EXISTS idx_tasks_provider_external_id ON tasks(provider, external_id) WHERE provider IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_client_created_at ON tasks(client, created_at);
CREATE INDEX IF NOT EXISTS idx_outbox_status_next_retry ON outbox(status, next_retry_at) WHERE status = 'pending' AND next_retry_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_outbox_provider_status ON outbox(provider, status) WHERE provider IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_swarm_memory_session_type ON swarm_memory(session_id, memory_type);
CREATE INDEX IF NOT EXISTS idx_task_mapping_internal_id ON task_mapping(internal_id);

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
