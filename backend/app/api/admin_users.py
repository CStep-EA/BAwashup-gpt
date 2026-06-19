"""
Bower Ag CowCare Tool — Admin User Management API
Sprint 11: User invite, list, update, deactivate for admin portal.

Role guards:
  - No one can create or change TO org_admin role
  - No one can change FROM org_admin role (immutable)
  - admin_manager cannot assign or change admin_manager role
  - Cannot deactivate yourself

All mutations are logged to audit_log with before/after values.
Auth: admin_manager, org_admin.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, require_role, ADMIN_ROLES, VALID_ROLES
from app.db.supabase_client import get_supabase_client
from app.services.audit_service import fire_and_forget_audit

router = APIRouter(prefix="/admin/users", tags=["Admin Users"])


# ─── Request / Response Models ────────────────────────────────────────────────

class UserListItem(BaseModel):
    id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str
    location_name: Optional[str] = None
    active: bool
    created_at: str


class InviteRequest(BaseModel):
    email: str = Field(..., min_length=3, description="Email address to invite")
    role: str = Field(..., description="Role to assign. Cannot be 'org_admin'.")
    location_id: Optional[str] = None
    full_name: str = Field(..., min_length=1)


class InviteResponse(BaseModel):
    user_id: str
    email: str
    role: str
    message: str


class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    location_id: Optional[str] = None
    full_name: Optional[str] = None
    active: Optional[bool] = None


class UpdateUserResponse(BaseModel):
    id: str
    full_name: Optional[str] = None
    role: str
    location_id: Optional[str] = None
    active: bool


class DeactivateResponse(BaseModel):
    message: str


# ─── GET /admin/users ─────────────────────────────────────────────────────────

@router.get("", response_model=list[UserListItem])
async def list_users(
    role: Optional[str] = Query(None),
    location_code: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    List all users with optional filters.

    Email comes from Supabase auth admin API; profile data from profiles table.
    """
    client = get_supabase_client()

    try:
        # Build query on profiles, join location name
        query = client.table("profiles").select(
            "id,full_name,role,location_id,active,created_at,locations(name)"
        )

        if role:
            query = query.eq("role", role)
        if active is not None:
            query = query.eq("active", active)

        result = query.order("created_at", desc=True).execute()
        profiles = result.data or []

    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    # Filter by location_code if provided
    if location_code:
        try:
            loc_result = (
                client.table("locations")
                .select("id")
                .eq("branch_code", location_code.upper())
                .execute()
            )
            if loc_result.data:
                loc_id = loc_result.data[0]["id"]
                profiles = [p for p in profiles if p.get("location_id") == loc_id]
            else:
                profiles = []
        except Exception:
            pass

    # Fetch emails from Supabase admin auth API
    email_map: dict[str, str] = {}
    try:
        auth_users = client.auth.admin.list_users()
        # auth_users may be a list or have .users attribute
        user_list = auth_users if isinstance(auth_users, list) else getattr(auth_users, "users", auth_users)
        if isinstance(user_list, list):
            for au in user_list:
                uid = getattr(au, "id", None) or (au.get("id") if isinstance(au, dict) else None)
                email = getattr(au, "email", None) or (au.get("email") if isinstance(au, dict) else None)
                if uid and email:
                    email_map[uid] = email
    except Exception:
        # If admin API fails, emails will be None
        pass

    # Apply search filter (name or email)
    if search:
        search_lower = search.lower()
        profiles = [
            p for p in profiles
            if (search_lower in (p.get("full_name") or "").lower()
                or search_lower in email_map.get(p["id"], "").lower())
        ]

    # Build response
    items = []
    for p in profiles:
        loc_data = p.get("locations")
        loc_name = None
        if isinstance(loc_data, dict):
            loc_name = loc_data.get("name")
        elif isinstance(loc_data, list) and loc_data:
            loc_name = loc_data[0].get("name")

        items.append(UserListItem(
            id=p["id"],
            full_name=p.get("full_name"),
            email=email_map.get(p["id"]),
            role=p["role"],
            location_name=loc_name,
            active=p.get("active", True),
            created_at=str(p.get("created_at", "")),
        ))

    return items


# ─── POST /admin/users/invite ─────────────────────────────────────────────────

@router.post("/invite", response_model=InviteResponse)
async def invite_user(
    body: InviteRequest,
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Invite a new user via Supabase email invite.

    Guards:
      - role cannot be 'org_admin' (for ANY caller)
      - admin_manager cannot assign 'admin_manager' role
      - email must not already exist in auth.users
    """
    client = get_supabase_client()

    # ── Guard: cannot create org_admin ──
    if body.role == "org_admin":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot invite users with org_admin role. This role is managed at the system level.",
        )

    # ── Guard: admin_manager cannot assign admin_manager ──
    if user.role == "admin_manager" and body.role == "admin_manager":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Admin managers cannot invite other admin managers. Only org_admin can.",
        )

    # ── Guard: validate role ──
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid role '{body.role}'. Valid roles: {', '.join(VALID_ROLES)}",
        )

    # ── Guard: email must not already exist ──
    try:
        auth_users = client.auth.admin.list_users()
        user_list = auth_users if isinstance(auth_users, list) else getattr(auth_users, "users", auth_users)
        existing_emails = set()
        if isinstance(user_list, list):
            for au in user_list:
                email = getattr(au, "email", None) or (au.get("email") if isinstance(au, dict) else None)
                if email:
                    existing_emails.add(email.lower())

        if body.email.lower() in existing_emails:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"A user with email '{body.email}' already exists.",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to check existing users: {str(e)[:200]}")

    # ── Invite user via Supabase auth ──
    try:
        invite_result = client.auth.admin.invite_user_by_email(body.email)
        new_user = invite_result.user
        new_user_id = new_user.id
    except Exception as e:
        raise HTTPException(500, f"Failed to send invitation: {str(e)[:200]}")

    # ── Pre-create profile row ──
    try:
        profile_row = {
            "id": new_user_id,
            "role": body.role,
            "full_name": body.full_name,
            "active": True,
        }
        if body.location_id:
            profile_row["location_id"] = body.location_id
        client.table("profiles").insert(profile_row).execute()
    except Exception as e:
        # Profile creation failed — log but don't fail the invite
        print(f"[ADMIN] Failed to pre-create profile for {body.email}: {e}")

    # ── Audit log ──
    fire_and_forget_audit(
        user_id=user.id,
        action="user_invited",
        domain="admin",
        query_text=body.email,
        governance_result={
            "invited_user_id": new_user_id,
            "role": body.role,
            "full_name": body.full_name,
        },
    )

    return InviteResponse(
        user_id=new_user_id,
        email=body.email,
        role=body.role,
        message=f"Invitation sent to {body.email}",
    )


# ─── PATCH /admin/users/{user_id} ─────────────────────────────────────────────

@router.patch("/{user_id}", response_model=UpdateUserResponse)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Update a user's profile (role, location, name, active status).

    Guards:
      - Cannot change any user TO org_admin role
      - Cannot change FROM org_admin role (org_admin users are immutable)
      - Cannot deactivate yourself
      - admin_manager cannot change another admin_manager's role
    """
    client = get_supabase_client()

    # Fetch current profile
    try:
        current_result = (
            client.table("profiles")
            .select("id,full_name,role,location_id,active")
            .eq("id", user_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    if not current_result.data:
        raise HTTPException(404, "User not found.")

    current_profile = current_result.data[0]

    # ── Guard: cannot modify org_admin users ──
    if current_profile["role"] == "org_admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Org admin users are immutable and cannot be modified.",
        )

    # ── Guard: cannot change TO org_admin ──
    if body.role == "org_admin":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot change a user's role to org_admin.",
        )

    # ── Guard: cannot deactivate yourself ──
    if body.active is False and user_id == user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "You cannot deactivate your own account.",
        )

    # ── Guard: admin_manager cannot change another admin_manager's role ──
    if (
        user.role == "admin_manager"
        and current_profile["role"] == "admin_manager"
        and body.role is not None
        and body.role != current_profile["role"]
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Admin managers cannot change another admin manager's role.",
        )

    # ── Guard: validate role ──
    if body.role and body.role not in VALID_ROLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid role '{body.role}'. Valid roles: {', '.join(VALID_ROLES)}",
        )

    # Build update patch (only non-None fields)
    patch: dict = {}
    if body.role is not None:
        patch["role"] = body.role
    if body.location_id is not None:
        patch["location_id"] = body.location_id
    if body.full_name is not None:
        patch["full_name"] = body.full_name
    if body.active is not None:
        patch["active"] = body.active

    if not patch:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No fields to update.",
        )

    # Apply update
    try:
        update_result = (
            client.table("profiles")
            .update(patch)
            .eq("id", user_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to update user: {str(e)[:200]}")

    updated = update_result.data[0] if update_result.data else {**current_profile, **patch}

    # ── Audit log with before/after ──
    fire_and_forget_audit(
        user_id=user.id,
        action="user_updated",
        domain="admin",
        query_text=user_id,
        governance_result={
            "target_user_id": user_id,
            "before": {
                "role": current_profile["role"],
                "location_id": current_profile.get("location_id"),
                "full_name": current_profile.get("full_name"),
                "active": current_profile.get("active", True),
            },
            "after": {
                "role": updated.get("role", current_profile["role"]),
                "location_id": updated.get("location_id", current_profile.get("location_id")),
                "full_name": updated.get("full_name", current_profile.get("full_name")),
                "active": updated.get("active", current_profile.get("active", True)),
            },
        },
    )

    return UpdateUserResponse(
        id=user_id,
        full_name=updated.get("full_name"),
        role=updated.get("role", current_profile["role"]),
        location_id=updated.get("location_id"),
        active=updated.get("active", True),
    )


# ─── DELETE /admin/users/{user_id} ────────────────────────────────────────────

@router.delete("/{user_id}", response_model=DeactivateResponse)
async def deactivate_user(
    user_id: str,
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Soft-deactivate a user: sets active=false in profiles AND bans in Supabase auth.

    Never hard-deletes. Same guards as PATCH.
    """
    client = get_supabase_client()

    # Fetch current profile
    try:
        current_result = (
            client.table("profiles")
            .select("id,full_name,role,active")
            .eq("id", user_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    if not current_result.data:
        raise HTTPException(404, "User not found.")

    current_profile = current_result.data[0]

    # ── Guard: cannot deactivate org_admin ──
    if current_profile["role"] == "org_admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Org admin users cannot be deactivated.",
        )

    # ── Guard: cannot deactivate yourself ──
    if user_id == user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "You cannot deactivate your own account.",
        )

    # Deactivate in profiles
    try:
        client.table("profiles").update({"active": False}).eq("id", user_id).execute()
    except Exception as e:
        raise HTTPException(500, f"Failed to deactivate user: {str(e)[:200]}")

    # Ban in Supabase auth
    try:
        client.auth.admin.update_user_by_id(user_id, {"ban_duration": "876000h"})
    except Exception as e:
        print(f"[ADMIN] Failed to ban user {user_id} in auth: {e}")

    # Audit log
    fire_and_forget_audit(
        user_id=user.id,
        action="user_deactivated",
        domain="admin",
        query_text=user_id,
        governance_result={
            "target_user_id": user_id,
            "full_name": current_profile.get("full_name"),
            "role": current_profile["role"],
            "before": {"active": current_profile.get("active", True)},
            "after": {"active": False},
        },
    )

    name = current_profile.get("full_name") or "User"
    return DeactivateResponse(message=f"{name} has been deactivated.")
