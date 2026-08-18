-- M8 Episodic: sequential links between memories (ADR-014)
CREATE TABLE memory_episode_link (
    link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    from_memory_id UUID NOT NULL REFERENCES memory(memory_id) ON DELETE CASCADE,
    to_memory_id UUID NOT NULL REFERENCES memory(memory_id) ON DELETE CASCADE,
    relation TEXT NOT NULL CHECK (relation IN ('before', 'after', 'replaces')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (from_memory_id, to_memory_id, relation)
);

CREATE INDEX idx_episode_link_to
    ON memory_episode_link (tenant_id, user_id, to_memory_id);

CREATE INDEX idx_episode_link_from
    ON memory_episode_link (tenant_id, user_id, from_memory_id);
