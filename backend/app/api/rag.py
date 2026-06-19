"""
Bower Ag CowCare Tool — RAG Advisory Search Endpoint
Sprint 4: Similarity search over embedded advisory documents using pgvector.

Endpoint:
    GET /advisory/search?q={query}&domain={optional}&limit={default 5}

Auth: Any role except customer.
Returns chunks ranked by cosine similarity, filtered by threshold (0.70).
"""

import time
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, NON_CUSTOMER_ROLES, require_role
from app.db.supabase_client import get_supabase_client
from app.services.audit_service import fire_and_forget_audit

router = APIRouter(tags=["RAG Advisory"])

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
TARGET_DIM = 1536
SIMILARITY_THRESHOLD = 0.70
VALID_DOMAINS = ["troubleshooting", "sds", "procedure", "product_info", "calculation"]

# ─────────────────────────────────────────────────────────────────────────────
# Embedding model (singleton, loaded on first request)
# ─────────────────────────────────────────────────────────────────────────────

_embedder = None


def _get_embedder():
    """Lazy-load the embedding model (cached after first call)."""
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding
        _embedder = TextEmbedding(EMBEDDING_MODEL)
    return _embedder


def _embed_query(query: str) -> list[float]:
    """Generate a 1536-dim zero-padded embedding for a query string."""
    embedder = _get_embedder()
    raw = list(embedder.embed([query]))[0]
    padded = np.zeros(TARGET_DIM)
    padded[:EMBEDDING_DIM] = raw
    return padded.tolist()


def _parse_embedding(emb) -> Optional[np.ndarray]:
    """
    Parse an embedding from Supabase — may be a string (PostgREST vector
    format: '[0.1,0.2,...]') or a list of floats.
    """
    if isinstance(emb, str):
        try:
            vals = [float(v) for v in emb.strip("[]").split(",")]
            return np.array(vals, dtype=np.float32)
        except (ValueError, AttributeError):
            return None
    elif isinstance(emb, list):
        return np.array(emb, dtype=np.float32)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/advisory/search")
async def advisory_search(
    q: str = Query(..., min_length=2, max_length=500, description="Search query"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    limit: int = Query(5, ge=1, le=20, description="Max results"),
    user: CurrentUser = Depends(require_role(NON_CUSTOMER_ROLES)),
):
    """
    Semantic search over advisory documents using pgvector cosine similarity.

    - Embeds the query using the same model as document ingestion
    - Fetches document_chunks and computes cosine similarity
    - Filters by domain if provided
    - Filters out results below similarity threshold (0.70)
    - Returns ranked results with section_title, content, source_doc, domain, similarity_score

    Auth: Any authenticated non-customer role.
    This endpoint does NOT call Claude/LLM — it's pure vector search.
    """
    start = time.time()

    # Validate domain filter
    if domain and domain not in VALID_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid domain '{domain}'. Valid domains: {VALID_DOMAINS}",
        )

    # Generate query embedding
    try:
        query_embedding = _embed_query(q)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate query embedding: {str(e)[:200]}",
        )

    # Fetch chunks from DB
    client = get_supabase_client()
    query_builder = client.table("document_chunks").select(
        "section_title, content, source_doc, domain, embedding"
    )
    if domain:
        query_builder = query_builder.eq("domain", domain)

    result = query_builder.execute()

    if not result.data:
        duration_ms = int((time.time() - start) * 1000)
        fire_and_forget_audit(
            user_id=user.id,
            action="advisory.search",
            domain="rag",
            query_text=q,
            llm_called=False,
            governance_result={"count": 0, "domain_filter": domain},
            response_summary="No chunks in database",
            duration_ms=duration_ms,
        )
        return {
            "query": q,
            "domain_filter": domain,
            "results": [],
            "count": 0,
            "source": "advisory_rag",
        }

    # Compute cosine similarity in Python
    # For ~30-50 advisory chunks, this is fast and avoids needing a custom
    # PostgreSQL function. For 1000+ chunks, use a Supabase RPC function.
    query_vec = np.array(query_embedding, dtype=np.float32)
    query_norm = np.linalg.norm(query_vec)

    scored = []
    for row in result.data:
        if not row.get("embedding"):
            continue

        doc_vec = _parse_embedding(row["embedding"])
        if doc_vec is None:
            continue

        doc_norm = np.linalg.norm(doc_vec)
        if query_norm == 0 or doc_norm == 0:
            continue

        similarity = float(np.dot(query_vec, doc_vec) / (query_norm * doc_norm))

        if similarity >= SIMILARITY_THRESHOLD:
            scored.append({
                "section_title": row["section_title"],
                "content": row["content"],
                "source_doc": row["source_doc"],
                "domain": row["domain"],
                "similarity_score": round(similarity, 4),
            })

    # Sort by similarity descending, take top-k
    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    top_results = scored[:limit]

    duration_ms = int((time.time() - start) * 1000)

    # Audit log
    fire_and_forget_audit(
        user_id=user.id,
        action="advisory.search",
        domain="rag",
        query_text=q,
        llm_called=False,
        governance_result={
            "count": len(top_results),
            "domain_filter": domain,
            "top_score": top_results[0]["similarity_score"] if top_results else None,
        },
        response_summary=f"Returned {len(top_results)} advisory chunks",
        duration_ms=duration_ms,
    )

    return {
        "query": q,
        "domain_filter": domain,
        "results": top_results,
        "count": len(top_results),
        "source": "advisory_rag",
    }
