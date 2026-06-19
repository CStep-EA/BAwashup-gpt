"""
Bower Ag CowCare Tool — Audit Service
Sprint 3: Non-blocking audit logging for governance compliance.

Every governance action is logged to the audit_log table.
Uses asyncio.create_task() so the response is never delayed by audit writes.
"""

import asyncio
import os
import traceback
from datetime import datetime
from typing import Optional

from app.db.supabase_client import get_supabase_client


async def log_governance_action(
    user_id: Optional[str],
    action: str,
    domain: Optional[str] = None,
    query_text: Optional[str] = None,
    location_locked: Optional[str] = None,
    governance_result: Optional[dict] = None,
    llm_called: bool = False,
    response_summary: Optional[str] = None,
    duration_ms: Optional[int] = None,
) -> None:
    """
    Asynchronously insert an audit_log row.

    This function is designed to be called with asyncio.create_task()
    so it never blocks the HTTP response. Failures are logged but
    never propagated to the caller.

    Args:
        user_id: UUID of the authenticated user (None for system events)
        action: What happened (e.g., 'product.exists', 'pricing.lookup')
        domain: Business domain (e.g., 'governance', 'chat', 'report')
        query_text: The original query or search term
        location_locked: Location code the session was locked to
        governance_result: JSON dict with governance check details
        llm_called: Whether Claude API was invoked (MUST be False for governance)
        response_summary: Brief summary of what was returned
        duration_ms: How long the request took in milliseconds
    """
    try:
        client = get_supabase_client()

        row = {
            "action": action,
            "domain": domain or "governance",
            "llm_called": llm_called,
            "app_version": os.getenv("APP_VERSION", "0.0.1"),
        }

        # Only include non-None fields to avoid sending null for FK columns
        if user_id:
            row["user_id"] = user_id
        if query_text:
            row["query_text"] = query_text
        if location_locked:
            row["location_locked"] = location_locked
        if governance_result is not None:
            row["governance_result"] = governance_result
        if response_summary:
            row["response_summary"] = response_summary
        if duration_ms is not None:
            row["duration_ms"] = duration_ms

        # Run the DB insert in a thread to avoid blocking the event loop
        # (supabase-py is synchronous)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.table("audit_log").insert(row).execute()
        )

    except Exception:
        # Never let audit failures crash the app.
        # In production, this would go to Sentry.
        print(f"[AUDIT] Failed to log action '{action}': {traceback.format_exc()}")


def fire_and_forget_audit(
    user_id: Optional[str],
    action: str,
    **kwargs,
) -> None:
    """
    Fire-and-forget wrapper for log_governance_action.
    Creates an async task that runs in the background.

    Usage in endpoint:
        fire_and_forget_audit(
            user_id=user.id,
            action="product.exists",
            query_text=name,
            governance_result={"exists": True, "count": 3},
        )
    """
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(
            log_governance_action(user_id=user_id, action=action, **kwargs)
        )
    except RuntimeError:
        # No event loop running — fallback to sync (shouldn't happen in FastAPI)
        print(f"[AUDIT] No event loop — skipping audit for '{action}'")
