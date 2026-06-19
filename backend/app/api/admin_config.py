"""
Bower Ag CowCare Tool — Admin System Config API
Sprint 11: Feature toggles and system settings management.

The system_config table has an `editable_by` column that controls
which role can modify each key:
  - 'admin_manager' → both admin_manager and org_admin can edit
  - 'org_admin' → only org_admin can edit

Auth: admin_manager, org_admin.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import CurrentUser, require_role, ADMIN_ROLES
from app.db.supabase_client import get_supabase_client
from app.services.audit_service import fire_and_forget_audit

router = APIRouter(prefix="/admin/config", tags=["Admin Config"])


# ─── Response Models ──────────────────────────────────────────────────────────

class ConfigItem(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None
    editable_by: str
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None


class UpdateConfigRequest(BaseModel):
    value: Any


# ─── GET /admin/config ────────────────────────────────────────────────────────

@router.get("", response_model=list[ConfigItem])
async def list_config(
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """Return all system_config rows including editable_by field."""
    client = get_supabase_client()

    try:
        result = (
            client.table("system_config")
            .select("key,value,description,editable_by,updated_by,updated_at")
            .order("key")
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    return [
        ConfigItem(
            key=r["key"],
            value=r.get("value"),
            description=r.get("description"),
            editable_by=r.get("editable_by", "admin_manager"),
            updated_by=r.get("updated_by"),
            updated_at=str(r["updated_at"]) if r.get("updated_at") else None,
        )
        for r in (result.data or [])
    ]


# ─── PATCH /admin/config/{key} ────────────────────────────────────────────────

@router.patch("/{key}", response_model=ConfigItem)
async def update_config(
    key: str,
    body: UpdateConfigRequest,
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Update a system config value.

    Guard: if editable_by='org_admin' and caller is admin_manager → 403
    """
    client = get_supabase_client()

    # Fetch current config row
    try:
        current_result = (
            client.table("system_config")
            .select("key,value,editable_by,description")
            .eq("key", key)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    if not current_result.data:
        raise HTTPException(404, f"Config key '{key}' not found.")

    config = current_result.data[0]

    # ── Guard: editable_by enforcement ──
    if config.get("editable_by") == "org_admin" and user.role != "org_admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Config key '{key}' can only be edited by org_admin.",
        )

    # Update
    now = datetime.now(timezone.utc).isoformat()
    try:
        update_result = (
            client.table("system_config")
            .update({
                "value": body.value,
                "updated_by": user.id,
                "updated_at": now,
            })
            .eq("key", key)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to update config: {str(e)[:200]}")

    # Audit log
    fire_and_forget_audit(
        user_id=user.id,
        action="config_updated",
        domain="admin",
        query_text=key,
        governance_result={
            "key": key,
            "before": config.get("value"),
            "after": body.value,
        },
    )

    updated = update_result.data[0] if update_result.data else None

    return ConfigItem(
        key=key,
        value=body.value if updated is None else updated.get("value", body.value),
        description=config.get("description"),
        editable_by=config.get("editable_by", "admin_manager"),
        updated_by=user.id,
        updated_at=now,
    )
