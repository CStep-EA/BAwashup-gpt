"""
Bower Ag CowCare Tool — Customer Portal API
Sprint 13: Customer-specific endpoints for viewing shared reports.

Governance:
  - Only 'customer' role can access these endpoints.
  - Only reports explicitly shared with the requesting customer are returned.
  - No internal fields exposed (no location_code, no pricing flags, no shared_with_user_ids).
  - Presigned URLs generated fresh on each request (24h expiry).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import CurrentUser, require_role
from app.db.supabase_client import get_supabase_client
from app.services.audit_service import fire_and_forget_audit
from app.services.storage_service import get_storage_service, StorageError

router = APIRouter(prefix="/customer", tags=["Customer Portal"])


# ─── Response Models ─────────────────────────────────────────────────────────

class CustomerReportSummary(BaseModel):
    report_id: str
    operation_name: str
    rep_name: Optional[str] = None
    created_at: str
    has_download: bool


class CustomerReportDetail(BaseModel):
    report_id: str
    operation_name: str
    rep_name: Optional[str] = None
    rep_title: Optional[str] = None
    report_content: Optional[str] = None
    download_url: Optional[str] = None
    created_at: str


# ─── GET /customer/reports ───────────────────────────────────────────────────

@router.get("/reports", response_model=list[CustomerReportSummary])
async def list_customer_reports(
    user: CurrentUser = Depends(require_role(["customer"])),
):
    """
    List all reports shared with the current customer.

    Returns only non-deleted reports where:
      - shared_with_customer = true
      - user.id is in shared_with_user_ids

    No internal fields are exposed (no location, pricing, shared_with_user_ids).
    """
    client = get_supabase_client()

    try:
        result = (
            client.table("reports")
            .select("id,operation_name,rep_name,docx_r2_path,created_at,shared_with_user_ids,shared_with_customer,status")
            .eq("shared_with_customer", True)
            .neq("status", "deleted")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    # Filter to only reports shared with this specific customer
    reports = []
    for r in (result.data or []):
        shared_ids = r.get("shared_with_user_ids") or []
        if user.id in shared_ids and r["status"] == "complete":
            reports.append(
                CustomerReportSummary(
                    report_id=r["id"],
                    operation_name=r["operation_name"],
                    rep_name=r.get("rep_name"),
                    created_at=str(r["created_at"]),
                    has_download=bool(r.get("docx_r2_path")),
                )
            )

    fire_and_forget_audit(
        user_id=user.id,
        action="customer.list_reports",
        domain="customer_portal",
        governance_result={"count": len(reports)},
        response_summary=f"Customer listed {len(reports)} reports",
    )

    return reports


# ─── GET /customer/reports/{report_id} ───────────────────────────────────────

@router.get("/reports/{report_id}", response_model=CustomerReportDetail)
async def get_customer_report(
    report_id: str,
    user: CurrentUser = Depends(require_role(["customer"])),
):
    """
    Get a single report detail for the current customer.

    Access check: shared_with_customer=true AND user.id in shared_with_user_ids.
    Returns report_content (the Claude-generated text) and a fresh presigned download URL.
    No internal fields are exposed.
    """
    client = get_supabase_client()

    try:
        result = (
            client.table("reports")
            .select("id,operation_name,rep_name,rep_title,report_content,docx_r2_path,created_at,shared_with_customer,shared_with_user_ids,status")
            .eq("id", report_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    if not result.data:
        raise HTTPException(404, "Report not found.")

    report = result.data[0]

    # Access check: must be shared with this customer
    is_shared = (
        report.get("shared_with_customer", False)
        and user.id in (report.get("shared_with_user_ids") or [])
    )

    if not is_shared:
        raise HTTPException(403, "You don't have access to this report.")

    if report["status"] != "complete":
        raise HTTPException(404, "Report not found.")

    # Generate fresh presigned URL if DOCX exists
    download_url = None
    r2_path = report.get("docx_r2_path")
    if r2_path:
        try:
            storage = get_storage_service()
            download_url = await storage.get_presigned_url(r2_path, expiry_seconds=86400)
        except StorageError:
            pass

    fire_and_forget_audit(
        user_id=user.id,
        action="customer.view_report",
        domain="customer_portal",
        governance_result={"report_id": report_id},
        response_summary=f"Customer viewed report {report['operation_name']}",
    )

    return CustomerReportDetail(
        report_id=report["id"],
        operation_name=report["operation_name"],
        rep_name=report.get("rep_name"),
        rep_title=report.get("rep_title"),
        report_content=report.get("report_content"),
        download_url=download_url,
        created_at=str(report["created_at"]),
    )
