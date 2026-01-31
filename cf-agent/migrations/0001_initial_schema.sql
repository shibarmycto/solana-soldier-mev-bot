-- Migration: Initial schema for Matrix AI Agent

CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    config TEXT
);

CREATE TABLE IF NOT EXISTS links (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    active BOOLEAN DEFAULT TRUE,
    visits INTEGER DEFAULT 0,
    user_id TEXT
);

CREATE TABLE IF NOT EXISTS webhook_logs (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_links_active ON links(active, expires_at);
CREATE INDEX IF NOT EXISTS idx_webhooks_processed ON webhook_logs(processed);
