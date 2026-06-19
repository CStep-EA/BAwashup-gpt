"""
Bower Ag CowCare Tool — Advisory Document Embedding Pipeline
Sprint 4: Parse advisory PDFs, chunk by section, embed with fastembed,
upsert into Supabase document_chunks table for RAG similarity search.

Usage:
    cd backend && python -m scripts.embed_documents

Embedding model: BAAI/bge-small-en-v1.5 (384 dims, zero-padded to 1536)
  - Local model, no API key required
  - Cosine similarity perfectly preserved after zero-padding
  - Matches document_chunks.embedding column: vector(1536)

PDF extraction: PyMuPDF (fitz) — fast, handles all PDF types.
Memory: Processes one PDF at a time, embeds+upserts in small batches.
"""

import gc
import os
import re
import sys
import time
import numpy as np
import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

ADVISORY_DIR = Path(__file__).parent.parent / "docs" / "advisory"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
TARGET_DIM = 1536
MIN_CHUNK_LENGTH = 50
MAX_CHUNK_LENGTH = 4000
EMBED_BATCH_SIZE = 8

DOMAIN_MAP = [
    (["troubleshoot", "bacteria", "parlor", "wash", "water", "recommendation"],
     "troubleshooting"),
    (["sds", "safety data sheet"], "sds"),
    (["decision tree", "cip.*decision", "cip.*gpt"], "procedure"),
    (["tech data", "technical data"], "product_info"),
    (["shield.*ofb", "ofb.*reference", "ofb.*blend"], "calculation"),
    (["cl2", "curiass.*chart", "cl2.*chart"], "calculation"),
    (["cd114", "usage rate", "usage strength"], "calculation"),
    (["gea", "binder product guide", "competitive"], "competitive_ref"),
    (["customer facing", "example document", "template"], "report_template"),
]


def classify_domain(filename: str) -> str:
    fname_lower = filename.lower()
    for patterns, domain in DOMAIN_MAP:
        for pat in patterns:
            if re.search(pat, fname_lower):
                return domain
    return "general"


# ─────────────────────────────────────────────────────────────────────────────
# Text extraction (PyMuPDF)
# ─────────────────────────────────────────────────────────────────────────────

def extract_pages(pdf_path: str) -> list[str]:
    """Extract text from every page of a PDF using PyMuPDF."""
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        text = page.get_text()
        pages.append(text)
    doc.close()
    return pages


# ─────────────────────────────────────────────────────────────────────────────
# Section-aware chunking
# ─────────────────────────────────────────────────────────────────────────────

def is_heading(line: str) -> bool:
    """Detect section headings."""
    stripped = line.strip()
    if not stripped or len(stripped) < 3:
        return False
    if stripped.endswith(":") and len(stripped) < 200:
        return True
    if re.match(r"^\d+\.\s+[A-Z]", stripped):
        return True
    if re.match(r"^STEP\s+\d+", stripped, re.IGNORECASE):
        return True
    alpha_chars = [c for c in stripped if c.isalpha()]
    if len(alpha_chars) >= 3:
        upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
        if upper_ratio > 0.6 and len(stripped) < 200:
            return True
    return False


def chunk_pages_by_section(pages: list[str], filename: str, domain: str) -> list[dict]:
    """Route to the right chunker based on domain."""
    if domain == "sds":
        return _chunk_sds(pages, filename)
    elif domain == "product_info":
        return _chunk_tech_data(pages, filename)
    else:
        return _chunk_general(pages, filename, domain)


def _chunk_general(pages: list[str], filename: str, domain: str) -> list[dict]:
    """General section-aware chunking for troubleshooting, procedures, etc."""
    chunks = []
    current_heading = "Introduction"
    current_content = []

    for text in pages:
        if not text:
            continue
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if is_heading(stripped):
                if current_content:
                    content_text = "\n".join(current_content).strip()
                    if len(content_text) >= MIN_CHUNK_LENGTH:
                        chunks.append({
                            "section_title": current_heading[:500],
                            "content": content_text[:MAX_CHUNK_LENGTH],
                            "source_doc": filename,
                            "domain": domain,
                        })
                current_heading = stripped
                current_content = []
            else:
                current_content.append(stripped)

    if current_content:
        content_text = "\n".join(current_content).strip()
        if len(content_text) >= MIN_CHUNK_LENGTH:
            chunks.append({
                "section_title": current_heading[:500],
                "content": content_text[:MAX_CHUNK_LENGTH],
                "source_doc": filename,
                "domain": domain,
            })

    return chunks


def _chunk_sds(pages: list[str], filename: str) -> list[dict]:
    """SDS Binder: chunk by product (detect 'SAFETY DATA SHEET' markers)."""
    chunks = []
    current_product = None
    current_content = []

    for text in pages:
        if not text:
            continue

        is_new_sds = False
        product_name = None
        if "SAFETY DATA SHEET" in text.upper():
            product_name = _extract_sds_product(text)
            if product_name and product_name != current_product:
                is_new_sds = True

        if is_new_sds:
            if current_product and current_content:
                content_text = "\n".join(current_content).strip()
                if len(content_text) >= MIN_CHUNK_LENGTH:
                    chunks.append({
                        "section_title": f"SDS: {current_product}",
                        "content": content_text[:MAX_CHUNK_LENGTH],
                        "source_doc": filename,
                        "domain": "sds",
                    })
            current_product = product_name
            current_content = [text.strip()]
        else:
            current_content.append(text.strip())

    if current_product and current_content:
        content_text = "\n".join(current_content).strip()
        if len(content_text) >= MIN_CHUNK_LENGTH:
            chunks.append({
                "section_title": f"SDS: {current_product}",
                "content": content_text[:MAX_CHUNK_LENGTH],
                "source_doc": filename,
                "domain": "sds",
            })

    return chunks


def _extract_sds_product(text: str) -> Optional[str]:
    """Extract product name from SDS page."""
    lines = text.strip().split("\n")
    for line in lines[:8]:
        stripped = line.strip()
        if stripped and "SAFETY DATA SHEET" not in stripped.upper():
            if "Revision" not in stripped and "Preparation" not in stripped:
                cleaned = re.sub(r"^\d{4}\s+", "", stripped)
                if cleaned and len(cleaned) > 2 and len(cleaned) < 100:
                    return cleaned
    return None


def _chunk_tech_data(pages: list[str], filename: str) -> list[dict]:
    """Tech Data Sheets: chunk by product ('Technical Data Sheet' markers)."""
    chunks = []
    current_product = None
    current_content = []

    for text in pages:
        if not text:
            continue

        is_new_product = False
        product_name = None

        if "Technical Data Sheet" in text or "TECHNICAL DATA SHEET" in text.upper():
            lines = text.strip().split("\n")
            for line in lines[:6]:
                stripped = line.strip()
                if stripped and "Technical Data Sheet" not in stripped and "TECHNICAL DATA SHEET" not in stripped.upper():
                    if not re.match(r"^\d+\s+of\s+\d+$", stripped, re.IGNORECASE):
                        candidate = re.sub(r"\s*\d+\s*of\s*\d+\s*$", "", stripped).strip()
                        if candidate and len(candidate) > 2:
                            product_name = candidate
                            is_new_product = True
                            break

        if is_new_product and product_name != current_product:
            if current_product and current_content:
                content_text = "\n".join(current_content).strip()
                if len(content_text) >= MIN_CHUNK_LENGTH:
                    chunks.append({
                        "section_title": f"Tech Data: {current_product}",
                        "content": content_text[:MAX_CHUNK_LENGTH],
                        "source_doc": filename,
                        "domain": "product_info",
                    })
            current_product = product_name
            current_content = [text.strip()]
        else:
            current_content.append(text.strip())

    if current_product and current_content:
        content_text = "\n".join(current_content).strip()
        if len(content_text) >= MIN_CHUNK_LENGTH:
            chunks.append({
                "section_title": f"Tech Data: {current_product}",
                "content": content_text[:MAX_CHUNK_LENGTH],
                "source_doc": filename,
                "domain": "product_info",
            })

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Embedding + Upsert
# ─────────────────────────────────────────────────────────────────────────────

def embed_and_upsert(embedder, chunks: list[dict], existing_titles: set) -> dict:
    """
    Embed chunks in small batches and batch-insert to Supabase.
    Skips chunks whose (source_doc, section_title) is in existing_titles.
    Uses batch inserts (multiple rows per HTTP request) for speed.
    """
    from app.db.supabase_client import get_supabase_client
    client = get_supabase_client()
    stats = {"inserted": 0, "skipped": 0, "errors": 0}

    # Filter out already-existing chunks
    new_chunks = []
    for c in chunks:
        key = f"{c['source_doc']}||{c['section_title']}"
        if key in existing_titles:
            stats["skipped"] += 1
        else:
            new_chunks.append(c)

    if not new_chunks:
        print(f"  All {len(chunks)} chunks already exist — skipping")
        return stats

    total = len(new_chunks)
    print(f"  {stats['skipped']} already exist, {total} new to embed")

    # Process in batches: embed + batch insert
    INSERT_BATCH = 20  # Rows per Supabase insert call
    for i in range(0, total, EMBED_BATCH_SIZE):
        batch = new_chunks[i:i + EMBED_BATCH_SIZE]
        texts = [c["content"] for c in batch]

        raw_embeddings = list(embedder.embed(texts))
        rows = []
        for chunk, emb in zip(batch, raw_embeddings):
            vec = np.zeros(TARGET_DIM)
            vec[:EMBEDDING_DIM] = emb
            rows.append({
                "source_doc": chunk["source_doc"],
                "section_title": chunk["section_title"],
                "domain": chunk["domain"],
                "content": chunk["content"],
                "embedding": vec.tolist(),
            })

        # Batch insert
        for j in range(0, len(rows), INSERT_BATCH):
            batch_rows = rows[j:j + INSERT_BATCH]
            try:
                client.table("document_chunks").insert(batch_rows).execute()
                stats["inserted"] += len(batch_rows)
            except Exception as e:
                # Fallback: insert one by one to identify which row failed
                for row in batch_rows:
                    try:
                        client.table("document_chunks").insert(row).execute()
                        stats["inserted"] += 1
                    except Exception as e2:
                        stats["errors"] += 1
                        print(f"  ERROR: {row['section_title'][:50]}: {e2}")

        progress = min(i + EMBED_BATCH_SIZE, total)
        print(f"  Embedded {progress}/{total}: "
              f"[{batch[0]['section_title'][:60]}]")

        del raw_embeddings, rows
        gc.collect()

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("Bower Ag CowCare — Advisory Document Embedding Pipeline")
    print("=" * 70)

    if not ADVISORY_DIR.exists():
        print(f"ERROR: Advisory directory not found: {ADVISORY_DIR}")
        sys.exit(1)

    pdf_files = sorted(ADVISORY_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"ERROR: No PDF files found in {ADVISORY_DIR}")
        sys.exit(1)

    print(f"\nFound {len(pdf_files)} advisory PDFs:")
    for f in pdf_files:
        domain = classify_domain(f.name)
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {domain:20s} ({size_mb:5.1f} MB) <- {f.name}")

    # Load embedding model once
    from fastembed import TextEmbedding
    print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
    embedder = TextEmbedding(EMBEDDING_MODEL)

    # Pre-fetch existing chunk keys to avoid duplicate inserts
    from app.db.supabase_client import get_supabase_client
    client = get_supabase_client()
    existing_result = client.table("document_chunks").select("source_doc, section_title").limit(10000).execute()
    existing_titles = set()
    for row in (existing_result.data or []):
        existing_titles.add(f"{row['source_doc']}||{row['section_title']}")
    print(f"Found {len(existing_titles)} existing chunks in DB (will skip)")

    total_stats = {"inserted": 0, "skipped": 0, "errors": 0}
    all_domain_counts = {}

    for pdf_path in pdf_files:
        domain = classify_domain(pdf_path.name)
        print(f"\n{'─' * 70}")
        print(f"📄 {pdf_path.name} (domain={domain})")
        print(f"{'─' * 70}")

        try:
            # Extract pages using PyMuPDF (fast)
            pages = extract_pages(str(pdf_path))
            print(f"  Extracted text from {len(pages)} pages")

            # Chunk
            chunks = chunk_pages_by_section(pages, pdf_path.name, domain)
            del pages  # Free page text memory
            print(f"  Created {len(chunks)} chunks")

            if not chunks:
                print("  (no chunks — skipping)")
                continue

            for j, c in enumerate(chunks[:10]):
                print(f"    [{j+1}] {c['section_title'][:70]} "
                      f"({len(c['content'])} chars)")
            if len(chunks) > 10:
                print(f"    ... and {len(chunks) - 10} more")

            all_domain_counts[domain] = all_domain_counts.get(domain, 0) + len(chunks)

            # Embed and upsert
            stats = embed_and_upsert(embedder, chunks, existing_titles)
            for k in total_stats:
                total_stats[k] += stats[k]

            print(f"  ✅ Inserted: {stats['inserted']}, "
                  f"Skipped: {stats['skipped']}, "
                  f"Errors: {stats['errors']}")

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

        gc.collect()

    # Summary
    print("\n" + "=" * 70)
    print("EMBEDDING PIPELINE COMPLETE")
    print("=" * 70)

    print(f"\nInserted: {total_stats['inserted']}")
    print(f"Skipped: {total_stats['skipped']}")
    print(f"Errors: {total_stats['errors']}")

    print("\nChunks by domain:")
    for domain, count in sorted(all_domain_counts.items()):
        print(f"  {domain:20s}: {count}")

    total_chunks = sum(all_domain_counts.values())
    print(f"\nTotal chunks created: {total_chunks}")

    from app.db.supabase_client import get_supabase_client
    client = get_supabase_client()
    result = client.table("document_chunks").select("id", count="exact").execute()
    print(f"Rows in document_chunks table: {result.count}")


if __name__ == "__main__":
    main()
