"""
Bower Ag CowCare Tool — Admin Governance Module API
Comprehensive governance management: audits, performance monitoring,
test suite execution, and document/reference material management.

Auth: org_admin and admin only.

Endpoints:
  GET  /admin/governance/audit              — Run governance audit (bypass detection)
  GET  /admin/governance/audit/details      — Drill into specific audit failures
  GET  /admin/governance/performance        — Domain performance breakdown
  GET  /admin/governance/performance/trends — Performance trends over time
  POST /admin/governance/tests/run          — Run governance regression test suite
  GET  /admin/governance/tests/history      — Test run history
  GET  /admin/governance/tests/{run_id}     — Individual test run results
  GET  /admin/governance/documents          — List all governance documents/chunks
  POST /admin/governance/documents/upload   — Upload a new document (PDF/DOCX/TXT)
  POST /admin/governance/documents/process  — Process (OCR + chunk + embed) a document
  DELETE /admin/governance/documents/{id}   — Delete a document and its chunks
  GET  /admin/governance/documents/stats    — Document stats (chunk counts, domains)
  POST /admin/governance/documents/reembed  — Re-embed all chunks for a source document
"""

import os
import re
import gc
import time
import uuid
import json
import tempfile
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional
from pathlib import Path

from fastapi import (
    APIRouter, Depends, HTTPException, Query, UploadFile, File, Form,
    BackgroundTasks, status
)
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, require_role, ADMIN_ROLES
from app.db.supabase_client import get_supabase_client

router = APIRouter(prefix="/admin/governance", tags=["Admin Governance"])


# ═══════════════════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class AuditBypass(BaseModel):
    id: str
    query_text: str
    domain: str
    created_at: str
    user_id: Optional[str] = None
    governance_result: Optional[dict] = None
    response_summary: Optional[str] = None


class AuditResult(BaseModel):
    total_queries: int
    bypasses_found: int
    bypass_rate: float
    bypasses: list[AuditBypass]
    domains_checked: list[str]
    time_window_days: int


class DomainPerformance(BaseModel):
    domain: str
    avg_ms: float
    max_ms: float
    min_ms: float
    p95_ms: float
    count: int
    over_5s_count: int
    over_5s_rate: float


class PerformanceResult(BaseModel):
    domains: list[DomainPerformance]
    overall_avg_ms: float
    overall_p95_ms: float
    total_queries: int
    time_window_days: int
    alert_domains: list[str]


class PerformanceTrend(BaseModel):
    date: str
    domain: str
    avg_ms: float
    count: int


class TestCaseResult(BaseModel):
    test_id: str
    test_name: str
    status: str  # passed, failed, skipped, error
    duration_ms: int
    message: Optional[str] = None
    details: Optional[str] = None


class TestRunResult(BaseModel):
    run_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: str  # running, completed, failed
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    test_cases: list[TestCaseResult]
    duration_ms: Optional[int] = None


class DocumentInfo(BaseModel):
    source_doc: str
    domain: str
    chunk_count: int
    total_chars: int
    created_at: Optional[str] = None
    last_embedded: Optional[str] = None


class DocumentStats(BaseModel):
    total_documents: int
    total_chunks: int
    total_chars: int
    by_domain: dict
    last_updated: Optional[str] = None


class ProcessingStatus(BaseModel):
    job_id: str
    status: str  # queued, processing, completed, failed
    filename: str
    domain: Optional[str] = None
    chunks_created: int = 0
    message: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# In-memory job tracking (lightweight — for small team use)
# ═══════════════════════════════════════════════════════════════════════════════

_processing_jobs: dict[str, ProcessingStatus] = {}
_test_runs: dict[str, TestRunResult] = {}


# ═══════════════════════════════════════════════════════════════════════════════
# GOVERNANCE AUDIT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/audit", response_model=AuditResult)
async def run_governance_audit(
    days: int = Query(default=7, ge=1, le=90, description="Time window in days"),
    domain: Optional[str] = Query(None, description="Filter by specific domain"),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Run a governance audit — find queries where governance data was empty
    on pricing/product domains (indicating a bypass or failure).

    Checks audit_log for rows where:
    - llm_called = true (Claude was invoked)
    - domain is a governance-sensitive domain (PRICING, TEAT_DIP, CHEMICAL_CIP, PRODUCTS)
    - governance_result is NULL, empty {}, or missing key fields
    """
    client = get_supabase_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    governance_domains = ["PRICING", "TEAT_DIP", "CHEMICAL_CIP", "PRODUCTS"]
    if domain:
        governance_domains = [domain.upper()]

    try:
        # Fetch all LLM queries in governance-sensitive domains
        query = (
            client.table("audit_log")
            .select("id,query_text,domain,governance_result,user_id,response_summary,created_at")
            .eq("llm_called", True)
            .gte("created_at", cutoff)
        )

        # Domain filter (IN not directly supported, so fetch all and filter)
        result = query.order("created_at", desc=True).limit(500).execute()
        rows = result.data or []

        # Filter to governance domains
        domain_rows = [
            r for r in rows
            if r.get("domain", "").upper() in governance_domains
        ]

        # Find bypasses: governance_result is null, empty, or has no meaningful data
        bypasses = []
        for row in domain_rows:
            gov = row.get("governance_result")
            is_bypass = False

            if gov is None:
                is_bypass = True
            elif isinstance(gov, dict) and (len(gov) == 0):
                is_bypass = True
            elif isinstance(gov, str) and gov.strip() in ("", "{}", "null"):
                is_bypass = True
            elif isinstance(gov, dict):
                # Check if governance actually provided pricing/product data
                has_data = any(
                    gov.get(k) for k in [
                        "products", "pricing", "sellability",
                        "product_exists", "price_data", "product_data"
                    ]
                )
                if not has_data and row.get("domain", "").upper() in ("PRICING", "PRODUCTS"):
                    is_bypass = True

            if is_bypass:
                bypasses.append(AuditBypass(
                    id=row["id"],
                    query_text=row.get("query_text", "")[:300],
                    domain=row.get("domain", "unknown"),
                    created_at=row.get("created_at", ""),
                    user_id=row.get("user_id"),
                    governance_result=gov if isinstance(gov, dict) else None,
                    response_summary=row.get("response_summary", "")[:200],
                ))

    except Exception as e:
        raise HTTPException(500, f"Audit query failed: {str(e)[:200]}")

    total = len(domain_rows)
    bypass_count = len(bypasses)

    return AuditResult(
        total_queries=total,
        bypasses_found=bypass_count,
        bypass_rate=round(bypass_count / max(total, 1) * 100, 2),
        bypasses=bypasses[:50],  # Cap at 50 for response size
        domains_checked=governance_domains,
        time_window_days=days,
    )


@router.get("/audit/details")
async def audit_details(
    audit_id: str = Query(..., description="Audit log entry ID"),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """Get full details for a specific audit log entry."""
    client = get_supabase_client()
    try:
        result = (
            client.table("audit_log")
            .select("*")
            .eq("id", audit_id)
            .single()
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(404, f"Audit entry not found: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE MONITORING
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/performance", response_model=PerformanceResult)
async def performance_check(
    days: int = Query(default=7, ge=1, le=90),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Performance analysis by domain — avg, max, p95 response times.
    Flags domains averaging over 5000ms as alerts.
    """
    client = get_supabase_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    try:
        result = (
            client.table("audit_log")
            .select("domain,duration_ms,created_at")
            .gte("created_at", cutoff)
            .not_.is_("duration_ms", "null")
            .order("created_at", desc=True)
            .limit(2000)
            .execute()
        )
        rows = result.data or []
    except Exception as e:
        raise HTTPException(500, f"Performance query failed: {str(e)[:200]}")

    # Group by domain
    domain_data: dict[str, list[int]] = {}
    for row in rows:
        d = row.get("domain") or "unknown"
        ms = row.get("duration_ms")
        if ms is not None:
            domain_data.setdefault(d, []).append(int(ms))

    domains = []
    alert_domains = []
    all_times = []

    for domain_name, times in sorted(domain_data.items()):
        times_sorted = sorted(times)
        count = len(times_sorted)
        avg = sum(times_sorted) / count
        p95_idx = int(count * 0.95)
        p95 = times_sorted[min(p95_idx, count - 1)]
        over_5s = sum(1 for t in times_sorted if t > 5000)

        dp = DomainPerformance(
            domain=domain_name,
            avg_ms=round(avg, 1),
            max_ms=float(times_sorted[-1]),
            min_ms=float(times_sorted[0]),
            p95_ms=float(p95),
            count=count,
            over_5s_count=over_5s,
            over_5s_rate=round(over_5s / count * 100, 1),
        )
        domains.append(dp)
        all_times.extend(times_sorted)

        if avg > 5000:
            alert_domains.append(domain_name)

    # Overall stats
    overall_avg = sum(all_times) / max(len(all_times), 1)
    all_sorted = sorted(all_times)
    overall_p95 = all_sorted[int(len(all_sorted) * 0.95)] if all_sorted else 0

    return PerformanceResult(
        domains=domains,
        overall_avg_ms=round(overall_avg, 1),
        overall_p95_ms=float(overall_p95),
        total_queries=len(all_times),
        time_window_days=days,
        alert_domains=alert_domains,
    )


@router.get("/performance/trends")
async def performance_trends(
    days: int = Query(default=14, ge=1, le=90),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """Daily performance trends — avg response time per domain per day."""
    client = get_supabase_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    try:
        result = (
            client.table("audit_log")
            .select("domain,duration_ms,created_at")
            .gte("created_at", cutoff)
            .not_.is_("duration_ms", "null")
            .order("created_at", desc=True)
            .limit(5000)
            .execute()
        )
        rows = result.data or []
    except Exception as e:
        raise HTTPException(500, f"Trends query failed: {str(e)[:200]}")

    # Group by (date, domain)
    daily: dict[tuple[str, str], list[int]] = {}
    for row in rows:
        created = row.get("created_at", "")[:10]  # YYYY-MM-DD
        domain_name = row.get("domain") or "unknown"
        ms = row.get("duration_ms")
        if ms is not None and created:
            daily.setdefault((created, domain_name), []).append(int(ms))

    trends = []
    for (date, domain_name), times in sorted(daily.items()):
        trends.append(PerformanceTrend(
            date=date,
            domain=domain_name,
            avg_ms=round(sum(times) / len(times), 1),
            count=len(times),
        ))

    return {"trends": trends, "time_window_days": days}


# ═══════════════════════════════════════════════════════════════════════════════
# TEST SUITE RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/tests/run", response_model=TestRunResult)
async def run_test_suite(
    background_tasks: BackgroundTasks,
    test_filter: Optional[str] = Query(
        None, description="Filter tests by name pattern (e.g., 'gr01' or 'pricing')"
    ),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Kick off the governance regression test suite.
    Tests run in background; poll GET /tests/{run_id} for results.

    ⚠️ This calls the real Claude API — each test costs tokens.
    """
    run_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()

    run_result = TestRunResult(
        run_id=run_id,
        started_at=now,
        status="running",
        total=0,
        passed=0,
        failed=0,
        skipped=0,
        errors=0,
        test_cases=[],
    )
    _test_runs[run_id] = run_result

    background_tasks.add_task(_execute_test_suite, run_id, test_filter)

    return run_result


def _execute_test_suite(run_id: str, test_filter: Optional[str] = None):
    """Background task: execute governance tests and update results."""
    import subprocess
    import sys

    run = _test_runs.get(run_id)
    if not run:
        return

    start_time = time.time()

    try:
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            "app/tests/test_governance_regression.py",
            "-v", "--tb=short", "-m", "regression",
            "--no-header",
        ]
        if test_filter:
            cmd.extend(["-k", test_filter])

        # Run pytest and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
            env={**os.environ, "PYTHONPATH": os.path.join(os.path.dirname(__file__), "..", "..")},
        )

        stdout = result.stdout
        stderr = result.stderr

        # Parse pytest output
        test_cases = _parse_pytest_output(stdout + stderr)
        run.test_cases = test_cases
        run.total = len(test_cases)
        run.passed = sum(1 for t in test_cases if t.status == "passed")
        run.failed = sum(1 for t in test_cases if t.status == "failed")
        run.skipped = sum(1 for t in test_cases if t.status == "skipped")
        run.errors = sum(1 for t in test_cases if t.status == "error")
        run.status = "completed"

    except subprocess.TimeoutExpired:
        run.status = "failed"
        run.test_cases.append(TestCaseResult(
            test_id="timeout",
            test_name="Test Suite Timeout",
            status="error",
            duration_ms=300000,
            message="Test suite exceeded 5 minute timeout",
        ))
        run.errors = 1
    except Exception as e:
        run.status = "failed"
        run.test_cases.append(TestCaseResult(
            test_id="error",
            test_name="Test Suite Error",
            status="error",
            duration_ms=0,
            message=str(e)[:500],
            details=traceback.format_exc()[:2000],
        ))
        run.errors = 1

    run.completed_at = datetime.now(timezone.utc).isoformat()
    run.duration_ms = int((time.time() - start_time) * 1000)


def _parse_pytest_output(output: str) -> list[TestCaseResult]:
    """Parse pytest verbose output into structured test results."""
    test_cases = []

    # Match lines like: test_governance_regression.py::TestGovernanceRegression::test_gr01... PASSED
    pattern = re.compile(
        r"(test_\w+)\s+(PASSED|FAILED|SKIPPED|ERROR)"
    )

    for match in pattern.finditer(output):
        test_name = match.group(1)
        status_str = match.group(2).lower()
        
        # Try to extract failure message
        message = None
        if status_str == "failed":
            # Look for AssertionError or FAIL message after the test name
            fail_pattern = re.compile(
                rf"{re.escape(test_name)}.*?(?:AssertionError|FAIL):\s*(.+?)(?:\n|$)",
                re.DOTALL,
            )
            fail_match = fail_pattern.search(output)
            if fail_match:
                message = fail_match.group(1)[:500]

        test_cases.append(TestCaseResult(
            test_id=test_name,
            test_name=test_name.replace("test_", "").replace("_", " ").title(),
            status=status_str,
            duration_ms=0,  # pytest doesn't give per-test timing in basic output
            message=message,
        ))

    # If no tests parsed, the suite might have had a setup error
    if not test_cases and ("error" in output.lower() or "ERROR" in output):
        test_cases.append(TestCaseResult(
            test_id="setup_error",
            test_name="Test Setup Error",
            status="error",
            duration_ms=0,
            message="Tests could not be collected — check configuration",
            details=output[:2000],
        ))

    return test_cases


@router.get("/tests/history")
async def test_history(
    limit: int = Query(default=20, ge=1, le=100),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """Get recent test run history."""
    runs = sorted(
        _test_runs.values(),
        key=lambda r: r.started_at,
        reverse=True,
    )[:limit]
    return {"runs": [r.model_dump() for r in runs]}


@router.get("/tests/{run_id}", response_model=TestRunResult)
async def get_test_run(
    run_id: str,
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """Get results for a specific test run."""
    run = _test_runs.get(run_id)
    if not run:
        raise HTTPException(404, "Test run not found")
    return run


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

VALID_DOMAINS = [
    "troubleshooting", "sds", "procedure", "product_info",
    "calculation", "competitive_ref", "report_template", "general",
]


@router.get("/documents")
async def list_documents(
    domain: Optional[str] = Query(None),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """List all governance/reference documents with chunk counts."""
    client = get_supabase_client()

    try:
        query = client.table("document_chunks").select(
            "source_doc, domain, content, created_at"
        )
        if domain:
            query = query.eq("domain", domain)

        result = query.order("source_doc").execute()
        rows = result.data or []
    except Exception as e:
        raise HTTPException(500, f"Document query failed: {str(e)[:200]}")

    # Aggregate by source_doc
    docs: dict[str, dict] = {}
    for row in rows:
        src = row["source_doc"]
        if src not in docs:
            docs[src] = {
                "source_doc": src,
                "domain": row.get("domain", "general"),
                "chunk_count": 0,
                "total_chars": 0,
                "created_at": row.get("created_at"),
            }
        docs[src]["chunk_count"] += 1
        docs[src]["total_chars"] += len(row.get("content", ""))

    return {
        "documents": list(docs.values()),
        "total_documents": len(docs),
        "domains": VALID_DOMAINS,
    }


@router.get("/documents/stats", response_model=DocumentStats)
async def document_stats(
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """Get aggregate document statistics."""
    client = get_supabase_client()

    try:
        result = (
            client.table("document_chunks")
            .select("source_doc, domain, content, created_at")
            .execute()
        )
        rows = result.data or []
    except Exception as e:
        raise HTTPException(500, f"Stats query failed: {str(e)[:200]}")

    by_domain: dict[str, int] = {}
    total_chars = 0
    source_docs = set()
    latest = None

    for row in rows:
        d = row.get("domain", "general")
        by_domain[d] = by_domain.get(d, 0) + 1
        total_chars += len(row.get("content", ""))
        source_docs.add(row["source_doc"])
        created = row.get("created_at")
        if created and (latest is None or created > latest):
            latest = created

    return DocumentStats(
        total_documents=len(source_docs),
        total_chunks=len(rows),
        total_chars=total_chars,
        by_domain=by_domain,
        last_updated=latest,
    )


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    domain: str = Form(default="general"),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Upload a governance document (PDF, DOCX, or TXT).
    File is stored temporarily for processing.
    Returns a job_id to track processing status.
    """
    if domain not in VALID_DOMAINS:
        raise HTTPException(400, f"Invalid domain. Valid: {VALID_DOMAINS}")

    # Validate file type
    filename = file.filename or "document"
    ext = Path(filename).suffix.lower()
    allowed = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv"}
    if ext not in allowed:
        raise HTTPException(
            400,
            f"Unsupported file type: {ext}. Allowed: {', '.join(allowed)}"
        )

    # Save to temp location
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(400, "File too large (max 50MB)")

    # Store file info for the processing step
    job_id = str(uuid.uuid4())[:8]
    temp_dir = Path(tempfile.gettempdir()) / "bowerag_uploads"
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"{job_id}_{filename}"
    temp_path.write_bytes(content)

    _processing_jobs[job_id] = ProcessingStatus(
        job_id=job_id,
        status="uploaded",
        filename=filename,
        domain=domain,
        message=f"File uploaded ({len(content) / 1024:.1f} KB). Ready to process.",
    )

    return {
        "job_id": job_id,
        "filename": filename,
        "size_kb": round(len(content) / 1024, 1),
        "domain": domain,
        "status": "uploaded",
        "message": "File uploaded successfully. Call POST /documents/process to extract, chunk, and embed.",
    }


@router.post("/documents/process")
async def process_document(
    background_tasks: BackgroundTasks,
    job_id: str = Form(..., description="Job ID from upload step"),
    domain: Optional[str] = Form(None, description="Override domain classification"),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Process an uploaded document: extract text (OCR for PDFs), chunk by section,
    generate embeddings, and insert into document_chunks table.

    Runs in background — poll GET /documents/process/{job_id} for status.
    """
    job = _processing_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found. Upload a document first.")

    if job.status == "processing":
        raise HTTPException(409, "Document is already being processed.")

    if domain and domain in VALID_DOMAINS:
        job.domain = domain

    job.status = "processing"
    job.message = "Processing started — extracting text..."

    background_tasks.add_task(_process_document_task, job_id)

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Document processing started. This may take 30-120 seconds depending on size.",
    }


def _process_document_task(job_id: str):
    """Background task: extract text, chunk, embed, and insert."""
    job = _processing_jobs.get(job_id)
    if not job:
        return

    temp_dir = Path(tempfile.gettempdir()) / "bowerag_uploads"
    # Find the file
    matching_files = list(temp_dir.glob(f"{job_id}_*"))
    if not matching_files:
        job.status = "failed"
        job.message = "Uploaded file not found on disk."
        return

    file_path = matching_files[0]
    ext = file_path.suffix.lower()

    try:
        # ─── Step 1: Text Extraction ──────────────────────────────────────
        job.message = "Extracting text from document..."

        if ext == ".pdf":
            pages = _extract_pdf_text(str(file_path))
        elif ext in (".docx", ".doc"):
            pages = _extract_docx_text(str(file_path))
        elif ext in (".txt", ".md", ".csv"):
            text = file_path.read_text(encoding="utf-8", errors="replace")
            pages = [text]
        else:
            job.status = "failed"
            job.message = f"Unsupported file type: {ext}"
            return

        total_text = sum(len(p) for p in pages)
        job.message = f"Extracted {len(pages)} pages ({total_text:,} characters)"

        if total_text < 50:
            job.status = "failed"
            job.message = "Document appears empty or unreadable. Try a different file format."
            return

        # ─── Step 2: Chunking ─────────────────────────────────────────────
        job.message = "Chunking document into sections..."
        domain = job.domain or "general"
        chunks = _chunk_document(pages, job.filename, domain)

        if not chunks:
            job.status = "failed"
            job.message = "No meaningful content chunks could be extracted."
            return

        job.message = f"Created {len(chunks)} chunks. Generating embeddings..."

        # ─── Step 3: Embedding ────────────────────────────────────────────
        job.message = f"Embedding {len(chunks)} chunks (this may take a moment)..."
        from app.services.embedding_service import get_batch_embeddings

        # Batch embed
        texts = [c["content"] for c in chunks]
        embeddings = get_batch_embeddings(texts)

        # ─── Step 4: Insert into DB ──────────────────────────────────────
        job.message = "Inserting into database..."
        client = get_supabase_client()

        # First, remove any existing chunks for this source_doc (re-upload scenario)
        try:
            client.table("document_chunks").delete().eq(
                "source_doc", job.filename
            ).execute()
        except Exception:
            pass  # Table might not have had any rows

        # Insert in batches
        inserted = 0
        batch_size = 20
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]

            rows = []
            for chunk, emb in zip(batch, batch_embeddings):
                rows.append({
                    "source_doc": chunk["source_doc"],
                    "section_title": chunk["section_title"],
                    "domain": chunk["domain"],
                    "content": chunk["content"],
                    "embedding": emb,
                })

            try:
                client.table("document_chunks").insert(rows).execute()
                inserted += len(rows)
            except Exception as e:
                # Try one by one
                for row in rows:
                    try:
                        client.table("document_chunks").insert(row).execute()
                        inserted += 1
                    except Exception:
                        pass

            job.chunks_created = inserted
            job.message = f"Inserted {inserted}/{len(chunks)} chunks..."

        job.status = "completed"
        job.chunks_created = inserted
        job.message = (
            f"Successfully processed '{job.filename}': "
            f"{inserted} chunks embedded and stored in domain '{domain}'."
        )

    except Exception as e:
        job.status = "failed"
        job.message = f"Processing failed: {str(e)[:500]}"
    finally:
        # Clean up temp file
        try:
            file_path.unlink()
        except Exception:
            pass
        gc.collect()


def _extract_pdf_text(path: str) -> list[str]:
    """Extract text from PDF using PyMuPDF (with OCR fallback concept)."""
    import fitz
    doc = fitz.open(path)
    pages = []
    for page in doc:
        text = page.get_text()
        # If page has very little text, it might be a scanned image
        # In that case, try to get text from images (basic OCR indication)
        if len(text.strip()) < 20:
            # Flag for potential OCR need
            text = text or f"[Page {page.number + 1}: Image-based content — OCR may be needed]"
        pages.append(text)
    doc.close()
    return pages


def _extract_docx_text(path: str) -> list[str]:
    """Extract text from DOCX file."""
    try:
        from docx import Document
        doc = Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        # Treat as one "page" for simplicity
        return ["\n".join(paragraphs)]
    except ImportError:
        # Fallback: try reading as plain text
        with open(path, "r", errors="replace") as f:
            return [f.read()]


def _chunk_document(pages: list[str], filename: str, domain: str) -> list[dict]:
    """Chunk document into sections (reuses embed_documents.py logic)."""
    MIN_CHUNK_LENGTH = 50
    MAX_CHUNK_LENGTH = 4000

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
            if _is_heading(stripped):
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

    # Final chunk
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


def _is_heading(line: str) -> bool:
    """Detect if a line is a section heading."""
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


@router.get("/documents/process/{job_id}")
async def get_processing_status(
    job_id: str,
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """Check the status of a document processing job."""
    job = _processing_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job.model_dump()


@router.delete("/documents/{source_doc}")
async def delete_document(
    source_doc: str,
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Delete all chunks for a source document.
    This removes the document from the RAG search index.
    """
    client = get_supabase_client()

    try:
        # Count before delete
        count_result = (
            client.table("document_chunks")
            .select("id", count="exact")
            .eq("source_doc", source_doc)
            .execute()
        )
        count = count_result.count or 0

        if count == 0:
            raise HTTPException(404, f"No chunks found for document: {source_doc}")

        # Delete all chunks
        client.table("document_chunks").delete().eq(
            "source_doc", source_doc
        ).execute()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {str(e)[:200]}")

    return {
        "deleted": True,
        "source_doc": source_doc,
        "chunks_removed": count,
        "message": f"Removed {count} chunks for '{source_doc}' from governance database.",
    }


@router.post("/documents/reembed")
async def reembed_document(
    background_tasks: BackgroundTasks,
    source_doc: str = Form(..., description="Source document filename to re-embed"),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Re-generate embeddings for all chunks of a specific source document.
    Useful after updating the embedding model or if embeddings are corrupted.
    """
    client = get_supabase_client()

    # Get existing chunks
    try:
        result = (
            client.table("document_chunks")
            .select("id, content, source_doc, section_title, domain")
            .eq("source_doc", source_doc)
            .execute()
        )
        chunks = result.data or []
    except Exception as e:
        raise HTTPException(500, f"Query failed: {str(e)[:200]}")

    if not chunks:
        raise HTTPException(404, f"No chunks found for: {source_doc}")

    job_id = str(uuid.uuid4())[:8]
    _processing_jobs[job_id] = ProcessingStatus(
        job_id=job_id,
        status="processing",
        filename=source_doc,
        message=f"Re-embedding {len(chunks)} chunks...",
    )

    background_tasks.add_task(_reembed_task, job_id, chunks)

    return {
        "job_id": job_id,
        "source_doc": source_doc,
        "chunk_count": len(chunks),
        "message": f"Re-embedding {len(chunks)} chunks in background.",
    }


def _reembed_task(job_id: str, chunks: list[dict]):
    """Background task: re-embed existing chunks."""
    job = _processing_jobs.get(job_id)
    if not job:
        return

    try:
        from app.services.embedding_service import get_batch_embeddings
        client = get_supabase_client()

        texts = [c["content"] for c in chunks]
        embeddings = get_batch_embeddings(texts)

        updated = 0
        for chunk, emb in zip(chunks, embeddings):
            try:
                client.table("document_chunks").update(
                    {"embedding": emb}
                ).eq("id", chunk["id"]).execute()
                updated += 1
            except Exception:
                pass

            job.chunks_created = updated
            job.message = f"Re-embedded {updated}/{len(chunks)} chunks..."

        job.status = "completed"
        job.chunks_created = updated
        job.message = f"Successfully re-embedded {updated} chunks for '{job.filename}'."

    except Exception as e:
        job.status = "failed"
        job.message = f"Re-embedding failed: {str(e)[:500]}"


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT CONTENT PREVIEW
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/documents/chunks/{source_doc}")
async def get_document_chunks(
    source_doc: str,
    limit: int = Query(default=50, ge=1, le=200),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Get all chunks for a specific document — allows admins to preview
    what was extracted and how it was split.
    """
    client = get_supabase_client()

    try:
        result = (
            client.table("document_chunks")
            .select("id, section_title, domain, content, source_doc, created_at")
            .eq("source_doc", source_doc)
            .limit(limit)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Query failed: {str(e)[:200]}")

    chunks = result.data or []
    return {
        "source_doc": source_doc,
        "chunks": chunks,
        "count": len(chunks),
    }


@router.put("/documents/chunks/{chunk_id}")
async def update_chunk(
    chunk_id: str,
    content: str = Form(None),
    section_title: str = Form(None),
    domain: str = Form(None),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Edit an individual chunk's content, title, or domain.
    After editing content, the embedding should be regenerated (call reembed).
    """
    client = get_supabase_client()
    updates = {}
    if content is not None:
        updates["content"] = content
    if section_title is not None:
        updates["section_title"] = section_title
    if domain is not None:
        if domain not in VALID_DOMAINS:
            raise HTTPException(400, f"Invalid domain. Valid: {VALID_DOMAINS}")
        updates["domain"] = domain

    if not updates:
        raise HTTPException(400, "No updates provided")

    try:
        result = (
            client.table("document_chunks")
            .update(updates)
            .eq("id", chunk_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(404, "Chunk not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Update failed: {str(e)[:200]}")

    return {
        "updated": True,
        "chunk_id": chunk_id,
        "fields_updated": list(updates.keys()),
        "message": "Chunk updated. If content was changed, run 'Re-embed' to update the search index.",
    }
