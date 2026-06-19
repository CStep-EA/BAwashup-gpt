"""
Bower Ag CowCare Tool — Admin Bug Reports API
Sprint 11: Bug triage, update, and CSV export for admin portal.

Uses the bug_reports table (migration 003_feedback_bugs.sql).
Note: The 003 migration uses slightly different column names than 001,
so we normalize in the API layer.

Auth: admin_manager, org_admin.
"""

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import CurrentUser, require_role, ADMIN_ROLES
from app.db.supabase_client import get_supabase_client
from app.services.audit_service import fire_and_forget_audit

router = APIRouter(prefix="/admin/bugs", tags=["Admin Bugs"])


# ─── Response Models ──────────────────────────────────────────────────────────

class BugReportItem(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    severity: str
    status: str
    version_tag: Optional[str] = None
    reporter_name: Optional[str] = None
    reporter_email: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    fix_notes: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str


class BugUpdateRequest(BaseModel):
    status: Optional[str] = None
    fix_notes: Optional[str] = None
    severity: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Map from 003 migration columns to sprint 11 spec
# 003 uses: user_id, what_happened, admin_notes, location_code, session_id, app_version
# 001 uses: reporter_id, description, fix_notes, steps_to_reproduce, etc.
# We handle both schemas gracefully.


def _normalize_bug(row: dict, profiles_map: dict) -> dict:
    """Normalize a bug_reports row to our response format."""
    reporter_id = row.get("reporter_id") or row.get("user_id")
    profile = profiles_map.get(reporter_id, {})

    return {
        "id": row["id"],
        "title": row.get("title", ""),
        "description": row.get("description") or row.get("what_happened"),
        "severity": row.get("severity", "medium"),
        "status": row.get("status", "open"),
        "version_tag": row.get("version_tag") or row.get("app_version"),
        "reporter_name": profile.get("full_name"),
        "reporter_email": None,  # Populated separately if needed
        "steps_to_reproduce": row.get("steps_to_reproduce"),
        "expected_behavior": row.get("expected_behavior"),
        "actual_behavior": row.get("actual_behavior"),
        "fix_notes": row.get("fix_notes") or row.get("admin_notes"),
        "resolved_at": str(row["resolved_at"]) if row.get("resolved_at") else None,
        "created_at": str(row.get("created_at", "")),
    }


# ─── GET /admin/bugs ──────────────────────────────────────────────────────────

@router.get("", response_model=list[BugReportItem])
async def list_bugs(
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    version_tag: Optional[str] = Query(None),
    days: Optional[int] = Query(None, ge=1, le=365),
    search: Optional[str] = Query(None),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    List bug reports with optional filters.

    Default sort: severity (critical first) then created_at DESC.
    """
    client = get_supabase_client()

    try:
        query = client.table("bug_reports").select("*")

        if severity:
            query = query.eq("severity", severity)
        if status_filter:
            query = query.eq("status", status_filter)
        if days:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            query = query.gte("created_at", cutoff)

        result = query.order("created_at", desc=True).execute()
        bugs = result.data or []

    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    # Fetch reporter profiles
    reporter_ids = list({
        b.get("reporter_id") or b.get("user_id")
        for b in bugs
        if b.get("reporter_id") or b.get("user_id")
    })
    profiles_map: dict = {}
    if reporter_ids:
        try:
            profiles_result = (
                client.table("profiles")
                .select("id,full_name")
                .in_("id", reporter_ids)
                .execute()
            )
            profiles_map = {p["id"]: p for p in (profiles_result.data or [])}
        except Exception:
            pass

    # Normalize and filter
    normalized = [_normalize_bug(b, profiles_map) for b in bugs]

    # Version tag filter (handle both column names)
    if version_tag:
        normalized = [
            n for n in normalized
            if n.get("version_tag") and version_tag.lower() in n["version_tag"].lower()
        ]

    # Search filter
    if search:
        search_lower = search.lower()
        normalized = [
            n for n in normalized
            if (search_lower in (n.get("title") or "").lower()
                or search_lower in (n.get("description") or "").lower())
        ]

    # Sort: severity first, then created_at DESC
    normalized.sort(
        key=lambda b: (
            SEVERITY_ORDER.get(b.get("severity", "medium"), 99),
            b.get("created_at", ""),
        ),
    )
    # Reverse created_at within same severity
    normalized.sort(
        key=lambda b: SEVERITY_ORDER.get(b.get("severity", "medium"), 99)
    )

    return [BugReportItem(**n) for n in normalized]


# ─── GET /admin/bugs/export ────────────────────────────────────────────────────

@router.get("/export")
async def export_bugs(
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    version_tag: Optional[str] = Query(None),
    days: Optional[int] = Query(None, ge=1, le=365),
    search: Optional[str] = Query(None),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """Export bug reports as CSV (streaming)."""
    # Reuse list logic
    bugs = await list_bugs(
        severity=severity,
        status_filter=status_filter,
        version_tag=version_tag,
        days=days,
        search=search,
        user=user,
    )

    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        # Header row
        columns = [
            "id", "title", "severity", "status", "reporter_name",
            "version_tag", "description", "steps_to_reproduce",
            "expected_behavior", "actual_behavior", "fix_notes",
            "created_at", "resolved_at",
        ]
        writer.writerow(columns)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Data rows
        for bug in bugs:
            bug_dict = bug.model_dump() if hasattr(bug, "model_dump") else bug.dict()
            row = [bug_dict.get(col, "") or "" for col in columns]
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bug_reports.csv"},
    )


# ─── GET /admin/bugs/{bug_id} ─────────────────────────────────────────────────

@router.get("/{bug_id}", response_model=BugReportItem)
async def get_bug(
    bug_id: str,
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """Get full bug report detail."""
    client = get_supabase_client()

    try:
        result = (
            client.table("bug_reports")
            .select("*")
            .eq("id", bug_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    if not result.data:
        raise HTTPException(404, "Bug report not found.")

    bug = result.data[0]

    # Fetch reporter profile
    reporter_id = bug.get("reporter_id") or bug.get("user_id")
    profiles_map: dict = {}
    if reporter_id:
        try:
            profile_result = (
                client.table("profiles")
                .select("id,full_name")
                .eq("id", reporter_id)
                .execute()
            )
            if profile_result.data:
                profiles_map[reporter_id] = profile_result.data[0]
        except Exception:
            pass

    return BugReportItem(**_normalize_bug(bug, profiles_map))


# ─── PATCH /admin/bugs/{bug_id} ───────────────────────────────────────────────

@router.patch("/{bug_id}", response_model=BugReportItem)
async def update_bug(
    bug_id: str,
    body: BugUpdateRequest,
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Update a bug report's status, severity, or fix_notes.

    If status changes to 'resolved' or 'fixed':
      - Auto-set resolved_at = now()
      - Auto-set resolved_by = current_user.id (if column exists)
    """
    client = get_supabase_client()

    # Fetch current bug
    try:
        current_result = (
            client.table("bug_reports")
            .select("*")
            .eq("id", bug_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    if not current_result.data:
        raise HTTPException(404, "Bug report not found.")

    current_bug = current_result.data[0]

    # Build patch
    patch: dict = {}
    if body.status is not None:
        patch["status"] = body.status
    if body.fix_notes is not None:
        # Handle both column names
        if "admin_notes" in current_bug and "fix_notes" not in current_bug:
            patch["admin_notes"] = body.fix_notes
        else:
            patch["fix_notes"] = body.fix_notes
    if body.severity is not None:
        patch["severity"] = body.severity

    if not patch:
        raise HTTPException(400, "No fields to update.")

    # Auto-set resolved_at when resolving
    resolving_statuses = {"resolved", "fixed"}
    if body.status and body.status in resolving_statuses:
        now = datetime.now(timezone.utc).isoformat()
        patch["resolved_at"] = now
        # Try to set resolved_by if column exists in this schema version
        if "resolved_by" in current_bug:
            patch["resolved_by"] = user.id

    try:
        update_result = (
            client.table("bug_reports")
            .update(patch)
            .eq("id", bug_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to update bug: {str(e)[:200]}")

    updated_bug = update_result.data[0] if update_result.data else {**current_bug, **patch}

    # Fetch reporter profile
    reporter_id = updated_bug.get("reporter_id") or updated_bug.get("user_id")
    profiles_map: dict = {}
    if reporter_id:
        try:
            profile_result = (
                client.table("profiles")
                .select("id,full_name")
                .eq("id", reporter_id)
                .execute()
            )
            if profile_result.data:
                profiles_map[reporter_id] = profile_result.data[0]
        except Exception:
            pass

    # Audit log
    fire_and_forget_audit(
        user_id=user.id,
        action="bug_updated",
        domain="admin",
        query_text=bug_id,
        governance_result={
            "bug_id": bug_id,
            "before": {
                "status": current_bug.get("status"),
                "severity": current_bug.get("severity"),
            },
            "after": {
                "status": updated_bug.get("status"),
                "severity": updated_bug.get("severity"),
            },
        },
    )

    return BugReportItem(**_normalize_bug(updated_bug, profiles_map))
