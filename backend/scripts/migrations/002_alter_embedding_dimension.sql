-- ═══════════════════════════════════════════════════════════════════════════════
-- MIGRATION 002: Alter document_chunks embedding from vector(1536) to vector(384)
-- ═══════════════════════════════════════════════════════════════════════════════
-- Sprint 4: RAG Advisory Layer
-- Reason: Using fastembed BAAI/bge-small-en-v1.5 (384 dimensions) instead of
--         OpenAI text-embedding-3-small (1536). bge-small is a high-quality,
--         fast, local embedding model -- no API key dependency.
--
-- Run in Supabase SQL Editor BEFORE running embed_documents.py
-- Safe to run: document_chunks table is empty at this point.
-- ═══════════════════════════════════════════════════════════════════════════════

-- Drop the existing HNSW index (uses old dimension)
DROP INDEX IF EXISTS idx_document_chunks_embedding;

-- Alter the embedding column to vector(384)
ALTER TABLE document_chunks
    ALTER COLUMN embedding TYPE vector(384)
    USING NULL;

-- Recreate the HNSW index with cosine distance operator
-- hnsw is preferred over ivfflat for < 100k rows (no training needed)
CREATE INDEX idx_document_chunks_embedding
    ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- Add a unique constraint for UPSERT support (source_doc + section_title)
-- This enables idempotent re-runs of the embedding script
ALTER TABLE document_chunks
    ADD CONSTRAINT uq_document_chunks_source_section
    UNIQUE (source_doc, section_title);

-- Verify
SELECT
    column_name,
    udt_name,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'document_chunks'
  AND column_name = 'embedding';
