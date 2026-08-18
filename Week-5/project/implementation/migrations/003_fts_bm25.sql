-- I4 hybrid retrieval: Postgres full-text search on memory.content (ADR-013)

ALTER TABLE memory ADD COLUMN IF NOT EXISTS content_tsv tsvector;

UPDATE memory
SET content_tsv = to_tsvector('english', coalesce(content, ''))
WHERE content_tsv IS NULL;

CREATE INDEX IF NOT EXISTS memory_content_tsv_idx ON memory USING GIN (content_tsv);

CREATE OR REPLACE FUNCTION memory_content_tsv_update() RETURNS trigger AS $$
BEGIN
    NEW.content_tsv := to_tsvector('english', coalesce(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS memory_content_tsv_trigger ON memory;

CREATE TRIGGER memory_content_tsv_trigger
    BEFORE INSERT OR UPDATE OF content ON memory
    FOR EACH ROW
    EXECUTE FUNCTION memory_content_tsv_update();
