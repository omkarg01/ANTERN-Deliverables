-- M8.1: canonical current state per topic domain (ADR-014 revision)
CREATE TABLE memory_canonical_state (
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    state_key TEXT NOT NULL,
    memory_id UUID NOT NULL REFERENCES memory(memory_id) ON DELETE CASCADE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, user_id, state_key)
);

CREATE INDEX idx_canonical_state_memory
    ON memory_canonical_state (memory_id);
