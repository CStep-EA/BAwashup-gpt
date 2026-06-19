"""
Bower Ag CowCare Tool — Media Pipeline Backend Tests
Sprint 14: 8 tests for media analysis endpoints.

Tests cover:
  1. POST /media/analyze-image: feature gate blocks when disabled
  2. POST /media/analyze-image: rejects invalid file type (text/plain)
  3. POST /media/analyze-image: rejects oversized file (>10MB)
  4. POST /media/analyze-image: successful upload + analysis with governance
  5. POST /media/analyze-video: returns job_id and enqueues ARQ job
  6. POST /media/analyze-image: customer role is blocked (403)
  7. GET /media/jobs/{job_id}: owner sees status, non-owner gets 403
  8. Feature flag cache: clear_feature_cache() resets state

Uses FastAPI dependency_overrides + unittest.mock.
No real external services needed.

Usage:
  cd backend
  pytest app/tests/test_media.py -v
"""

import io
import os
import sys
import time
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import CurrentUser, get_current_user
from app.core.feature_flags import clear_feature_cache


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

client = TestClient(app)

# Mock CurrentUser objects (Pydantic models, not MagicMocks)
MOCK_CONSULTANT = CurrentUser(
    id="user-consultant-001",
    email="consultant@bowerag.test",
    role="consultant",
    location_id="loc-001",
    full_name="Test Consultant",
)

MOCK_CUSTOMER = CurrentUser(
    id="user-customer-001",
    email="customer@bowerag.test",
    role="customer",
    location_id=None,
    full_name="Test Customer",
)

MOCK_ORG_ADMIN = CurrentUser(
    id="user-admin-001",
    email="admin@bowerag.test",
    role="org_admin",
    location_id=None,
    full_name="Test Admin",
)


def _make_test_image(size_bytes: int = 1024, content_type: str = "image/jpeg") -> tuple[io.BytesIO, str]:
    """Create a fake image file of given size."""
    data = b"\xff\xd8\xff\xe0" + b"\x00" * (size_bytes - 4)  # JPEG magic + padding
    buf = io.BytesIO(data)
    buf.name = "test_image.jpg"
    return buf, content_type


def _make_test_video(size_bytes: int = 2048) -> tuple[io.BytesIO, str]:
    """Create a fake video file of given size."""
    data = b"\x00\x00\x00\x1c" + b"ftyp" + b"\x00" * (size_bytes - 8)
    buf = io.BytesIO(data)
    buf.name = "test_video.mp4"
    return buf, "video/mp4"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Override FastAPI dependency for auth
# ─────────────────────────────────────────────────────────────────────────────

def _override_auth(mock_user: CurrentUser):
    """Set FastAPI dependency override for get_current_user."""
    async def _override():
        return mock_user
    app.dependency_overrides[get_current_user] = _override


def _clear_auth_override():
    """Remove FastAPI dependency override."""
    app.dependency_overrides.pop(get_current_user, None)


def _patch_feature_enabled():
    """Patch require_feature to be a no-op (feature enabled)."""
    return patch("app.api.media.require_feature", AsyncMock(return_value=None))


def _patch_feature_disabled():
    """Patch require_feature to raise 403 (feature disabled)."""
    from fastapi import HTTPException
    async def _disabled(key: str):
        raise HTTPException(status_code=403, detail="This feature is not enabled.")
    return patch("app.api.media.require_feature", _disabled)


def _patch_storage():
    """Patch storage service for upload and presigned URL."""
    mock_storage = MagicMock()
    mock_storage.upload_bytes = AsyncMock(return_value=None)
    mock_storage.get_presigned_url = AsyncMock(return_value="https://r2.example.com/media/test.jpg?signed=1")
    return patch("app.api.media.get_storage_service", return_value=mock_storage)


def _patch_claude_vision(response_text: str = "Analysis: Healthy teat condition, score 2."):
    """Patch Claude Vision API to return a mock response."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=response_text)]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client

    return patch.dict("sys.modules", {"anthropic": mock_anthropic})


def _patch_supabase_governance(product_exists: bool = False):
    """Patch Supabase client for governance checks."""
    mock_client = MagicMock()

    # Products table mock
    mock_product_result = MagicMock()
    if product_exists:
        mock_product_result.data = [{"id": "prod-001", "product_name": "TestProduct"}]
    else:
        mock_product_result.data = []

    mock_product_chain = MagicMock()
    mock_product_chain.select.return_value = mock_product_chain
    mock_product_chain.ilike.return_value = mock_product_chain
    mock_product_chain.eq.return_value = mock_product_chain
    mock_product_chain.limit.return_value = mock_product_chain
    mock_product_chain.execute.return_value = mock_product_result

    mock_client.table.return_value = mock_product_chain

    return patch("app.api.media.get_supabase_client", return_value=mock_client)


def _patch_audit():
    """Patch audit logging to be a no-op."""
    return patch("app.api.media.fire_and_forget_audit", MagicMock())


# ─────────────────────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestFeatureGate:
    """Test 1: Feature flag blocks when disabled."""

    def test_image_upload_blocked_when_feature_disabled(self):
        """POST /media/analyze-image when feature.video_upload=false -> 403."""
        buf, ct = _make_test_image()

        try:
            _override_auth(MOCK_CONSULTANT)
            with _patch_feature_disabled():
                response = client.post(
                    "/media/analyze-image",
                    files={"file": ("test.jpg", buf, ct)},
                    data={"domain": "general"},
                )
        finally:
            _clear_auth_override()

        assert response.status_code == 403
        assert "not enabled" in response.json()["detail"].lower()


class TestImageValidation:
    """Test 2 & 3: File type and size validation."""

    def test_rejects_invalid_file_type(self):
        """POST /media/analyze-image with text/plain file -> 400."""
        buf = io.BytesIO(b"This is not an image")
        buf.name = "notes.txt"

        try:
            _override_auth(MOCK_CONSULTANT)
            with _patch_feature_enabled():
                response = client.post(
                    "/media/analyze-image",
                    files={"file": ("notes.txt", buf, "text/plain")},
                    data={"domain": "general"},
                )
        finally:
            _clear_auth_override()

        assert response.status_code == 400
        assert "jpeg" in response.json()["detail"].lower() or "JPEG" in response.json()["detail"]

    def test_rejects_oversized_image(self):
        """POST /media/analyze-image with 11MB file -> 400."""
        size_11mb = 11 * 1024 * 1024
        buf = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * (size_11mb - 4))
        buf.name = "huge.jpg"

        try:
            _override_auth(MOCK_CONSULTANT)
            with _patch_feature_enabled():
                response = client.post(
                    "/media/analyze-image",
                    files={"file": ("huge.jpg", buf, "image/jpeg")},
                    data={"domain": "general"},
                )
        finally:
            _clear_auth_override()

        assert response.status_code == 400
        assert "10MB" in response.json()["detail"] or "10mb" in response.json()["detail"].lower()


class TestImageAnalysis:
    """Test 4: Successful upload + Claude Vision analysis with governance."""

    def test_successful_image_analysis_with_governance(self):
        """POST /media/analyze-image -> 200 with analysis, governance check, teat scores."""
        buf, ct = _make_test_image(size_bytes=2048)

        try:
            _override_auth(MOCK_CONSULTANT)
            with (
                _patch_feature_enabled(),
                _patch_storage(),
                _patch_claude_vision("Teat condition: smooth ring, score 2. Healthy overall."),
                _patch_supabase_governance(product_exists=False),
                _patch_audit(),
            ):
                response = client.post(
                    "/media/analyze-image",
                    files={"file": ("cow_teats.jpg", buf, ct)},
                    data={"domain": "teat_condition"},
                )
        finally:
            _clear_auth_override()

        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        data = response.json()

        # Response schema
        assert "analysis" in data
        assert "domain" in data
        assert data["domain"] == "teat_condition"
        assert "image_url" in data
        assert "governance_applied" in data
        assert "teat_scores" in data

        # Analysis content
        assert len(data["analysis"]) > 0
        assert "score" in data["analysis"].lower() or "teat" in data["analysis"].lower()

        # Teat scores extracted
        assert data["teat_scores"] is not None
        assert 2 in data["teat_scores"]


class TestVideoUpload:
    """Test 5: Video upload creates job and returns immediately."""

    def test_video_upload_returns_job_id(self):
        """POST /media/analyze-video -> 200 with job_id."""
        buf, ct = _make_test_video(size_bytes=4096)
        fake_job_id = str(uuid.uuid4())

        # Mock DB insert for media_jobs
        mock_db = MagicMock()
        mock_insert_result = MagicMock()
        mock_insert_result.data = [{"id": fake_job_id}]
        mock_insert_chain = MagicMock()
        mock_insert_chain.insert.return_value = mock_insert_chain
        mock_insert_chain.execute.return_value = mock_insert_result
        mock_db.table.return_value = mock_insert_chain

        # Mock ARQ create_pool
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=None)
        mock_pool.close = AsyncMock(return_value=None)

        async def fake_create_pool(*args, **kwargs):
            return mock_pool

        try:
            _override_auth(MOCK_CONSULTANT)
            with (
                _patch_feature_enabled(),
                _patch_storage(),
                patch("app.api.media.get_supabase_client", return_value=mock_db),
                patch("arq.create_pool", fake_create_pool),
                _patch_audit(),
            ):
                response = client.post(
                    "/media/analyze-video",
                    files={"file": ("dairy_walk.mp4", buf, ct)},
                )
        finally:
            _clear_auth_override()

        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        data = response.json()
        assert data["job_id"] == fake_job_id
        assert data["status"] in ("processing", "pending")
        assert "message" in data
        assert len(data["message"]) > 0


class TestCustomerBlocked:
    """Test 6: Customer role cannot access media endpoints."""

    def test_customer_blocked_from_image_upload(self):
        """POST /media/analyze-image as customer -> 403."""
        buf, ct = _make_test_image()

        try:
            _override_auth(MOCK_CUSTOMER)
            response = client.post(
                "/media/analyze-image",
                files={"file": ("test.jpg", buf, ct)},
                data={"domain": "general"},
            )
        finally:
            _clear_auth_override()

        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower() or "access" in response.json()["detail"].lower()


class TestJobStatus:
    """Test 7: Job status endpoint — owner access and non-owner rejection."""

    def test_owner_can_view_job_status(self):
        """GET /media/jobs/{id} as owner -> 200 with status."""
        fake_job_id = str(uuid.uuid4())

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{
            "id": fake_job_id,
            "user_id": MOCK_CONSULTANT.id,
            "r2_path": "media/test/video.mp4",
            "status": "processing",
            "frames_extracted": 15,
            "frames_analyzed": 8,
            "result_report_id": None,
            "error_message": None,
            "created_at": "2026-05-15T10:00:00+00:00",
            "completed_at": None,
        }]
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.execute.return_value = mock_result
        mock_db.table.return_value = mock_chain

        try:
            _override_auth(MOCK_CONSULTANT)
            with patch("app.api.media.get_supabase_client", return_value=mock_db):
                response = client.get(f"/media/jobs/{fake_job_id}")
        finally:
            _clear_auth_override()

        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        data = response.json()
        assert data["job_id"] == fake_job_id
        assert data["status"] == "processing"
        assert data["frames_extracted"] == 15
        assert data["frames_analyzed"] == 8
        assert data["result_report_id"] is None

    def test_non_owner_blocked_from_job_status(self):
        """GET /media/jobs/{id} as non-owner -> 403."""
        fake_job_id = str(uuid.uuid4())

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{
            "id": fake_job_id,
            "user_id": "different-user-999",  # Not MOCK_CONSULTANT
            "r2_path": "media/other/video.mp4",
            "status": "complete",
            "frames_extracted": 30,
            "frames_analyzed": 30,
            "result_report_id": str(uuid.uuid4()),
            "error_message": None,
            "created_at": "2026-05-15T10:00:00+00:00",
            "completed_at": "2026-05-15T10:05:00+00:00",
        }]
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.execute.return_value = mock_result
        mock_db.table.return_value = mock_chain

        try:
            _override_auth(MOCK_CONSULTANT)
            with patch("app.api.media.get_supabase_client", return_value=mock_db):
                response = client.get(f"/media/jobs/{fake_job_id}")
        finally:
            _clear_auth_override()

        assert response.status_code == 403
        assert "own" in response.json()["detail"].lower()


class TestFeatureFlagCache:
    """Test 8: Feature flag cache can be cleared."""

    def test_clear_feature_cache_resets_state(self):
        """clear_feature_cache() empties the internal cache dict."""
        from app.core.feature_flags import _cache

        # Populate cache manually
        _cache["feature.test_flag"] = (True, time.time())
        assert "feature.test_flag" in _cache

        # Clear
        clear_feature_cache()
        assert len(_cache) == 0
        assert "feature.test_flag" not in _cache
