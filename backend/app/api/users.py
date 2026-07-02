"""
Bower Ag CowCare Tool — User Search API
Sprint 21: User lookup for report sharing.

Provides a /users endpoint to search for users by role and name/email.
Available to NON_CUSTOMER_ROLES (consultants, technicians, etc.) for
sharing reports with both internal team members and customer accounts.

This is separate from /admin/users which requires admin roles.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import CurrentUser, NON_CUSTOMER_ROLES, require_role
from app.db.supabase_client import get_supabase_client

router = APIRouter(tags=["Users"])


# ─── Response Models ──────────────────────────────────────────────────────────

class UserSearchResult(BaseModel):
    id: str
    email: str | None = None
    full_name: str | None = None
    role: str
    customer_operation: str | None = None


# ─── GET /users ──────────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserSearchResult])
async def search_users(
    search: str = Query(..., min_length=2, description="Search term (name or email)"),
    role: Optional[str] = Query(None, description="Filter by role (e.g. 'customer')"),
    user: CurrentUser = Depends(require_role(NON_CUSTOMER_ROLES)),
):
    """
    Search for users by name or email.
    
    Used by report sharing to find recipients (internal or customer).
    Auth: Any non-customer role.
    
    If role filter is provided, results are limited to that role.
    Otherwise returns all matching users.
    """
    client = get_supabase_client()

    try:
        # Query profiles table
        query = client.table("profiles").select(
            "id,full_name,role,active"
        ).eq("active", True)

        if role:
            query = query.eq("role", role)

        result = query.execute()
        profiles = result.data or []

    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    # Fetch emails from auth admin API
    email_map: dict[str, str] = {}
    try:
        auth_users = client.auth.admin.list_users()
        user_list = auth_users if isinstance(auth_users, list) else getattr(auth_users, "users", auth_users)
        if isinstance(user_list, list):
            for au in user_list:
                uid = getattr(au, "id", None) or (au.get("id") if isinstance(au, dict) else None)
                email = getattr(au, "email", None) or (au.get("email") if isinstance(au, dict) else None)
                if uid and email:
                    email_map[str(uid)] = email
    except Exception:
        pass

    # Filter by search term (case-insensitive match on name or email)
    search_lower = search.lower()
    results: list[UserSearchResult] = []

    for profile in profiles:
        pid = str(profile["id"])
        name = profile.get("full_name") or ""
        email = email_map.get(pid, "")
        role_val = profile.get("role", "")

        # Match against name or email
        if search_lower in name.lower() or search_lower in email.lower():
            results.append(UserSearchResult(
                id=pid,
                email=email or None,
                full_name=name or None,
                role=role_val,
                customer_operation=None,  # Could be enriched later
            ))

        if len(results) >= 20:
            break

    return results
