-- I1 BGE embedder: migrate embedding column 128 -> 384 (ADR-007)
-- Clears existing vectors; run scripts/reembed_memories.py after applying.

UPDATE memory SET embedding = NULL, embedding_model = NULL WHERE embedding IS NOT NULL;

ALTER TABLE memory
    ALTER COLUMN embedding TYPE vector(384);
