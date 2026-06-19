"""
Bower Ag CowCare Tool — Session & Feedback API
Sprint 7: Location selection, message feedback, bug reports.

Endpoints:
  POST /session/location       — Set/change session location lock
  DELETE /session/location      — Clear session location lock
  POST /feedback               — Thumbs up/down on assistant messages
  POST /bugs                   — Submit bug report with auto-context
"""

import asyncio
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, NON_CUSTOMER_ROLES, VALID_ROLES, require_role
from app.core.location_lock import location_lock_store
from app.db.supabase_client import get_supabase_client
from app.services.audit_service import log_governance_action

router = APIRouter(tags=["Session & Feedback"])

# ─── Location models ──────────────────────────────────────────────────────────

VALID_LOCATIONS = {
    "EVANS": "Evans CO",
    "ULYSSES": "Ulysses KS",
    "JEROME": "Jerome ID",
    "TURLOCK": "Turlock CA",
    "TULARE": "Tulare CA",
}


class SetLocationRequest(BaseModel):
    location_code: str = Field(..., description="Branch code: EVANS, ULYSSES, JEROME, TURLOCK, TULARE")
    force: bool = Field(False, description="Force override if already locked to different location")


class LocationResponse(BaseModel):
    location_code: str
    location_name: str
    previously_locked: Optional[str] = None
    message: str


# ─── Feedback models ──────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    conversation_id: Optional[str] = None
    message_index: Optional[int] = None
    rating: int = Field(..., ge=-1, le=1, description="-1=thumbs down, 1=thumbs up")
    comment: Optional[str] = Field(None, max_length=1000)
    session_id: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    message: str


# ─── Bug report models ───────────────────────────────────────────────────────

class BugReportRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    what_happened: str = Field(..., min_length=10, max_length=2000)
    expected_behavior: Optional[str] = Field(None, max_length=2000)
    severity: str = Field("medium", pattern="^(critical|high|medium|low)$")
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None


class BugReportResponse(BaseModel):
    id: str
    message: str


# ─── POST /session/location ──────────────────────────────────────────────────

@router.post("/session/location", response_model=LocationResponse)
async def set_session_location(
    body: SetLocationRequest,
    user: CurrentUser = Depends(require_role(NON_CUSTOMER_ROLES)),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    Set or change the location lock for this session.
    If already locked to a different location and force=False, returns 409.
    If force=True, overrides the lock (used after user confirms location change).
    """
    session_id = x_session_id or "default"
    code = body.location_code.upper()

    if code not in VALID_LOCATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid location code '{code}'. Valid: {', '.join(VALID_LOCATIONS.keys())}",
        )

    existing = location_lock_store.get_location(session_id)

    if existing and existing != code and not body.force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session already locked to {existing} ({VALID_LOCATIONS.get(existing, existing)}). "
                   f"Set force=true to switch.",
        )

    # Set (or override) the lock
    location_lock_store.set_location(session_id, code, user.id)

    # Audit
    asyncio.create_task(log_governance_action(
        user_id=user.id,
        action="session.location_set",
        domain="session",
        location_locked=code,
        governance_result={
            "previous": existing,
            "new": code,
            "forced": body.force and existing is not None and existing != code,
        },
        response_summary=f"Location set to {code}",
    ))

    return LocationResponse(
        location_code=code,
        location_name=VALID_LOCATIONS[code],
        previously_locked=existing if existing and existing != code else None,
        message=f"Location set to {VALID_LOCATIONS[code]}. All pricing will use {code} rates.",
    )


# ─── DELETE /session/location ────────────────────────────────────────────────

@router.delete("/session/location")
async def clear_session_location(
    user: CurrentUser = Depends(require_role(NON_CUSTOMER_ROLES)),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """Clear the location lock for this session (used by 'New Conversation')."""
    session_id = x_session_id or "default"
    existed = location_lock_store.clear_location(session_id)

    asyncio.create_task(log_governance_action(
        user_id=user.id,
        action="session.location_cleared",
        domain="session",
        response_summary=f"Location lock cleared (existed={existed})",
    ))

    return {"cleared": existed, "message": "Location lock cleared."}


# ─── POST /feedback ──────────────────────────────────────────────────────────

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    body: FeedbackRequest,
    user: CurrentUser = Depends(require_role(NON_CUSTOMER_ROLES)),
):
    """
    Submit thumbs up/down feedback on an assistant message.
    Stores in feedback table with user context.
    """
    client = get_supabase_client()

    row = {
        "user_id": user.id,
        "rating": body.rating,
        "user_role": user.role,
        "app_version": os.getenv("APP_VERSION", "0.0.1"),
    }
    if body.conversation_id:
        row["conversation_id"] = body.conversation_id
    if body.message_index is not None:
        row["message_index"] = body.message_index
    if body.comment:
        row["comment"] = body.comment
    if body.session_id:
        row["session_id"] = body.session_id

    try:
        result = client.table("feedback").insert(row).execute()
        feedback_id = result.data[0]["id"] if result.data else "unknown"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save feedback: {str(e)[:200]}",
        )

    return FeedbackResponse(
        id=str(feedback_id),
        message="Thanks for the feedback!" if body.rating > 0 else "Got it — we'll use this to improve.",
    )


# ─── POST /bugs ──────────────────────────────────────────────────────────────

@router.post("/bugs", response_model=BugReportResponse)
async def submit_bug_report(
    body: BugReportRequest,
    user: CurrentUser = Depends(require_role(VALID_ROLES)),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    Submit a bug report with auto-attached context.
    Context: user role, location, app version, conversation_id.
    """
    session_id = x_session_id or "default"
    location = location_lock_store.get_location(session_id)
    client = get_supabase_client()

    row = {
        "user_id": user.id,
        "title": body.title,
        "what_happened": body.what_happened,
        "severity": body.severity,
        "status": "open",
        "user_role": user.role,
        "location_code": location,
        "app_version": os.getenv("APP_VERSION", "0.0.1"),
    }
    if body.expected_behavior:
        row["expected_behavior"] = body.expected_behavior
    if body.conversation_id:
        row["conversation_id"] = body.conversation_id
    if body.session_id:
        row["session_id"] = body.session_id

    try:
        result = client.table("bug_reports").insert(row).execute()
        bug_id = result.data[0]["id"] if result.data else "unknown"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save bug report: {str(e)[:200]}",
        )

    # Audit
    asyncio.create_task(log_governance_action(
        user_id=user.id,
        action="bug_report.submitted",
        domain="system",
        governance_result={
            "bug_id": str(bug_id),
            "severity": body.severity,
            "title": body.title[:100],
        },
        response_summary=f"Bug report '{body.title[:50]}' submitted",
    ))

    return BugReportResponse(
        id=str(bug_id),
        message="Got it — we'll look into this. Thanks for helping make CowCare better.",
    )
