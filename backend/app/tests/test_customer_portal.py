"""
Bower Ag CowCare Tool — Customer Portal Backend Tests
Sprint 13: 6 tests for customer-specific report endpoints.

Tests cover:
  - GET /customer/reports: returns only shared reports for customer
  - GET /customer/reports: blocks non-customer roles (consultant -> 403)
  - GET /customer/reports/{id}: returns report detail with content
  - GET /customer/reports/{id}: blocks access to unshared reports (403)
  - GET /customer/reports/{id}: blocks non-customer roles (403)
  - GET /customer/reports/{id}: returns 404 for non-existent report

Usage:
  cd backend
  pytest app/tests/test_customer_portal.py -v
"""

import os
import sys

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
# Helper: ensure a shared test report exists
# ─────────────────────────────────────────────────────────────────────────────

_test_report_id: str | None = None


def _ensure_shared_report() -> str:
    """Create a complete report shared with the test customer, return its ID."""
    global _test_report_id
    if _test_report_id:
        return _test_report_id

    sb = get_supabase_client()
    consultant_id = _get_user_id("consultant")
    customer_id = _get_user_id("customer")

    report_row = {
        "created_by": consultant_id,
        "customer_name": "Test Customer Farm",
        "operation_name": "Test Dairy Operation",
        "location_code": "EVANS",
        "product_ids": [],
        "findings": "Test findings for customer portal.",
        "recommendations": "Test recommendations for customer portal.",
        "rep_name": "Test Consultant",
        "rep_title": "Bower Ag Consultant",
        "include_pricing": False,
        "status": "complete",
        "report_content": "## Overview\n\nWe visited your operation and found everything in great shape.\n\n## Recommendations\n\nContinue current protocols.",
        "shared_with_customer": True,
        "shared_with_user_ids": [customer_id],
    }

    result = sb.table("reports").insert(report_row).execute()
    _test_report_id = result.data[0]["id"]
    return _test_report_id


# ─────────────────────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestCustomerReportsList:
    """Tests for GET /customer/reports."""

    def test_customer_list_reports_returns_shared(self):
        """GET /customer/reports as customer -> returns array with shared report."""
        report_id = _ensure_shared_report()

        response = client.get(
            "/customer/reports",
            headers=_auth_headers("customer"),
        )
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Find our test report
        report_ids = [r["report_id"] for r in data]
        assert report_id in report_ids

        # Verify no internal fields are exposed
        sample = data[0]
        assert "report_id" in sample
        assert "operation_name" in sample
        assert "rep_name" in sample
        assert "created_at" in sample
        assert "has_download" in sample
        # These should NOT be present
        assert "location_code" not in sample
        assert "shared_with_user_ids" not in sample
        assert "include_pricing" not in sample
        assert "shared_with_customer" not in sample

    def test_consultant_cannot_access_customer_endpoint(self):
        """GET /customer/reports as consultant -> 403."""
        response = client.get(
            "/customer/reports",
            headers=_auth_headers("consultant"),
        )
        assert response.status_code == 403


class TestCustomerReportDetail:
    """Tests for GET /customer/reports/{report_id}."""

    def test_customer_view_shared_report(self):
        """GET /customer/reports/{id} as customer -> returns report with content."""
        report_id = _ensure_shared_report()

        response = client.get(
            f"/customer/reports/{report_id}",
            headers=_auth_headers("customer"),
        )
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        data = response.json()

        assert data["report_id"] == report_id
        assert data["operation_name"] == "Test Dairy Operation"
        assert data["rep_name"] == "Test Consultant"
        assert data["rep_title"] == "Bower Ag Consultant"
        assert data["report_content"] is not None
        assert "Overview" in data["report_content"]
        assert data["created_at"] is not None

        # No internal fields
        assert "location_code" not in data
        assert "shared_with_user_ids" not in data
        assert "include_pricing" not in data
        assert "status" not in data

    def test_customer_cannot_view_unshared_report(self):
        """GET /customer/reports/{id} for report not shared with customer -> 403."""
        # Create a report NOT shared with the customer
        sb = get_supabase_client()
        consultant_id = _get_user_id("consultant")

        result = sb.table("reports").insert({
            "created_by": consultant_id,
            "customer_name": "Other Farm",
            "operation_name": "Private Report",
            "location_code": "JEROME",
            "product_ids": [],
            "findings": "Private findings.",
            "recommendations": "Private recs.",
            "rep_name": "Private Rep",
            "include_pricing": False,
            "status": "complete",
            "report_content": "Private content.",
            "shared_with_customer": False,
            "shared_with_user_ids": [],
        }).execute()
        private_report_id = result.data[0]["id"]

        response = client.get(
            f"/customer/reports/{private_report_id}",
            headers=_auth_headers("customer"),
        )
        assert response.status_code == 403

    def test_consultant_cannot_access_customer_report_detail(self):
        """GET /customer/reports/{id} as consultant -> 403."""
        report_id = _ensure_shared_report()

        response = client.get(
            f"/customer/reports/{report_id}",
            headers=_auth_headers("consultant"),
        )
        assert response.status_code == 403

    def test_customer_report_not_found(self):
        """GET /customer/reports/{nonexistent} as customer -> 404."""
        response = client.get(
            "/customer/reports/00000000-0000-0000-0000-000000000000",
            headers=_auth_headers("customer"),
        )
        assert response.status_code == 404
