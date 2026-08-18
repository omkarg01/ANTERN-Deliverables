-- CMIS initial schema (M1) — Postgres + pgvector
-- Traces to: design/data_model.md, ADR-001

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE memory_type AS ENUM (
    'preference', 'fact', 'constraint', 'context', 'reflection', 'episodic'
);

CREATE TYPE memory_status AS ENUM (
    'active', 'superseded', 'archived', 'deleted'
);

CREATE TYPE sensitivity_level AS ENUM (
    'public', 'internal', 'restricted', 'confidential'
);

CREATE TYPE actor_type AS ENUM (
    'user', 'system', 'reflection', 'admin'
);

CREATE TYPE event_type AS ENUM (
    'created', 'updated', 'superseded', 'archived', 'deleted', 'retrieved', 'injected'
);

CREATE TABLE memory (
    memory_id       UUID PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    content         TEXT NOT NULL,
    memory_type     memory_type NOT NULL DEFAULT 'fact',
    source_turn_id  UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      actor_type NOT NULL DEFAULT 'system',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_from      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until     TIMESTAMPTZ,
    status          memory_status NOT NULL DEFAULT 'active',
    version         INT NOT NULL DEFAULT 1,
    importance      REAL NOT NULL DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
    confidence      REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    embedding       vector(384),
    embedding_model TEXT,
    contains_pii    BOOLEAN NOT NULL DEFAULT FALSE,
    sensitivity_level sensitivity_level NOT NULL DEFAULT 'internal',
    supersedes      UUID REFERENCES memory(memory_id),
    superseded_by   UUID REFERENCES memory(memory_id)
);

CREATE INDEX idx_memory_tenant_user_status ON memory (tenant_id, user_id, status);
CREATE INDEX idx_memory_created_at ON memory (created_at DESC);

CREATE TABLE memory_event (
    event_id        UUID PRIMARY KEY,
    memory_id       UUID NOT NULL REFERENCES memory(memory_id) ON DELETE CASCADE,
    tenant_id       TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    event_type      event_type NOT NULL,
    event_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor           actor_type NOT NULL,
    content_before  TEXT,
    content_after   TEXT,
    status_before   memory_status,
    status_after    memory_status NOT NULL,
    source_turn_id  UUID,
    reason          TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_memory_event_memory_id ON memory_event (memory_id);
CREATE INDEX idx_memory_event_tenant_user ON memory_event (tenant_id, user_id);
