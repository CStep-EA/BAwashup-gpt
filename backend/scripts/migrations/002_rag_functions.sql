-- ═══════════════════════════════════════════════════════════════════════════════
-- Bower Ag CowCare Tool — Sprint 4 Migration: RAG Advisory Functions
-- Run in Supabase SQL Editor to enable server-side similarity search.
-- Without this, the Python fallback (in-memory cosine similarity) is used.
-- ═══════════════════════════════════════════════════════════════════════════════

-- match_advisory_chunks: pgvector cosine similarity search
-- Called by GET /advisory/search via supabase.rpc('match_advisory_chunks', ...)
CREATE OR REPLACE FUNCTION match_advisory_chunks(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.75,
    match_count int DEFAULT 5,
    filter_domain text DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    section_title text,
    content text,
    source_doc text,
    domain text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.section_title,
        dc.content,
        dc.source_doc,
        dc.domain,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    WHERE
        (filter_domain IS NULL OR dc.domain = filter_domain)
        AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
