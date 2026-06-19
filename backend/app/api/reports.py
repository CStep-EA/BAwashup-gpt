"""
Bower Ag CowCare Tool — Reports API
Sprint 9: Report generation, listing, sharing, deletion.

Pipeline: Validate -> Governance check -> Create record -> Claude -> DOCX -> R2 -> Presigned URL

⚠️ Every product MUST be governance-checked before Claude is called.
⚠️ Report records are created BEFORE Claude is called so failures are tracked.
⚠️ Never expose R2 paths — always return presigned URLs.
"""

import re
import time
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import (
    CurrentUser,
    get_current_user,
    require_role,
    NON_CUSTOMER_ROLES,
    ADMIN_ROLES,
)
from app.db.supabase_client import get_supabase_client
from app.services.audit_service import fire_and_forget_audit
from app.services.claude_service import call_claude
from app.services.report_builder import build_report_docx
from app.services.storage_service import get_storage_service, StorageError

router = APIRouter(prefix="/reports", tags=["Reports"])

# Roles that can generate reports
REPORT_ROLES = ["consultant", "account_manager", "admin_manager", "org_admin"]


# ─── Request / Response Models ────────────────────────────────────────────────

class ReportRequest(BaseModel):
    customer_name: str = Field(..., min_length=1)
    operation_name: str = Field(..., min_length=1)
    location_code: str = Field(..., min_length=1)
    product_ids: list[UUID] = Field(..., min_length=1, max_length=20)
    findings: str = Field(..., min_length=1)
    recommendations: str = Field(..., min_length=1)
    rep_name: str = Field(..., min_length=1)
    rep_title: str = Field(default="Bower Ag Consultant")
    include_pricing: bool = Field(default=False)


class ReportGenerateResponse(BaseModel):
    report_id: str
    download_url: str
    status: str
    customer_name: str
    operation_name: str
    products_included: int
    pricing_included: bool
    created_at: str


class ReportSummary(BaseModel):
    report_id: str
    customer_name: str
    operation_name: str
    location_code: str
    status: str
    shared_with_customer: bool
    created_at: str


class ReportDetailResponse(BaseModel):
    report_id: str
    customer_name: str
    operation_name: str
    location_code: str
    rep_name: Optional[str] = None
    rep_title: Optional[str] = None
    include_pricing: bool
    status: str
    shared_with_customer: bool
    shared_with_user_ids: Optional[list[str]] = None
    download_url: Optional[str] = None
    created_at: str
    updated_at: str


class ShareRequest(BaseModel):
    customer_user_ids: list[UUID]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """Create a URL/filename-safe slug from text."""
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", text.lower())
    slug = re.sub(r"[\s-]+", "_", slug).strip("_")
    return slug[:60]


# ─── POST /reports/generate ───────────────────────────────────────────────────

@router.post("/generate", response_model=ReportGenerateResponse)
async def generate_report(
    body: ReportRequest,
    user: CurrentUser = Depends(require_role(REPORT_ROLES)),
):
    """
    Generate a customer-facing DOCX report.

    Pipeline:
      A. Validate location
      B. Governance check every product (sellability + pricing)
      C. Create report record (status=generating)
      D. Call Claude with REPORT_WRITING_ADDENDUM
      E. Build DOCX
      F. Upload to R2
      G. Generate presigned URL
    """
    start = time.time()
    client = get_supabase_client()
    report_date = date.today().isoformat()

    # ── STEP A: Validate location ──
    try:
        loc_result = (
            client.table("locations")
            .select("id,name,branch_code")
            .eq("branch_code", body.location_code.upper())
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    if not loc_result.data:
        raise HTTPException(404, f"Location '{body.location_code}' not found.")

    location = loc_result.data[0]
    location_id = location["id"]
    location_name = location["name"]

    # ── STEP B: Governance check every product ──
    product_details = []
    pricing_table = []

    for pid in body.product_ids:
        pid_str = str(pid)

        # Check product exists
        try:
            prod_result = (
                client.table("products")
                .select("id,product_name,part_number,chemistry_type,product_type")
                .eq("id", pid_str)
                .eq("active", True)
                .execute()
            )
        except Exception as e:
            raise HTTPException(500, f"Database error: {str(e)[:200]}")

        if not prod_result.data:
            raise HTTPException(400, f"Product ID '{pid_str}' not found or inactive.")

        product = prod_result.data[0]

        # Check sellability at location
        try:
            sell_result = (
                client.table("product_sellability")
                .select("sellable")
                .eq("product_id", pid_str)
                .eq("location_id", location_id)
                .execute()
            )
        except Exception as e:
            raise HTTPException(500, f"Database error: {str(e)[:200]}")

        if not sell_result.data or not sell_result.data[0].get("sellable", False):
            raise HTTPException(
                400,
                f"Product '{product['product_name']}' is not available at {body.location_code}. "
                f"Remove it and try again.",
            )

        product_details.append(product)

        # Fetch pricing if requested
        if body.include_pricing:
            try:
                price_result = (
                    client.table("pricing")
                    .select("container_size,uom,price_per_unit,extended_price")
                    .eq("product_id", pid_str)
                    .eq("location_id", location_id)
                    .is_("superseded_date", "null")
                    .execute()
                )
            except Exception:
                pass  # Pricing is best-effort

            for pr in (price_result.data or []):
                pricing_table.append({
                    "product_name": product["product_name"],
                    "container": f"{pr['container_size']} {pr['uom']}",
                    "price_per_unit": pr["price_per_unit"],
                    "extended": pr.get("extended_price"),
                })

    # ── STEP C: Create report record (status=generating) ──
    try:
        report_row = {
            "created_by": user.id,
            "customer_name": body.customer_name,
            "operation_name": body.operation_name,
            "location_code": body.location_code.upper(),
            "product_ids": [str(pid) for pid in body.product_ids],
            "findings": body.findings,
            "recommendations": body.recommendations,
            "rep_name": body.rep_name,
            "rep_title": body.rep_title,
            "include_pricing": body.include_pricing,
            "status": "generating",
        }
        insert_result = client.table("reports").insert(report_row).execute()
    except Exception as e:
        raise HTTPException(500, f"Failed to create report record: {str(e)[:200]}")

    if not insert_result.data:
        raise HTTPException(500, "Failed to create report record — no data returned.")

    report_id = insert_result.data[0]["id"]

    # ── STEP D: Build Claude prompt and call ──
    product_list_str = "\n".join(
        f"- {p['product_name']} ({p.get('chemistry_type', 'N/A')})"
        for p in product_details
    )
    pricing_str = ""
    if body.include_pricing and pricing_table:
        pricing_str = "\n".join(
            f"- {pt['product_name']}: {pt['container']} @ ${pt['price_per_unit']:.2f}"
            for pt in pricing_table
        )

    context_text = (
        f"CUSTOMER: {body.customer_name} | OPERATION: {body.operation_name}\n"
        f"LOCATION: {location_name}\n"
        f"REP: {body.rep_name}, {body.rep_title}\n\n"
        f"PRODUCTS:\n{product_list_str}\n\n"
        f"{'PRICING:\\n' + pricing_str + chr(10) + chr(10) if pricing_str else ''}"
        f"FINDINGS FROM VISIT:\n{body.findings}\n\n"
        f"RECOMMENDATIONS:\n{body.recommendations}"
    )

    governance_data = {
        "products": [
            {
                "name": p["product_name"],
                "chemistry": p.get("chemistry_type"),
                "type": p.get("product_type"),
            }
            for p in product_details
        ],
        "location": location_name,
        "location_code": body.location_code.upper(),
        "pricing": pricing_table if body.include_pricing else None,
    }

    try:
        claude_result = call_claude(
            messages=[{"role": "user", "content": context_text}],
            governance_data=governance_data,
            domain="PRICING" if body.include_pricing else "COW_HEALTH",
            is_report=True,
            user_role=user.role,
            location_code=body.location_code.upper(),
        )
        report_content = claude_result["reply"]
    except Exception as e:
        # Update status to failed
        try:
            client.table("reports").update({"status": "failed"}).eq("id", report_id).execute()
        except Exception:
            pass
        raise HTTPException(500, f"Claude API failed: {str(e)[:200]}")

    # Store Claude output
    try:
        client.table("reports").update({
            "report_content": report_content,
        }).eq("id", report_id).execute()
    except Exception:
        pass  # Non-critical

    # ── STEP E: Build DOCX ──
    try:
        docx_bytes = build_report_docx(
            customer_name=body.customer_name,
            operation_name=body.operation_name,
            location_name=location_name,
            rep_name=body.rep_name,
            rep_title=body.rep_title,
            report_date=report_date,
            report_content=report_content,
            pricing_table=pricing_table,
            include_pricing=body.include_pricing,
        )
    except Exception as e:
        try:
            client.table("reports").update({"status": "failed"}).eq("id", report_id).execute()
        except Exception:
            pass
        raise HTTPException(500, f"DOCX generation failed: {str(e)[:200]}")

    # ── STEP F: Upload to R2 ──
    op_slug = _slugify(body.operation_name)
    r2_path = f"reports/{user.id}/{report_id}/{op_slug}_{report_date}.docx"

    try:
        storage = get_storage_service()
        await storage.upload_bytes(
            docx_bytes,
            r2_path,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except StorageError as e:
        try:
            client.table("reports").update({"status": "failed"}).eq("id", report_id).execute()
        except Exception:
            pass
        raise HTTPException(500, f"R2 upload failed: {str(e)[:200]}")

    # Update record with R2 path and status
    try:
        client.table("reports").update({
            "docx_r2_path": r2_path,
            "status": "complete",
        }).eq("id", report_id).execute()
    except Exception:
        pass

    # ── STEP G: Generate presigned URL ──
    try:
        download_url = await storage.get_presigned_url(r2_path, expiry_seconds=86400)
    except StorageError:
        download_url = ""

    duration_ms = int((time.time() - start) * 1000)

    fire_and_forget_audit(
        user_id=user.id,
        action="report.generate",
        domain="report",
        location_locked=body.location_code.upper(),
        llm_called=True,
        governance_result={
            "report_id": report_id,
            "products": len(product_details),
            "pricing_included": body.include_pricing,
        },
        response_summary=f"Report generated for {body.operation_name}",
        duration_ms=duration_ms,
    )

    return ReportGenerateResponse(
        report_id=report_id,
        download_url=download_url,
        status="complete",
        customer_name=body.customer_name,
        operation_name=body.operation_name,
        products_included=len(product_details),
        pricing_included=body.include_pricing,
        created_at=report_date,
    )


# ─── GET /reports ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[ReportSummary])
async def list_reports(
    user: CurrentUser = Depends(require_role(REPORT_ROLES)),
):
    """List reports for the current user, sorted by created_at DESC."""
    client = get_supabase_client()

    try:
        result = (
            client.table("reports")
            .select("id,customer_name,operation_name,location_code,status,shared_with_customer,created_at")
            .eq("created_by", user.id)
            .neq("status", "deleted")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    return [
        ReportSummary(
            report_id=r["id"],
            customer_name=r["customer_name"],
            operation_name=r["operation_name"],
            location_code=r["location_code"],
            status=r["status"],
            shared_with_customer=r.get("shared_with_customer", False),
            created_at=str(r["created_at"]),
        )
        for r in (result.data or [])
    ]


# ─── GET /reports/{report_id} ────────────────────────────────────────────────

@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Get full report detail + fresh presigned URL.
    Auth: owner, admin, or shared customer.
    """
    client = get_supabase_client()

    try:
        result = (
            client.table("reports")
            .select("*")
            .eq("id", report_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    if not result.data:
        raise HTTPException(404, "Report not found.")

    report = result.data[0]

    # Access check: owner, admin, or shared customer
    is_owner = report["created_by"] == user.id
    is_admin = user.role in ADMIN_ROLES
    is_shared_customer = (
        report.get("shared_with_customer", False)
        and user.id in (report.get("shared_with_user_ids") or [])
    )

    if not (is_owner or is_admin or is_shared_customer):
        raise HTTPException(403, "You don't have access to this report.")

    # Generate fresh presigned URL
    download_url = None
    r2_path = report.get("docx_r2_path")
    if r2_path and report["status"] == "complete":
        try:
            storage = get_storage_service()
            download_url = await storage.get_presigned_url(r2_path, expiry_seconds=86400)
        except StorageError:
            pass

    return ReportDetailResponse(
        report_id=report["id"],
        customer_name=report["customer_name"],
        operation_name=report["operation_name"],
        location_code=report["location_code"],
        rep_name=report.get("rep_name"),
        rep_title=report.get("rep_title"),
        include_pricing=report.get("include_pricing", False),
        status=report["status"],
        shared_with_customer=report.get("shared_with_customer", False),
        shared_with_user_ids=report.get("shared_with_user_ids"),
        download_url=download_url,
        created_at=str(report["created_at"]),
        updated_at=str(report["updated_at"]),
    )


# ─── POST /reports/{report_id}/share ──────────────────────────────────────────

@router.post("/{report_id}/share")
async def share_report(
    report_id: str,
    body: ShareRequest,
    user: CurrentUser = Depends(require_role(REPORT_ROLES)),
):
    """
    Share a report with customer user IDs.
    Auth: owner (consultant+), account_manager, admin.
    """
    client = get_supabase_client()

    try:
        result = (
            client.table("reports")
            .select("id,created_by,shared_with_user_ids")
            .eq("id", report_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    if not result.data:
        raise HTTPException(404, "Report not found.")

    report = result.data[0]

    # Owner or admin check
    if report["created_by"] != user.id and user.role not in ADMIN_ROLES:
        raise HTTPException(403, "You can only share your own reports.")

    # Merge new user IDs with existing
    existing_ids = report.get("shared_with_user_ids") or []
    new_ids = [str(uid) for uid in body.customer_user_ids]
    merged_ids = list(set(existing_ids + new_ids))

    try:
        client.table("reports").update({
            "shared_with_customer": True,
            "shared_with_user_ids": merged_ids,
        }).eq("id", report_id).execute()
    except Exception as e:
        raise HTTPException(500, f"Failed to share report: {str(e)[:200]}")

    return {
        "report_id": report_id,
        "shared_with_user_ids": merged_ids,
        "message": "Report shared successfully",
    }


# ─── DELETE /reports/{report_id} ──────────────────────────────────────────────

@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Soft-delete a report (sets status='deleted').
    Auth: owner or org_admin only.
    Does NOT delete from R2 — kept for audit.
    """
    client = get_supabase_client()

    try:
        result = (
            client.table("reports")
            .select("id,created_by")
            .eq("id", report_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    if not result.data:
        raise HTTPException(404, "Report not found.")

    report = result.data[0]

    if report["created_by"] != user.id and user.role != "org_admin":
        raise HTTPException(403, "Only the report owner or org_admin can delete reports.")

    try:
        client.table("reports").update({
            "status": "deleted",
        }).eq("id", report_id).execute()
    except Exception as e:
        raise HTTPException(500, f"Failed to delete report: {str(e)[:200]}")

    return {"report_id": report_id, "status": "deleted", "message": "Report soft-deleted."}
