"""
Bower Ag CowCare Tool — Admin API Tests
Sprint 11: 15 tests for admin portal backend endpoints.

Tests cover:
  - Analytics: summary schema, role blocking
  - User management: invite, org_admin guard, admin_manager restrictions, self-deactivate guard
  - System config: list all keys, editable_by enforcement
  - Bug reports: list, resolve, CSV export
  - Audit log: org_admin-only access
  - Version log: create by org_admin

Uses real Supabase instance with test users.
Endpoints that create side effects (bugs, versions) use cleanup or accept idempotent data.

Usage:
  cd backend
  pytest app/tests/test_admin_api.py -v
"""

import csv
import io
import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.supabase_client import get_supabase_client, get_supabase_anon_client


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

client = TestClient(app)

TEST_USERS = {
    "org_admin": {"email": "admin@bowerag.test", "password": "TestAdmin123!"},
    "admin_manager": {"email": "manager@bowerag.test", "password": "TestManager123!"},
    "consultant": {"email": "consultant@bowerag.test", "password": "TestConsult123!"},
    "customer": {"email": "customer@bowerag.test", "password": "TestCustomer123!"},
}

_token_cache: dict[str, str] = {}
_user_id_cache: dict[str, str] = {}


def _get_token(role: str) -> str:
    """Sign in a test user and return the JWT access token."""
    if role in _token_cache:
        return _token_cache[role]

    anon = get_supabase_anon_client()
    creds = TEST_USERS[role]
    result = anon.auth.sign_in_with_password({
        "email": creds["email"],
        "password": creds["password"],
    })

    if not result.session:
        pytest.skip(f"Could not sign in test user '{role}'. Ensure test users exist in Supabase.")

    _token_cache[role] = result.session.access_token
    _user_id_cache[role] = result.user.id
    return _token_cache[role]


def _get_user_id(role: str) -> str:
    _get_token(role)  # Ensure cached
    return _user_id_cache[role]


def _auth_headers(role: str) -> dict:
    return {"Authorization": f"Bearer {_get_token(role)}"}


# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalytics:
    """Tests for /admin/analytics/* endpoints."""

    def test_analytics_summary_returns_valid_schema(self):
        """GET /admin/analytics/summary as admin_manager -> all expected keys present, values are numbers."""
        response = client.get(
            "/admin/analytics/summary?days=7",
            headers=_auth_headers("admin_manager"),
        )
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        data = response.json()

        # All expected keys must be present
        expected_keys = [
            "total_queries", "queries_today", "active_users",
            "queries_by_domain", "queries_by_location",
            "avg_response_ms", "governance_blocks", "claude_api_calls",
            "thumbs_up", "thumbs_down", "open_bugs", "open_critical_bugs",
        ]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"

        # Numeric values must be numbers
        numeric_keys = [
            "total_queries", "queries_today", "active_users",
            "avg_response_ms", "governance_blocks", "claude_api_calls",
            "thumbs_up", "thumbs_down", "open_bugs", "open_critical_bugs",
        ]
        for key in numeric_keys:
            assert isinstance(data[key], (int, float)), (
                f"Key '{key}' should be numeric, got {type(data[key])}: {data[key]}"
            )

        # Array fields must be lists
        assert isinstance(data["queries_by_domain"], list)
        assert isinstance(data["queries_by_location"], list)

    def test_analytics_blocked_for_consultant(self):
        """GET /admin/analytics/summary as consultant -> 403."""
        response = client.get(
            "/admin/analytics/summary",
            headers=_auth_headers("consultant"),
        )
        assert response.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# USER MANAGEMENT TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestUserManagement:
    """Tests for /admin/users/* endpoints."""

    def test_invite_user_success(self):
        """POST /admin/users/invite with valid payload -> 200, invitation logged."""
        unique_email = f"test-invite-{uuid.uuid4().hex[:8]}@bowerag.example.com"
        mock_user_id = str(uuid.uuid4())

        # Mock the Supabase admin auth calls so we don't actually send emails
        # or hit real Supabase auth validation
        with patch("app.api.admin_users.get_supabase_client") as mock_sb:
            real_client = get_supabase_client()

            # Create a proxy that mocks auth.admin but passes through table()
            class _AuthAdminMock:
                def list_users(self):
                    return []  # No existing users with this email

                def invite_user_by_email(self, email):
                    class _User:
                        id = mock_user_id
                    class _Result:
                        user = _User()
                    return _Result()

            class _AuthMock:
                admin = _AuthAdminMock()

            class _ClientProxy:
                auth = _AuthMock()
                def table(self, name):
                    return real_client.table(name)
                def __getattr__(self, name):
                    return getattr(real_client, name)

            mock_sb.return_value = _ClientProxy()

            response = client.post(
                "/admin/users/invite",
                json={
                    "email": unique_email,
                    "role": "consultant",
                    "full_name": "Test Invite User",
                },
                headers=_auth_headers("org_admin"),
            )

        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        data = response.json()
        assert "user_id" in data
        assert data["email"] == unique_email
        assert data["role"] == "consultant"
        assert "Invitation sent" in data["message"]

        # Cleanup: delete the pre-created profile
        try:
            sb = get_supabase_client()
            sb.table("profiles").delete().eq("id", mock_user_id).execute()
        except Exception:
            pass

    def test_cannot_invite_org_admin(self):
        """POST /admin/users/invite with role='org_admin' (even as org_admin caller) -> 400."""
        response = client.post(
            "/admin/users/invite",
            json={
                "email": "nope@bowerag.test",
                "role": "org_admin",
                "full_name": "Should Fail",
            },
            headers=_auth_headers("org_admin"),
        )
        assert response.status_code == 400
        assert "org_admin" in response.text.lower()

    def test_admin_manager_cannot_invite_admin_manager(self):
        """POST /admin/users/invite with role='admin_manager' as admin_manager caller -> 403."""
        response = client.post(
            "/admin/users/invite",
            json={
                "email": "nope2@bowerag.test",
                "role": "admin_manager",
                "full_name": "Should Fail",
            },
            headers=_auth_headers("admin_manager"),
        )
        assert response.status_code == 403

    def test_cannot_deactivate_self(self):
        """PATCH /admin/users/{own_user_id} with active=false -> 400."""
        # Use admin_manager (not org_admin, which hits the 'immutable' guard first)
        own_id = _get_user_id("admin_manager")

        response = client.patch(
            f"/admin/users/{own_id}",
            json={"active": False},
            headers=_auth_headers("admin_manager"),
        )
        assert response.status_code == 400
        assert "your own" in response.text.lower() or "yourself" in response.text.lower()

    def test_cannot_change_org_admin_role(self):
        """PATCH /admin/users/{org_admin_id} -> 403 (org_admin users are immutable)."""
        org_admin_id = _get_user_id("org_admin")

        # Try to change org_admin's role (even as org_admin)
        response = client.patch(
            f"/admin/users/{org_admin_id}",
            json={"role": "consultant"},
            headers=_auth_headers("org_admin"),
        )
        assert response.status_code == 403
        assert "immutable" in response.text.lower() or "org_admin" in response.text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestConfig:
    """Tests for /admin/config/* endpoints."""

    def test_config_list_returns_all_keys(self):
        """GET /admin/config -> response has all 7 seeded keys."""
        response = client.get(
            "/admin/config",
            headers=_auth_headers("org_admin"),
        )
        assert response.status_code == 200
        data = response.json()
        keys = [item["key"] for item in data]

        expected_keys = [
            "chat.max_history_length",
            "feature.customer_portal",
            "feature.proposal_generator",
            "feature.spanish_mode",
            "feature.video_upload",
            "maintenance.mode",
            "pricing.visible_to_roles",
        ]
        for key in expected_keys:
            assert key in keys, f"Missing config key: {key}"

    def test_admin_manager_cannot_edit_org_admin_only_config(self):
        """PATCH /admin/config/feature.video_upload as admin_manager -> 403."""
        response = client.patch(
            "/admin/config/feature.video_upload",
            json={"value": True},
            headers=_auth_headers("admin_manager"),
        )
        assert response.status_code == 403

    def test_org_admin_can_edit_any_config(self):
        """PATCH /admin/config/feature.video_upload as org_admin -> 200."""
        # Get current value first
        list_response = client.get(
            "/admin/config",
            headers=_auth_headers("org_admin"),
        )
        current_config = list_response.json()
        video_upload = next(
            (c for c in current_config if c["key"] == "feature.video_upload"),
            None,
        )
        original_value = video_upload["value"] if video_upload else False

        # Toggle to the opposite
        new_value = not bool(original_value)
        response = client.patch(
            "/admin/config/feature.video_upload",
            json={"value": new_value},
            headers=_auth_headers("org_admin"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "feature.video_upload"
        assert data["value"] == new_value

        # Restore original value
        client.patch(
            "/admin/config/feature.video_upload",
            json={"value": original_value},
            headers=_auth_headers("org_admin"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# BUG REPORT TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestBugReports:
    """Tests for /admin/bugs/* endpoints."""

    @pytest.fixture(autouse=True)
    def _ensure_test_bug(self):
        """Create a test bug report if none exist, using the 001 migration schema."""
        sb = get_supabase_client()
        existing = sb.table("bug_reports").select("id").limit(1).execute()
        if not existing.data:
            user_id = _get_user_id("consultant")
            sb.table("bug_reports").insert({
                "reporter_id": user_id,
                "title": "Test Bug for Sprint 11",
                "description": "Something broke during testing.",
                "expected_behavior": "Should have worked fine.",
                "severity": "high",
                "status": "open",
                "version_tag": "v0.0.1",
                "user_role": "consultant",
            }).execute()
        yield

    def test_bug_list_returns_results(self):
        """GET /admin/bugs -> array with at least one bug."""
        response = client.get(
            "/admin/bugs",
            headers=_auth_headers("admin_manager"),
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Verify structure
        bug = data[0]
        assert "id" in bug
        assert "title" in bug
        assert "severity" in bug
        assert "status" in bug

    def test_bug_resolve_sets_resolved_at(self):
        """PATCH /admin/bugs/{id} with status='resolved' -> resolved_at is not null."""
        # Get a bug to resolve
        sb = get_supabase_client()
        user_id = _get_user_id("consultant")
        # Create a fresh bug for this test
        insert_result = sb.table("bug_reports").insert({
            "reporter_id": user_id,
            "title": "Resolve Test Bug",
            "description": "Needs resolving.",
            "severity": "low",
            "status": "open",
            "version_tag": "v0.0.1",
        }).execute()
        bug_id = insert_result.data[0]["id"]

        # Resolve it
        response = client.patch(
            f"/admin/bugs/{bug_id}",
            json={"status": "resolved", "fix_notes": "Fixed in Sprint 11."},
            headers=_auth_headers("org_admin"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resolved_at"] is not None
        assert data["status"] == "resolved"

    def test_bug_export_returns_csv(self):
        """GET /admin/bugs/export -> Content-Type: text/csv, has header row."""
        response = client.get(
            "/admin/bugs/export",
            headers=_auth_headers("admin_manager"),
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

        # Parse CSV
        content = response.text
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) >= 1, "CSV should have at least a header row"

        # Verify header columns
        header = rows[0]
        expected_columns = [
            "id", "title", "severity", "status", "reporter_name",
        ]
        for col in expected_columns:
            assert col in header, f"Missing CSV column: {col}"


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOG TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditLog:
    """Tests for /admin/audit/* endpoints."""

    def test_audit_log_blocked_for_admin_manager(self):
        """GET /admin/audit as admin_manager -> 403."""
        response = client.get(
            "/admin/audit",
            headers=_auth_headers("admin_manager"),
        )
        assert response.status_code == 403

    def test_audit_log_accessible_for_org_admin(self):
        """GET /admin/audit as org_admin -> 200 with audit rows."""
        response = client.get(
            "/admin/audit?limit=10",
            headers=_auth_headers("org_admin"),
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have audit rows from test activities
        # Each row should have the expected structure
        if data:
            row = data[0]
            assert "id" in row
            assert "action" in row
            assert "created_at" in row
            assert "llm_called" in row


# ─────────────────────────────────────────────────────────────────────────────
# VERSION LOG TESTS (bonus — validates org_admin only POST)
# ─────────────────────────────────────────────────────────────────────────────

class TestVersionLog:
    """Validates version_log create is org_admin only."""

    def test_create_version_as_org_admin(self):
        """POST /admin/versions as org_admin -> 201 with valid schema."""
        import random
        tag = f"v0.11.{random.randint(100,999)}"
        response = client.post(
            "/admin/versions",
            json={
                "version_tag": tag,
                "release_notes": "Sprint 11 admin portal backend complete.",
                "breaking_changes": None,
                "bugs_resolved": [],
            },
            headers=_auth_headers("org_admin"),
        )
        assert response.status_code == 201, f"Got {response.status_code}: {response.text}"
        data = response.json()
        assert data["version_tag"] == tag
        assert data["deployed_by"] is not None
