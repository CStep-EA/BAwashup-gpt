"""
Bower Ag CowCare Tool — Admin Audit Log API
Sprint 11: Raw audit log access for governance compliance.

⚠️ org_admin ONLY — this is raw governance data, not for admin_manager.

Provides paginated access to audit_log with profile info joined,
plus CSV export for compliance reports.
"""

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import CurrentUser, require_role
from app.db.supabase_client import get_supabase_client

router = APIRouter(prefix="/admin/audit", tags=["Admin Audit"])


# ─── Response Models ──────────────────────────────────────────────────────────

class AuditLogItem(BaseModel):
    id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    domain: Optional[str] = None
    query_text: Optional[str] = None
    location_locked: Optional[str] = None
    governance_result: Optional[dict] = None
    llm_called: bool
    response_summary: Optional[str] = None
    feedback_rating: Optional[int] = None
    duration_ms: Optional[int] = None
    app_version: Optional[str] = None
    created_at: str


# ─── GET /admin/audit ─────────────────────────────────────────────────────────

@router.get("", response_model=list[AuditLogItem])
async def list_audit_logs(
    user_id: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = Depends(require_role(["org_admin"])),
):
    """
    Raw audit log access — org_admin ONLY.

    Returns audit_log rows with profile info joined.
    """
    client = get_supabase_client()

    try:
        query = (
            client.table("audit_log")
            .select("*")
        )

        if user_id:
            query = query.eq("user_id", user_id)
        if domain:
            query = query.eq("domain", domain)
        if action:
            query = query.eq("action", action)
        if start_date:
            query = query.gte("created_at", f"{start_date}T00:00:00Z")
        if end_date:
            query = query.lte("created_at", f"{end_date}T23:59:59Z")

        result = (
            query
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = result.data or []

    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    # Fetch profile info for user_ids
    user_ids = list({r["user_id"] for r in rows if r.get("user_id")})
    profiles_map: dict = {}
    if user_ids:
        try:
            profiles_result = (
                client.table("profiles")
                .select("id,full_name,role")
                .in_("id", user_ids)
                .execute()
            )
            profiles_map = {p["id"]: p for p in (profiles_result.data or [])}
        except Exception:
            pass

    return [
        AuditLogItem(
            id=r["id"],
            user_id=r.get("user_id"),
            user_name=profiles_map.get(r.get("user_id"), {}).get("full_name"),
            user_role=profiles_map.get(r.get("user_id"), {}).get("role"),
            action=r["action"],
            domain=r.get("domain"),
            query_text=r.get("query_text"),
            location_locked=r.get("location_locked"),
            governance_result=r.get("governance_result"),
            llm_called=r.get("llm_called", False),
            response_summary=r.get("response_summary"),
            feedback_rating=r.get("feedback_rating"),
            duration_ms=r.get("duration_ms"),
            app_version=r.get("app_version"),
            created_at=str(r.get("created_at", "")),
        )
        for r in rows
    ]


# ─── GET /admin/audit/export ──────────────────────────────────────────────────

@router.get("/export")
async def export_audit_logs(
    user_id: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(default=500, ge=1, le=500),
    user: CurrentUser = Depends(require_role(["org_admin"])),
):
    """Export audit logs as CSV (streaming) — org_admin ONLY."""
    audit_rows = await list_audit_logs(
        user_id=user_id,
        domain=domain,
        action=action,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        user=user,
    )

    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)

        columns = [
            "id", "user_id", "user_name", "user_role", "action", "domain",
            "query_text", "location_locked", "llm_called", "response_summary",
            "feedback_rating", "duration_ms", "app_version", "created_at",
        ]
        writer.writerow(columns)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in audit_rows:
            row_dict = row.model_dump() if hasattr(row, "model_dump") else row.dict()
            csv_row = [str(row_dict.get(col, "") or "") for col in columns]
            writer.writerow(csv_row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )
