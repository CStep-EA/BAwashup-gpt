"""
Bower Ag CowCare Tool — Governance API Endpoints
Sprint 3: Product lookup, sellability check, pricing lookup, governance health.

⚠️  CRITICAL: These endpoints NEVER call Claude API. Zero LLM involvement.
    All data comes from Supabase DB via service_role client.
    The llm_called field in audit_log is ALWAYS False for governance.
"""

import os
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status

from app.core.auth import (
    CurrentUser,
    get_current_user,
    require_role,
    NON_CUSTOMER_ROLES,
    ADMIN_ROLES,
)
from app.core.location_lock import location_lock_store
from app.db.supabase_client import get_supabase_client
from app.services.audit_service import fire_and_forget_audit

router = APIRouter(tags=["Governance"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /product/exists
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/product/exists")
async def product_exists(
    name: str = Query(..., min_length=1, description="Product name or part number to search"),
    user: CurrentUser = Depends(require_role(NON_CUSTOMER_ROLES)),
):
    """
    Search for a product by name (fuzzy) or part number (exact).
    Auth: any role except customer.
    Returns: {exists, products, count}

    ⚠️  NO LLM — pure DB query.
    """
    start = time.time()
    client = get_supabase_client()

    # Search: product_name ILIKE '%{name}%' OR part_number = name
    try:
        # ILIKE search on product_name
        name_result = (
            client.table("products")
            .select("id,product_name,part_number,category,product_type,active")
            .ilike("product_name", f"%{name}%")
            .eq("active", True)
            .limit(25)
            .execute()
        )

        # Exact match on part_number
        pn_result = (
            client.table("products")
            .select("id,product_name,part_number,category,product_type,active")
            .eq("part_number", name)
            .eq("active", True)
            .limit(10)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)[:200]}",
        )

    # Merge and deduplicate by id
    seen_ids = set()
    products = []
    for row in (name_result.data or []) + (pn_result.data or []):
        if row["id"] not in seen_ids:
            seen_ids.add(row["id"])
            products.append(row)

    duration_ms = int((time.time() - start) * 1000)

    result = {
        "exists": len(products) > 0,
        "products": products,
        "count": len(products),
        "source": "governance_db",
    }

    # Audit (fire-and-forget)
    fire_and_forget_audit(
        user_id=user.id,
        action="product.exists",
        query_text=name,
        governance_result={"exists": result["exists"], "count": result["count"]},
        response_summary=f"Found {result['count']} product(s) matching '{name}'",
        duration_ms=duration_ms,
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# GET /product/sellable
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/product/sellable")
async def product_sellable(
    product_id: str = Query(..., description="Product UUID"),
    location_code: str = Query(..., description="Branch code (e.g., EVANS, TURLOCK)"),
    user: CurrentUser = Depends(require_role(NON_CUSTOMER_ROLES)),
):
    """
    Check if a product is sellable at a specific location.
    Auth: any role except customer.
    Returns: {sellable, product_id, location, location_code, reason?}

    ⚠️  NO LLM — pure DB query.
    """
    start = time.time()
    client = get_supabase_client()

    # Lookup location by branch_code
    try:
        loc_result = (
            client.table("locations")
            .select("id,name,branch_code")
            .eq("branch_code", location_code.upper())
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)[:200]}",
        )

    if not loc_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location '{location_code}' not found. Valid codes: EVANS, ULYSSES, JEROME, TURLOCK, TULARE",
        )

    location = loc_result.data[0]
    location_id = location["id"]

    # Query product_sellability
    try:
        sell_result = (
            client.table("product_sellability")
            .select("sellable")
            .eq("product_id", product_id)
            .eq("location_id", location_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)[:200]}",
        )

    duration_ms = int((time.time() - start) * 1000)

    if not sell_result.data:
        result = {
            "sellable": False,
            "product_id": product_id,
            "location": location["name"],
            "location_code": location["branch_code"],
            "reason": "Not in sellability matrix",
            "source": "governance_db",
        }
    else:
        is_sellable = sell_result.data[0].get("sellable", False)
        result = {
            "sellable": is_sellable,
            "product_id": product_id,
            "location": location["name"],
            "location_code": location["branch_code"],
            "source": "governance_db",
        }
        if not is_sellable:
            result["reason"] = "Product is marked as not sellable at this location"

    # Audit
    fire_and_forget_audit(
        user_id=user.id,
        action="product.sellable",
        query_text=f"product_id={product_id}, location={location_code}",
        location_locked=location_code,
        governance_result={
            "sellable": result["sellable"],
            "product_id": product_id,
            "location_code": location_code,
        },
        response_summary=f"Sellable={result['sellable']} at {location_code}",
        duration_ms=duration_ms,
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# GET /pricing/lookup
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/pricing/lookup")
async def pricing_lookup(
    product_id: str = Query(..., description="Product UUID"),
    location_code: str = Query(..., description="Branch code (e.g., EVANS)"),
    container_size: Optional[str] = Query(None, description="Filter by container size"),
    user: CurrentUser = Depends(get_current_user),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    Look up active pricing for a product at a location.

    Auth: role must be in system_config 'pricing.visible_to_roles'.
    Sellability is checked first — 403 if product is not sellable.
    Location lock enforced via X-Session-ID header.

    ⚠️  NO LLM — pure DB query.
    """
    start = time.time()
    client = get_supabase_client()

    # ── Check role permission via system_config ──
    try:
        config_result = (
            client.table("system_config")
            .select("value")
            .eq("key", "pricing.visible_to_roles")
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load pricing config: {str(e)[:200]}",
        )

    allowed_roles = []
    if config_result.data:
        val = config_result.data[0].get("value")
        if isinstance(val, list):
            allowed_roles = val
        elif isinstance(val, str):
            import json
            allowed_roles = json.loads(val)

    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Access denied. Your role '{user.role}' cannot view pricing. "
                f"Allowed roles: {', '.join(allowed_roles)}"
            ),
        )

    # ── Resolve location ──
    try:
        loc_result = (
            client.table("locations")
            .select("id,name,branch_code")
            .eq("branch_code", location_code.upper())
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)[:200]}",
        )

    if not loc_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location '{location_code}' not found.",
        )

    location = loc_result.data[0]
    location_id = location["id"]

    # ── Location lock enforcement ──
    if x_session_id:
        ok, existing_code = location_lock_store.check_and_lock(
            session_id=x_session_id,
            location_code=location_code.upper(),
            user_id=user.id,
        )
        if not ok:
            fire_and_forget_audit(
                user_id=user.id,
                action="pricing.location_lock_conflict",
                location_locked=existing_code,
                governance_result={
                    "attempted_location": location_code.upper(),
                    "locked_location": existing_code,
                    "session_id": x_session_id,
                },
                response_summary=f"Location lock conflict: locked to {existing_code}, attempted {location_code.upper()}",
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Session is locked to location '{existing_code}'. "
                    f"You're trying to access pricing for '{location_code.upper()}'. "
                    f"To switch locations, start a new session or clear the lock."
                ),
            )

    # ── Step 1: Verify sellability first ──
    try:
        sell_result = (
            client.table("product_sellability")
            .select("sellable")
            .eq("product_id", product_id)
            .eq("location_id", location_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)[:200]}",
        )

    if not sell_result.data or not sell_result.data[0].get("sellable", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Product is not sellable at '{location_code.upper()}'. "
                f"Pricing cannot be shown for unsellable products."
            ),
        )

    # ── Step 2: Query active pricing ──
    try:
        query = (
            client.table("pricing")
            .select("id,product_id,location_id,container_size,uom,"
                    "price_per_unit,extended_price,version,effective_date,superseded_date")
            .eq("product_id", product_id)
            .eq("location_id", location_id)
            .is_("superseded_date", "null")
        )

        if container_size:
            query = query.eq("container_size", container_size)

        pricing_result = query.execute()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)[:200]}",
        )

    duration_ms = int((time.time() - start) * 1000)

    pricing_rows = pricing_result.data or []

    result = {
        "pricing": pricing_rows,
        "count": len(pricing_rows),
        "product_id": product_id,
        "location": location["name"],
        "location_code": location["branch_code"],
        "location_locked": x_session_id is not None,
        "effective_date": pricing_rows[0].get("effective_date") if pricing_rows else None,
        "source": "governance_db",
    }

    # Audit
    fire_and_forget_audit(
        user_id=user.id,
        action="pricing.lookup",
        query_text=f"product_id={product_id}, location={location_code}, container={container_size}",
        location_locked=location_code.upper(),
        governance_result={
            "count": len(pricing_rows),
            "sellable": True,
            "location_code": location_code.upper(),
        },
        response_summary=f"Returned {len(pricing_rows)} pricing row(s) for {location_code}",
        duration_ms=duration_ms,
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# GET /governance/health
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/governance/health")
async def governance_health(
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """
    Governance engine health check — admin only.
    Returns DB connectivity status and data counts.

    ⚠️  NO LLM — pure DB query.
    """
    client = get_supabase_client()

    counts = {}
    for table, key in [
        ("products", "product_count"),
        ("product_sellability", "sellability_count"),
        ("pricing", "pricing_count"),
        ("locations", "location_count"),
    ]:
        try:
            result = client.table(table).select("id", count="exact").execute()
            counts[key] = result.count if result.count is not None else len(result.data or [])
        except Exception:
            counts[key] = -1  # Signal error

    # Active pricing (superseded_date IS NULL)
    try:
        result = (
            client.table("pricing")
            .select("id", count="exact")
            .is_("superseded_date", "null")
            .execute()
        )
        counts["active_pricing_count"] = result.count if result.count is not None else len(result.data or [])
    except Exception:
        counts["active_pricing_count"] = -1

    return {
        "status": "ok",
        "db_connected": all(v >= 0 for v in counts.values()),
        **counts,
        "session_locks_active": location_lock_store.active_locks_count,
        "version": os.getenv("APP_VERSION", "0.0.1"),
        "source": "governance_db",
    }
