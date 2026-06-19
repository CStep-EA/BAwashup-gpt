"""
Bower Ag CowCare Tool — Product Catalog API
Sprint 8: Full product list, detail, and category metadata endpoints.

⚠️  NO LLM — pure DB queries against Supabase.
    All product, sellability, and pricing data comes from governance tables.
"""

import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.auth import (
    CurrentUser,
    get_current_user,
    require_role,
    NON_CUSTOMER_ROLES,
)
from app.db.supabase_client import get_supabase_client
from app.services.audit_service import fire_and_forget_audit

router = APIRouter(prefix="/products", tags=["Products"])


# ─── Response Models ──────────────────────────────────────────────────────────

class ProductSummary(BaseModel):
    id: str
    product_name: str
    part_number: Optional[str] = None
    category: str
    product_type: str
    chemistry_type: Optional[str] = None
    germicide_type: Optional[str] = None
    usage_timing: Optional[str] = None
    is_concentrate: bool = False
    emollient_pct: Optional[float] = None
    emollient_type: Optional[str] = None
    notes: Optional[str] = None
    sds_verified: bool = False


class ProductListResponse(BaseModel):
    products: list[ProductSummary]
    total_count: int
    has_more: bool


class SellabilityEntry(BaseModel):
    location_name: str
    branch_code: str
    sellable: bool


class PricingEntry(BaseModel):
    container_size: str
    uom: str
    price_per_unit: float
    extended_price: Optional[float] = None


class ProductDetailResponse(ProductSummary):
    sellability: list[SellabilityEntry]
    my_location_pricing: list[PricingEntry]


class CategoryMetadata(BaseModel):
    categories: list[str]
    chemistry_types: list[str]
    product_types: list[str]


# ─── GET /products/categories ─────────────────────────────────────────────────

@router.get("/categories", response_model=CategoryMetadata)
async def get_product_categories(
    user: CurrentUser = Depends(require_role(NON_CUSTOMER_ROLES)),
):
    """
    Return distinct category, chemistry_type, and product_type values.
    Used to populate filter dropdowns in the UI.

    ⚠️  NO LLM — pure DB query.
    """
    client = get_supabase_client()

    try:
        # Get distinct categories
        cat_result = (
            client.table("products")
            .select("category")
            .eq("active", True)
            .execute()
        )
        categories = sorted(set(
            row["category"] for row in (cat_result.data or []) if row.get("category")
        ))

        # Get distinct chemistry_types
        chem_result = (
            client.table("products")
            .select("chemistry_type")
            .eq("active", True)
            .not_.is_("chemistry_type", "null")
            .execute()
        )
        chemistry_types = sorted(set(
            row["chemistry_type"] for row in (chem_result.data or []) if row.get("chemistry_type")
        ))

        # Get distinct product_types
        pt_result = (
            client.table("products")
            .select("product_type")
            .eq("active", True)
            .execute()
        )
        product_types = sorted(set(
            row["product_type"] for row in (pt_result.data or []) if row.get("product_type")
        ))

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch categories: {str(e)[:200]}",
        )

    return CategoryMetadata(
        categories=categories,
        chemistry_types=chemistry_types,
        product_types=product_types,
    )


# ─── GET /products ─────────────────────────────────────────────────────────────

@router.get("", response_model=ProductListResponse)
async def list_products(
    search: Optional[str] = Query(None, min_length=1, description="Search by name or part number"),
    category: Optional[str] = Query(None, description="Filter by category: teat_dip, chemical, cip"),
    chemistry: Optional[str] = Query(None, description="Filter by chemistry_type ILIKE"),
    location_code: Optional[str] = Query(None, description="Only return products sellable at this location"),
    limit: int = Query(25, ge=1, le=100, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    user: CurrentUser = Depends(require_role(NON_CUSTOMER_ROLES)),
):
    """
    List products with optional search + filter. Pagination via limit/offset.

    Filters are AND logic — all active filters apply simultaneously.
    Always filters WHERE active = true.

    ⚠️  NO LLM — pure DB query.
    """
    start = time.time()
    client = get_supabase_client()

    select_fields = (
        "id,product_name,part_number,category,product_type,"
        "chemistry_type,germicide_type,usage_timing,"
        "is_concentrate,emollient_pct,emollient_type,notes,sds_verified"
    )

    try:
        # If location_code filter is provided, get sellable product_ids first
        sellable_product_ids: Optional[set] = None
        if location_code:
            loc_result = (
                client.table("locations")
                .select("id")
                .eq("branch_code", location_code.upper())
                .execute()
            )
            if not loc_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Location '{location_code}' not found.",
                )
            location_id = loc_result.data[0]["id"]

            sell_result = (
                client.table("product_sellability")
                .select("product_id")
                .eq("location_id", location_id)
                .eq("sellable", True)
                .execute()
            )
            sellable_product_ids = set(
                row["product_id"] for row in (sell_result.data or [])
            )

        # Build main query
        query = (
            client.table("products")
            .select(select_fields, count="exact")
            .eq("active", True)
        )

        # Apply search filter (ILIKE on product_name, or exact part_number)
        if search:
            # Use or_ filter: product_name ILIKE or part_number ILIKE
            query = query.or_(
                f"product_name.ilike.%{search}%,part_number.ilike.%{search}%"
            )

        # Apply category filter
        if category:
            query = query.eq("product_type", category)

        # Apply chemistry filter
        if chemistry:
            query = query.ilike("chemistry_type", f"%{chemistry}%")

        # Apply sellable product IDs filter
        if sellable_product_ids is not None:
            if not sellable_product_ids:
                # No products sellable at this location
                return ProductListResponse(products=[], total_count=0, has_more=False)
            query = query.in_("id", list(sellable_product_ids))

        # Apply pagination
        query = query.order("product_name").range(offset, offset + limit - 1)

        result = query.execute()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)[:200]}",
        )

    products = [ProductSummary(**row) for row in (result.data or [])]
    total_count = result.count if result.count is not None else len(products)
    has_more = (offset + limit) < total_count

    duration_ms = int((time.time() - start) * 1000)

    # Audit (fire-and-forget)
    fire_and_forget_audit(
        user_id=user.id,
        action="products.list",
        query_text=f"search={search}, category={category}, chemistry={chemistry}, location={location_code}",
        governance_result={"total_count": total_count, "returned": len(products)},
        response_summary=f"Returned {len(products)}/{total_count} products",
        duration_ms=duration_ms,
    )

    return ProductListResponse(
        products=products,
        total_count=total_count,
        has_more=has_more,
    )


# ─── GET /products/{product_id} ────────────────────────────────────────────────

@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product_detail(
    product_id: str,
    user: CurrentUser = Depends(require_role(NON_CUSTOMER_ROLES)),
):
    """
    Get full product detail including sellability at all 5 locations
    and pricing at the user's assigned location.

    ⚠️  NO LLM — pure DB query.
    """
    start = time.time()
    client = get_supabase_client()

    # Fetch product
    try:
        prod_result = (
            client.table("products")
            .select("*")
            .eq("id", product_id)
            .eq("active", True)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)[:200]}",
        )

    if not prod_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found or inactive.",
        )

    product = prod_result.data[0]

    # Fetch all locations for sellability matrix
    try:
        locations_result = (
            client.table("locations")
            .select("id,name,branch_code")
            .order("branch_code")
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch locations: {str(e)[:200]}",
        )

    locations = locations_result.data or []

    # Fetch sellability for this product across all locations
    try:
        sell_result = (
            client.table("product_sellability")
            .select("location_id,sellable")
            .eq("product_id", product_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sellability: {str(e)[:200]}",
        )

    # Build sellability map: location_id -> sellable
    sell_map = {
        row["location_id"]: row["sellable"]
        for row in (sell_result.data or [])
    }

    sellability = [
        SellabilityEntry(
            location_name=loc["name"],
            branch_code=loc["branch_code"],
            sellable=sell_map.get(loc["id"], False),
        )
        for loc in locations
    ]

    # Fetch pricing at user's location (from profile)
    my_location_pricing: list[PricingEntry] = []
    if user.location_id:
        try:
            pricing_result = (
                client.table("pricing")
                .select("container_size,uom,price_per_unit,extended_price")
                .eq("product_id", product_id)
                .eq("location_id", user.location_id)
                .is_("superseded_date", "null")
                .execute()
            )
            my_location_pricing = [
                PricingEntry(**row) for row in (pricing_result.data or [])
            ]
        except Exception:
            # Non-critical — pricing just won't show
            pass

    duration_ms = int((time.time() - start) * 1000)

    fire_and_forget_audit(
        user_id=user.id,
        action="products.detail",
        query_text=f"product_id={product_id}",
        governance_result={
            "product_name": product["product_name"],
            "sellability_count": len([s for s in sellability if s.sellable]),
        },
        response_summary=f"Product detail: {product['product_name']}",
        duration_ms=duration_ms,
    )

    return ProductDetailResponse(
        id=product["id"],
        product_name=product["product_name"],
        part_number=product.get("part_number"),
        category=product["category"],
        product_type=product["product_type"],
        chemistry_type=product.get("chemistry_type"),
        germicide_type=product.get("germicide_type"),
        usage_timing=product.get("usage_timing"),
        is_concentrate=product.get("is_concentrate", False),
        emollient_pct=product.get("emollient_pct"),
        emollient_type=product.get("emollient_type"),
        notes=product.get("notes"),
        sds_verified=product.get("sds_verified", False),
        sellability=sellability,
        my_location_pricing=my_location_pricing,
    )
