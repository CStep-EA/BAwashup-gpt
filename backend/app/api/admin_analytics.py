"""
Bower Ag CowCare Tool — Admin Analytics API
Sprint 11: Dashboard analytics for admin portal.

Queries audit_log, bug_reports, and products tables to provide
summary metrics, top product mentions, and daily usage charts.

Auth: admin_manager, org_admin only.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import CurrentUser, require_role, ADMIN_ROLES
from app.db.supabase_client import get_supabase_client

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])


# ─── Response Models ──────────────────────────────────────────────────────────

class DomainCount(BaseModel):
    domain: str
    count: int


class LocationCount(BaseModel):
    location_locked: str
    count: int


class AnalyticsSummary(BaseModel):
    total_queries: int
    queries_today: int
    active_users: int
    queries_by_domain: list[DomainCount]
    queries_by_location: list[LocationCount]
    avg_response_ms: float
    governance_blocks: int
    claude_api_calls: int
    thumbs_up: int
    thumbs_down: int
    open_bugs: int
    open_critical_bugs: int


class TopProduct(BaseModel):
    product_name: str
    mention_count: int


class DailyUsage(BaseModel):
    date: str
    query_count: int
    active_users: int


# ─── GET /admin/analytics/summary ─────────────────────────────────────────────

@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    days: int = Query(default=7, ge=1, le=90),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Dashboard summary metrics.

    Aggregates audit_log and bug_reports within the given time window.
    """
    client = get_supabase_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()

    try:
        # Fetch audit rows in the time window
        audit_result = (
            client.table("audit_log")
            .select("user_id,domain,location_locked,governance_result,llm_called,duration_ms,feedback_rating,created_at")
            .gte("created_at", cutoff)
            .execute()
        )
        audit_rows = audit_result.data or []

        # Bug reports — open + open critical
        bugs_result = (
            client.table("bug_reports")
            .select("id,severity,status")
            .execute()
        )
        bug_rows = bugs_result.data or []

    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    # Compute metrics from fetched rows
    total_queries = len(audit_rows)

    # Queries today
    queries_today = sum(
        1 for r in audit_rows
        if str(r.get("created_at", "")) >= today_start
    )

    # Active users (distinct user_ids)
    user_ids = {r["user_id"] for r in audit_rows if r.get("user_id")}
    active_users = len(user_ids)

    # Queries by domain
    domain_counts: dict[str, int] = {}
    for r in audit_rows:
        d = r.get("domain") or "unknown"
        domain_counts[d] = domain_counts.get(d, 0) + 1
    queries_by_domain = [
        DomainCount(domain=d, count=c)
        for d, c in sorted(domain_counts.items(), key=lambda x: -x[1])
    ]

    # Queries by location
    loc_counts: dict[str, int] = {}
    for r in audit_rows:
        loc = r.get("location_locked") or "none"
        loc_counts[loc] = loc_counts.get(loc, 0) + 1
    queries_by_location = [
        LocationCount(location_locked=loc, count=c)
        for loc, c in sorted(loc_counts.items(), key=lambda x: -x[1])
    ]

    # Avg response time
    durations = [r["duration_ms"] for r in audit_rows if r.get("duration_ms") is not None]
    avg_response_ms = round(sum(durations) / len(durations), 1) if durations else 0.0

    # Governance blocks — where governance_result contains sellable:false
    governance_blocks = 0
    for r in audit_rows:
        gr = r.get("governance_result")
        if isinstance(gr, dict):
            # Check top-level or nested sellable:false
            if gr.get("sellable") is False:
                governance_blocks += 1
            elif isinstance(gr.get("results"), list):
                for item in gr["results"]:
                    if isinstance(item, dict) and item.get("sellable") is False:
                        governance_blocks += 1
                        break

    # Claude API calls
    claude_api_calls = sum(1 for r in audit_rows if r.get("llm_called"))

    # Feedback
    thumbs_up = sum(1 for r in audit_rows if r.get("feedback_rating") == 1)
    thumbs_down = sum(1 for r in audit_rows if r.get("feedback_rating") == -1)

    # Bug counts
    open_statuses = {"open", "investigating", "in_progress"}
    open_bugs = sum(1 for b in bug_rows if b.get("status") in open_statuses)
    open_critical_bugs = sum(
        1 for b in bug_rows
        if b.get("status") in open_statuses and b.get("severity") == "critical"
    )

    return AnalyticsSummary(
        total_queries=total_queries,
        queries_today=queries_today,
        active_users=active_users,
        queries_by_domain=queries_by_domain,
        queries_by_location=queries_by_location,
        avg_response_ms=avg_response_ms,
        governance_blocks=governance_blocks,
        claude_api_calls=claude_api_calls,
        thumbs_up=thumbs_up,
        thumbs_down=thumbs_down,
        open_bugs=open_bugs,
        open_critical_bugs=open_critical_bugs,
    )


# ─── GET /admin/analytics/top_products ────────────────────────────────────────

@router.get("/top_products", response_model=list[TopProduct])
async def top_products(
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=10, ge=1, le=50),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Most-mentioned products in audit_log query_text.

    Parses audit_log.query_text and matches against the products table
    using simple ILIKE matching.
    """
    client = get_supabase_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    try:
        # Get all active product names
        products_result = (
            client.table("products")
            .select("product_name")
            .eq("active", True)
            .execute()
        )
        product_names = [p["product_name"] for p in (products_result.data or [])]

        # Get audit_log query_text in the time window
        audit_result = (
            client.table("audit_log")
            .select("query_text")
            .gte("created_at", cutoff)
            .execute()
        )
        query_texts = [
            (r.get("query_text") or "").lower()
            for r in (audit_result.data or [])
            if r.get("query_text")
        ]

    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    # Count mentions
    mention_counts: dict[str, int] = {}
    for pname in product_names:
        pname_lower = pname.lower()
        count = sum(1 for qt in query_texts if pname_lower in qt)
        if count > 0:
            mention_counts[pname] = count

    # Sort and limit
    sorted_products = sorted(mention_counts.items(), key=lambda x: -x[1])[:limit]
    return [
        TopProduct(product_name=name, mention_count=count)
        for name, count in sorted_products
    ]


# ─── GET /admin/analytics/usage_by_day ────────────────────────────────────────

@router.get("/usage_by_day", response_model=list[DailyUsage])
async def usage_by_day(
    days: int = Query(default=30, ge=1, le=90),
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Daily query counts and active users for line chart.

    Returns one entry per day in the window, sorted chronologically.
    """
    client = get_supabase_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    try:
        audit_result = (
            client.table("audit_log")
            .select("user_id,created_at")
            .gte("created_at", cutoff)
            .execute()
        )
        rows = audit_result.data or []

    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    # Group by date
    daily_data: dict[str, dict] = {}
    for r in rows:
        created = r.get("created_at", "")
        # Parse ISO date
        day_str = str(created)[:10]  # YYYY-MM-DD
        if day_str not in daily_data:
            daily_data[day_str] = {"count": 0, "users": set()}
        daily_data[day_str]["count"] += 1
        if r.get("user_id"):
            daily_data[day_str]["users"].add(r["user_id"])

    # Fill missing days and sort
    result = []
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).date()
    end_date = datetime.now(timezone.utc).date()
    current = start_date
    while current <= end_date:
        day_str = current.isoformat()
        data = daily_data.get(day_str, {"count": 0, "users": set()})
        result.append(DailyUsage(
            date=day_str,
            query_count=data["count"],
            active_users=len(data["users"]),
        ))
        current += timedelta(days=1)

    return result
