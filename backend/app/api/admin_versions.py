"""
Bower Ag CowCare Tool — Admin Version Log API
Sprint 11: Version/release log management.

GET: admin_manager, org_admin
POST: org_admin ONLY (creating releases is a privileged operation)
EXPORT: admin_manager, org_admin

Auth varies per endpoint — see docstrings.
"""

import csv
import io
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.core.auth import CurrentUser, require_role, ADMIN_ROLES
from app.db.supabase_client import get_supabase_client

router = APIRouter(prefix="/admin/versions", tags=["Admin Versions"])


# ─── Models ───────────────────────────────────────────────────────────────────

class VersionLogItem(BaseModel):
    id: str
    version_tag: str
    release_date: Optional[str] = None
    release_notes: Optional[str] = None
    breaking_changes: Optional[str] = None
    bugs_resolved: Optional[list[str]] = None
    deployed_by: Optional[str] = None
    created_at: str


class CreateVersionRequest(BaseModel):
    version_tag: str = Field(..., min_length=1)
    release_notes: Optional[str] = None
    breaking_changes: Optional[str] = None
    bugs_resolved: Optional[list[str]] = None

    @field_validator("version_tag")
    @classmethod
    def validate_version_tag(cls, v: str) -> str:
        """Validate version_tag format: vX.Y.Z or vX.Y.Z-beta"""
        pattern = r"^v\d+\.\d+\.\d+(-beta)?$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid version tag '{v}'. Expected format: vX.Y.Z or vX.Y.Z-beta"
            )
        return v


# ─── GET /admin/versions ──────────────────────────────────────────────────────

@router.get("", response_model=list[VersionLogItem])
async def list_versions(
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """List all version_log rows, newest first."""
    client = get_supabase_client()

    try:
        result = (
            client.table("version_log")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    return [
        VersionLogItem(
            id=r["id"],
            version_tag=r["version_tag"],
            release_date=str(r.get("release_date", "")) if r.get("release_date") else None,
            release_notes=r.get("release_notes"),
            breaking_changes=r.get("breaking_changes"),
            bugs_resolved=r.get("bugs_resolved"),
            deployed_by=r.get("deployed_by"),
            created_at=str(r.get("created_at", "")),
        )
        for r in (result.data or [])
    ]


# ─── POST /admin/versions ────────────────────────────────────────────────────

@router.post("", response_model=VersionLogItem, status_code=201)
async def create_version(
    body: CreateVersionRequest,
    user: CurrentUser = Depends(require_role(["org_admin"])),
):
    """
    Create a new version_log entry.

    Auth: org_admin ONLY.
    Validates version_tag format (vX.Y.Z or vX.Y.Z-beta).
    Sets deployed_by to current user.
    """
    client = get_supabase_client()

    row = {
        "version_tag": body.version_tag,
        "deployed_by": user.id,
    }
    if body.release_notes:
        row["release_notes"] = body.release_notes
    if body.breaking_changes:
        row["breaking_changes"] = body.breaking_changes
    if body.bugs_resolved:
        row["bugs_resolved"] = body.bugs_resolved

    try:
        result = client.table("version_log").insert(row).execute()
    except Exception as e:
        raise HTTPException(500, f"Failed to create version: {str(e)[:200]}")

    if not result.data:
        raise HTTPException(500, "Failed to create version — no data returned.")

    created = result.data[0]
    return VersionLogItem(
        id=created["id"],
        version_tag=created["version_tag"],
        release_date=str(created.get("release_date", "")) if created.get("release_date") else None,
        release_notes=created.get("release_notes"),
        breaking_changes=created.get("breaking_changes"),
        bugs_resolved=created.get("bugs_resolved"),
        deployed_by=created.get("deployed_by"),
        created_at=str(created.get("created_at", "")),
    )


# ─── GET /admin/versions/export ──────────────────────────────────────────────

@router.get("/export")
async def export_versions(
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """Export version history as CSV (streaming)."""
    client = get_supabase_client()

    try:
        result = (
            client.table("version_log")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        versions = result.data or []
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)

        columns = [
            "id", "version_tag", "release_date", "release_notes",
            "breaking_changes", "bugs_resolved", "deployed_by", "created_at",
        ]
        writer.writerow(columns)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for v in versions:
            row = [
                v.get("id", ""),
                v.get("version_tag", ""),
                str(v.get("release_date", "")) if v.get("release_date") else "",
                v.get("release_notes", "") or "",
                v.get("breaking_changes", "") or "",
                ",".join(v.get("bugs_resolved") or []),
                v.get("deployed_by", "") or "",
                str(v.get("created_at", "")) if v.get("created_at") else "",
            ]
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=version_history.csv"},
    )
