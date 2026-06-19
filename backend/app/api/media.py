"""
Bower Ag CowCare Tool — Media Analysis API
Sprint 14: Image upload + Claude Vision analysis, video upload + ARQ job queueing.

Endpoints:
  POST /media/analyze-image — Sync image analysis via Claude Vision
  POST /media/analyze-video — Async video processing via ARQ
  GET  /media/jobs/{job_id}  — Poll video job status

Feature gate: feature.video_upload must be enabled in system_config.
"""

import base64
import io
import os
import re
import time
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from PIL import Image

from app.core.auth import CurrentUser, require_role
from app.core.feature_flags import require_feature
from app.db.supabase_client import get_supabase_client
from app.services.audit_service import fire_and_forget_audit
from app.services.storage_service import get_storage_service, StorageError

router = APIRouter(prefix="/media", tags=["Media"])

# Roles that can use media endpoints (NOT account_manager, NOT customer)
MEDIA_ROLES = ["consultant", "technician", "admin_manager", "org_admin"]

# Limits
MAX_IMAGE_SIZE = 10 * 1024 * 1024       # 10MB
MAX_VIDEO_SIZE = 500 * 1024 * 1024       # 500MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/heic", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo"}

# Claude Vision model
CLAUDE_MODEL = "claude-sonnet-4-20250514"
VISION_MAX_TOKENS = 1024

# ─── Vision prompts by domain ───────────────────────────────────────────────

VISION_PROMPTS = {
    "teat_condition": (
        "You are a dairy cow care expert. Analyze this image of cow teats. "
        "Score each visible teat end using the 4-point hyperkeratosis scale: "
        "1=Normal (smooth), 2=Slight (smooth ring), 3=Moderate (rough ring), "
        "4=Severe (rough with tags). "
        "Report: approximate score, what you observe, and one practical next step."
    ),
    "equipment": (
        "You are a dairy equipment specialist. Identify any equipment visible in this image. "
        "Note condition, any visible wear, deposits, or potential issues. "
        "Suggest any relevant maintenance or product categories (do not invent specific products)."
    ),
    "parlor": (
        "You are a dairy parlor expert. Analyze this parlor or barn image. "
        "Identify: cleanliness indicators, equipment condition, any visible CIP or chemical systems. "
        "Note any concerns and suggest general areas for improvement."
    ),
    "general": (
        "You are a dairy industry expert. Describe what you see in this image "
        "in the context of dairy cow care, milking operations, or animal health. "
        "Be specific and practical."
    ),
}


# ─── Response models ─────────────────────────────────────────────────────────

class ImageAnalysisResponse(BaseModel):
    analysis: str
    domain: str
    image_url: str
    governance_applied: bool
    teat_scores: Optional[list[int]] = None


class VideoUploadResponse(BaseModel):
    job_id: str
    status: str
    message: str


class MediaJobResponse(BaseModel):
    job_id: str
    status: str
    frames_extracted: Optional[int] = None
    frames_analyzed: Optional[int] = None
    result_report_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


# ─── POST /media/analyze-image ───────────────────────────────────────────────

@router.post("/analyze-image", response_model=ImageAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    domain: str = Form(default="general"),
    user: CurrentUser = Depends(require_role(MEDIA_ROLES)),
):
    """
    Upload an image and get Claude Vision analysis.
    Feature-gated: requires feature.video_upload = true.
    """
    # Feature gate (BEFORE reading file)
    await require_feature("feature.video_upload")

    start = time.time()

    # ── Validation ──
    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "Please upload a JPEG, PNG, HEIC, or WebP image.")

    # Read file bytes
    file_bytes = await file.read()
    if len(file_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(400, "Image must be under 10MB.")

    if len(file_bytes) == 0:
        raise HTTPException(400, "Empty file uploaded.")

    # ── Step A: Upload to R2 ──
    timestamp = int(time.time())
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", file.filename or "image")
    r2_path = f"media/{user.id}/{date.today().isoformat()}/{timestamp}_{safe_name}"

    try:
        storage = get_storage_service()
        await storage.upload_bytes(file_bytes, r2_path, content_type)
    except StorageError as e:
        raise HTTPException(500, f"Failed to upload image: {str(e)[:200]}")

    # ── Step B: Convert to base64 for Claude Vision ──
    media_type = content_type
    image_data = file_bytes

    # HEIC → JPEG conversion (Claude Vision doesn't accept HEIC)
    if content_type == "image/heic":
        try:
            img = Image.open(io.BytesIO(file_bytes))
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=90)
            buf.seek(0)
            image_data = buf.read()
            media_type = "image/jpeg"
        except Exception as e:
            raise HTTPException(400, f"Failed to convert HEIC image: {str(e)[:100]}")

    b64_data = base64.b64encode(image_data).decode()

    # ── Step C: Build Vision prompt ──
    vision_prompt = VISION_PROMPTS.get(domain, VISION_PROMPTS["general"])

    # ── Step D: Call Claude Vision API ──
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=VISION_MAX_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64_data,
                            },
                        },
                        {"type": "text", "text": vision_prompt},
                    ],
                }
            ],
        )
        analysis_text = response.content[0].text
    except Exception as e:
        raise HTTPException(500, f"Claude Vision API failed: {str(e)[:200]}")

    # ── Step E: Governance check on Vision output ──
    governance_applied = False
    governed_text = analysis_text

    # Look for potential product mentions
    db_client = get_supabase_client()
    product_mentions = re.findall(
        r"\b([A-Z][a-z]+(?:\s+[A-Z0-9][a-z0-9]*)+)\b", analysis_text
    )

    for name in set(product_mentions):
        try:
            result = (
                db_client.table("products")
                .select("id,product_name")
                .ilike("product_name", f"%{name}%")
                .eq("active", True)
                .limit(1)
                .execute()
            )
            if not result.data:
                # Product doesn't exist in master — replace
                governed_text = governed_text.replace(
                    name,
                    "[Product category] options are available -- ask your Bower Ag rep for specifics.",
                )
                governance_applied = True
            else:
                # Check sellability at user's location if location is set
                if user.location_id:
                    product_id = result.data[0]["id"]
                    sell_result = (
                        db_client.table("product_sellability")
                        .select("sellable")
                        .eq("product_id", product_id)
                        .eq("location_id", user.location_id)
                        .limit(1)
                        .execute()
                    )
                    if sell_result.data and not sell_result.data[0].get("sellable", True):
                        prod_name = result.data[0]["product_name"]
                        governed_text = governed_text.replace(
                            name,
                            f"{prod_name} is not currently available at your location -- "
                            "your rep can suggest an alternative.",
                        )
                        governance_applied = True
        except Exception:
            pass  # Skip governance for this mention

    # ── Extract teat scores if applicable ──
    teat_scores = None
    if domain == "teat_condition":
        scores = re.findall(r"\b([1-4])\b", governed_text)
        if scores:
            teat_scores = [int(s) for s in scores[:20]]  # Max 20 teats

    # ── Generate presigned URL ──
    try:
        image_url = await storage.get_presigned_url(r2_path, expiry_seconds=3600)
    except StorageError:
        image_url = ""

    # ── Step F: Audit log ──
    duration_ms = int((time.time() - start) * 1000)
    fire_and_forget_audit(
        user_id=user.id,
        action="image_analysis",
        domain=domain,
        llm_called=True,
        governance_result={
            "media_url": r2_path,
            "governance_applied": governance_applied,
        },
        response_summary=f"Image analyzed ({domain})",
        duration_ms=duration_ms,
    )

    return ImageAnalysisResponse(
        analysis=governed_text,
        domain=domain,
        image_url=image_url,
        governance_applied=governance_applied,
        teat_scores=teat_scores,
    )


# ─── POST /media/analyze-video ───────────────────────────────────────────────

@router.post("/analyze-video", response_model=VideoUploadResponse)
async def analyze_video(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_role(MEDIA_ROLES)),
):
    """
    Upload a video for async analysis. Returns immediately with job_id.
    Feature-gated: requires feature.video_upload = true.
    """
    # Feature gate
    await require_feature("feature.video_upload")

    # ── Validation ──
    content_type = file.content_type or ""
    if content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(400, "Please upload an MP4, MOV, or AVI video.")

    # Read file (streaming for large files)
    file_bytes = await file.read()
    if len(file_bytes) > MAX_VIDEO_SIZE:
        raise HTTPException(400, "Video must be under 500MB.")

    if len(file_bytes) == 0:
        raise HTTPException(400, "Empty file uploaded.")

    # ── Step A: Upload to R2 ──
    timestamp = int(time.time())
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", file.filename or "video.mp4")
    r2_path = f"media/{user.id}/video/{date.today().isoformat()}/{timestamp}_{safe_name}"

    try:
        storage = get_storage_service()
        await storage.upload_bytes(file_bytes, r2_path, content_type)
    except StorageError as e:
        raise HTTPException(500, f"Failed to upload video: {str(e)[:200]}")

    # ── Step B: Create job record ──
    db_client = get_supabase_client()
    try:
        job_result = db_client.table("media_jobs").insert({
            "user_id": user.id,
            "r2_path": r2_path,
            "status": "pending",
        }).execute()
    except Exception as e:
        raise HTTPException(500, f"Failed to create job record: {str(e)[:200]}")

    job_id = job_result.data[0]["id"]

    # ── Step C: Enqueue ARQ job ──
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        pool = await create_pool(RedisSettings.from_dsn(redis_url))
        await pool.enqueue_job("process_video", job_id, user.id, r2_path)
        await pool.close()
    except Exception as e:
        # If Redis/ARQ is unavailable, update job as failed
        _update_job_status_direct(job_id, "failed", f"Queue unavailable: {str(e)[:200]}")
        raise HTTPException(500, f"Job queue unavailable: {str(e)[:200]}")

    # ── Step D: Return immediately ──
    fire_and_forget_audit(
        user_id=user.id,
        action="video_upload",
        domain="media",
        governance_result={"job_id": job_id, "r2_path": r2_path},
        response_summary="Video uploaded for analysis",
    )

    return VideoUploadResponse(
        job_id=job_id,
        status="processing",
        message=(
            "Your video is being analyzed. This usually takes 3-5 minutes. "
            "We will have your report ready shortly."
        ),
    )


# ─── GET /media/jobs/{job_id} ────────────────────────────────────────────────

@router.get("/jobs/{job_id}", response_model=MediaJobResponse)
async def get_media_job(
    job_id: str,
    user: CurrentUser = Depends(require_role(MEDIA_ROLES)),
):
    """
    Check the status of a video analysis job.
    Auth: job owner only.
    """
    db_client = get_supabase_client()

    try:
        result = (
            db_client.table("media_jobs")
            .select("*")
            .eq("id", job_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    if not result.data:
        raise HTTPException(404, "Job not found.")

    job = result.data[0]

    # Owner check
    if job["user_id"] != user.id:
        raise HTTPException(403, "You can only view your own jobs.")

    return MediaJobResponse(
        job_id=job["id"],
        status=job["status"],
        frames_extracted=job.get("frames_extracted"),
        frames_analyzed=job.get("frames_analyzed"),
        result_report_id=str(job["result_report_id"]) if job.get("result_report_id") else None,
        error_message=job.get("error_message"),
        created_at=str(job["created_at"]),
        completed_at=str(job["completed_at"]) if job.get("completed_at") else None,
    )


# ─── Helper ──────────────────────────────────────────────────────────────────

def _update_job_status_direct(
    job_id: str,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    """Update job status directly (used when ARQ is unavailable)."""
    try:
        client = get_supabase_client()
        fields: dict = {"status": status}
        if error_message:
            fields["error_message"] = error_message[:500]
        client.table("media_jobs").update(fields).eq("id", job_id).execute()
    except Exception:
        pass
