"""
Bower Ag CowCare Tool — Authentication & Authorization Middleware
Sprint 3: JWT validation via Supabase Auth, role guards, profile auto-creation.

Governance-first: Auth middleware runs on every protected endpoint.
Roles enforce what each user can see and do.
"""

from typing import Optional
from pydantic import BaseModel
from fastapi import Depends, HTTPException, Header, status
from functools import wraps

from app.db.supabase_client import get_supabase_client


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────

class CurrentUser(BaseModel):
    """Authenticated user context, attached to every protected request."""
    id: str
    email: str
    role: str
    location_id: Optional[str] = None
    full_name: Optional[str] = None


# All valid roles from the profiles.role CHECK constraint
VALID_ROLES = [
    "org_admin",
    "admin_manager",
    "consultant",
    "technician",
    "account_manager",
    "customer",
]


# ─────────────────────────────────────────────────────────────────────────────
# Dependencies
# ─────────────────────────────────────────────────────────────────────────────

async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> CurrentUser:
    """
    FastAPI dependency: extract and validate Bearer token, return CurrentUser.

    Steps:
      1. Extract Bearer token from Authorization header — 401 if missing
      2. supabase.auth.get_user(token) — 401 if invalid/expired
      3. Query profiles table for role + location_id
      4. If no profile: auto-create with role='consultant'
      5. Return CurrentUser with all fields populated
    """
    # Step 1: Extract Bearer token
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Send: Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # Step 2: Validate token with Supabase Auth
    client = get_supabase_client()
    try:
        user_response = client.auth.get_user(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)[:100]}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_response or not user_response.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed — no user found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supabase_user = user_response.user
    user_id = supabase_user.id
    user_email = supabase_user.email or ""

    # Step 3: Query profiles table for role + location
    try:
        profile_result = (
            client.table("profiles")
            .select("role,location_id,full_name")
            .eq("id", user_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query user profile: {str(e)[:100]}",
        )

    # Step 4: Auto-create profile if missing
    if not profile_result.data:
        try:
            new_profile = {
                "id": user_id,
                "role": "consultant",
                "full_name": supabase_user.user_metadata.get("full_name", user_email.split("@")[0]),
            }
            client.table("profiles").insert(new_profile).execute()
            return CurrentUser(
                id=user_id,
                email=user_email,
                role="consultant",
                location_id=None,
                full_name=new_profile["full_name"],
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to auto-create user profile: {str(e)[:100]}",
            )

    # Step 5: Return CurrentUser from existing profile
    profile = profile_result.data[0]
    return CurrentUser(
        id=user_id,
        email=user_email,
        role=profile.get("role", "consultant"),
        location_id=profile.get("location_id"),
        full_name=profile.get("full_name"),
    )


def require_role(allowed_roles: list[str]):
    """
    FastAPI dependency factory: raises 403 if user's role is not in allowed_roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role(["org_admin"]))])
        async def admin_endpoint(user: CurrentUser = Depends(get_current_user)):
            ...

    Or inline:
        async def endpoint(user: CurrentUser = Depends(require_role(["consultant", "org_admin"]))):
            ...
    """
    async def role_checker(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Your role '{user.role}' does not have permission. "
                    f"Required: {', '.join(allowed_roles)}"
                ),
            )
        return user

    return role_checker


# ─────────────────────────────────────────────────────────────────────────────
# Convenience role sets (used by endpoints)
# ─────────────────────────────────────────────────────────────────────────────

# All roles except customer — for product lookup endpoints
NON_CUSTOMER_ROLES = [r for r in VALID_ROLES if r != "customer"]

# Admin roles — for governance health and admin endpoints
ADMIN_ROLES = ["org_admin", "admin_manager"]
