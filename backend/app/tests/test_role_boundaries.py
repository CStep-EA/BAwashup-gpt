"""
Bower Ag CowCare Tool — Role Boundary Tests
Sprint 15, Step 3: Parametrized matrix of 14 endpoints × 4 roles.

Verifies that every API endpoint enforces its role guard correctly:
  - Allowed roles receive 2xx or domain-specific responses (not 401/403)
  - Denied roles receive exactly 403 Forbidden

Roles tested:
  org_admin, admin_manager, consultant, customer

These tests hit real Supabase auth to validate the full auth pipeline.
They send minimal payloads — just enough to pass validation and reach the
role guard. Some "allowed" tests may return 4xx for business reasons
(e.g., 400 bad input, 404 not found), but they MUST NOT return 403.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

import pytest
from fastapi.testclient import TestClient
from app.main import app

# Import convenience helpers from conftest
from app.tests.conftest import auth_headers


# ─── Test Client ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient for role boundary tests."""
    return TestClient(app)


# ─── Role Access Matrix ──────────────────────────────────────────────────────
#
# Each entry: (endpoint_label, method, path, body_or_params, allowed_roles)
#
# allowed_roles: set of role strings that should NOT get 403.
# All other roles from {org_admin, admin_manager, consultant, customer}
# should receive 403.
#
# body_or_params: dict sent as JSON body (POST/PATCH) or query params (GET/DELETE).
# Minimal payloads — just enough to pass Pydantic validation.
# ─────────────────────────────────────────────────────────────────────────────

NON_CUSTOMER = {"org_admin", "admin_manager", "consultant"}
ADMIN_ONLY = {"org_admin", "admin_manager"}
ORG_ADMIN_ONLY = {"org_admin"}
REPORT_ROLES = {"consultant", "org_admin", "admin_manager"}  # account_manager not tested
CUSTOMER_ONLY = {"customer"}
ALL_ROLES = {"org_admin", "admin_manager", "consultant", "customer"}

ENDPOINTS = [
    # ── 1. POST /conversation — NON_CUSTOMER_ROLES ───────────────────────────
    (
        "POST /conversation",
        "post",
        "/conversation",
        {"message": "What is Curiass pricing?", "session_id": "role-test"},
        NON_CUSTOMER,
    ),
    # ── 2. GET /products — NON_CUSTOMER_ROLES ────────────────────────────────
    (
        "GET /products",
        "get",
        "/products",
        {},
        NON_CUSTOMER,
    ),
    # ── 3. POST /session/location — NON_CUSTOMER_ROLES ──────────────────────
    (
        "POST /session/location",
        "post",
        "/session/location",
        {"location_code": "EVANS", "force": True},
        NON_CUSTOMER,
    ),
    # ── 4. POST /feedback — NON_CUSTOMER_ROLES ──────────────────────────────
    (
        "POST /feedback",
        "post",
        "/feedback",
        {"rating": 1, "comment": "Role boundary test"},
        NON_CUSTOMER,
    ),
    # ── 5. POST /bugs — VALID_ROLES (all) ───────────────────────────────────
    (
        "POST /bugs",
        "post",
        "/bugs",
        {
            "title": "Role boundary test bug",
            "what_happened": "Testing role boundaries for bug report endpoint",
            "severity": "low",
        },
        ALL_ROLES,
    ),
    # ── 6. GET /advisory/search — NON_CUSTOMER_ROLES ────────────────────────
    (
        "GET /advisory/search",
        "get",
        "/advisory/search",
        {"q": "mastitis", "limit": "1"},
        NON_CUSTOMER,
    ),
    # ── 7. POST /reports/generate — REPORT_ROLES ────────────────────────────
    (
        "POST /reports/generate",
        "post",
        "/reports/generate",
        {
            "title": "Role Boundary Test Report",
            "conversation_ids": [],
            "location_code": "EVANS",
        },
        REPORT_ROLES,
    ),
    # ── 8. GET /customer/reports — customer ONLY ─────────────────────────────
    (
        "GET /customer/reports",
        "get",
        "/customer/reports",
        {},
        CUSTOMER_ONLY,
    ),
    # ── 9. GET /admin/analytics/summary — ADMIN_ROLES ───────────────────────
    (
        "GET /admin/analytics/summary",
        "get",
        "/admin/analytics/summary",
        {},
        ADMIN_ONLY,
    ),
    # ── 10. PATCH /admin/config/{key} — ADMIN_ROLES ─────────────────────────
    (
        "PATCH /admin/config/{key}",
        "patch",
        "/admin/config/feature.video_upload",
        {"value": "true"},
        ADMIN_ONLY,
    ),
    # ── 11. POST /admin/users/invite — ADMIN_ROLES ──────────────────────────
    (
        "POST /admin/users/invite",
        "post",
        "/admin/users/invite",
        {
            "email": "role-boundary-test@bowerag.test",
            "role": "consultant",
            "full_name": "Role Boundary Test",
        },
        ADMIN_ONLY,
    ),
    # ── 12. GET /admin/audit — org_admin ONLY ───────────────────────────────
    (
        "GET /admin/audit",
        "get",
        "/admin/audit",
        {"limit": "1"},
        ORG_ADMIN_ONLY,
    ),
    # ── 13. POST /admin/versions — org_admin ONLY ───────────────────────────
    (
        "POST /admin/versions",
        "post",
        "/admin/versions",
        {
            "version": "0.0.0-role-test",
            "summary": "Role boundary test — should not persist",
        },
        ORG_ADMIN_ONLY,
    ),
    # ── 14. GET /governance/health — ADMIN_ROLES ────────────────────────────
    (
        "GET /governance/health",
        "get",
        "/governance/health",
        {},
        ADMIN_ONLY,
    ),
]

ALL_TEST_ROLES = ["org_admin", "admin_manager", "consultant", "customer"]


# ─── Generate test IDs for readability ───────────────────────────────────────

def _test_id(endpoint_label: str, role: str, allowed_roles: set) -> str:
    """Generate a human-readable test ID like 'POST_conversation__consultant__ALLOW'."""
    safe_label = endpoint_label.replace(" ", "_").replace("/", "_").replace("{", "").replace("}", "")
    verdict = "ALLOW" if role in allowed_roles else "DENY"
    return f"{safe_label}__{role}__{verdict}"


# Build parametrize list: (endpoint_label, method, path, body, role, should_allow)
_params = []
_ids = []
for (label, method, path, body, allowed) in ENDPOINTS:
    for role in ALL_TEST_ROLES:
        should_allow = role in allowed
        _params.append((label, method, path, body, role, should_allow))
        _ids.append(_test_id(label, role, allowed))


# ─── The Parametrized Test ───────────────────────────────────────────────────

class TestRoleBoundaries:
    """
    Parametrized role boundary matrix.
    14 endpoints × 4 roles = 56 test cases.
    """

    @pytest.mark.parametrize(
        "label, method, path, body, role, should_allow",
        _params,
        ids=_ids,
    )
    def test_role_access(
        self,
        client: TestClient,
        label: str,
        method: str,
        path: str,
        body: dict,
        role: str,
        should_allow: bool,
    ):
        """
        For each (endpoint, role) pair:
          - If should_allow: status code must NOT be 403
          - If should NOT allow: status code must be exactly 403
        """
        headers = auth_headers(role)

        # Dispatch by HTTP method
        if method == "get":
            resp = client.get(path, params=body, headers=headers)
        elif method == "post":
            resp = client.post(path, json=body, headers=headers)
        elif method == "patch":
            resp = client.patch(path, json=body, headers=headers)
        elif method == "delete":
            resp = client.delete(path, params=body, headers=headers)
        else:
            pytest.fail(f"Unknown method: {method}")

        if should_allow:
            # Allowed role: we should NOT get 403 (or 401).
            # We may get other 4xx for business logic (400, 404, 409, 422),
            # or 2xx — all acceptable. Only 403 is a failure.
            assert resp.status_code != 403, (
                f"ROLE BOUNDARY VIOLATION: {role} should be ALLOWED on {label} "
                f"but got 403. Response: {resp.text[:300]}"
            )
            assert resp.status_code != 401, (
                f"AUTH FAILURE: {role} got 401 on {label}. "
                f"Token may be expired. Response: {resp.text[:200]}"
            )
        else:
            # Denied role: must get exactly 403.
            assert resp.status_code == 403, (
                f"ROLE BOUNDARY VIOLATION: {role} should be DENIED on {label} "
                f"but got {resp.status_code}. Response: {resp.text[:300]}"
            )


# ─── Standalone Targeted Tests ───────────────────────────────────────────────
# These provide extra assertions beyond the matrix for critical boundaries.

class TestCriticalBoundaries:
    """
    Targeted tests for the most security-sensitive role boundaries.
    These verify specific response details, not just status codes.
    """

    def test_customer_cannot_see_products(self, client):
        """Customer must not access internal product catalog."""
        headers = auth_headers("customer")
        resp = client.get("/products", headers=headers)
        assert resp.status_code == 403
        assert "customer" in resp.json()["detail"].lower() or "permission" in resp.json()["detail"].lower()

    def test_customer_cannot_use_conversation(self, client):
        """Customer must not access the conversation/chat engine."""
        headers = auth_headers("customer")
        resp = client.post(
            "/conversation",
            json={"message": "Should be blocked"},
            headers=headers,
        )
        assert resp.status_code == 403

    def test_consultant_cannot_access_audit(self, client):
        """Consultant must not see audit logs (org_admin only)."""
        headers = auth_headers("consultant")
        resp = client.get("/admin/audit", headers=headers)
        assert resp.status_code == 403

    def test_admin_manager_cannot_access_audit(self, client):
        """Admin manager must not see audit logs (org_admin only)."""
        headers = auth_headers("admin_manager")
        resp = client.get("/admin/audit", headers=headers)
        assert resp.status_code == 403

    def test_consultant_cannot_manage_users(self, client):
        """Consultant must not invite users (ADMIN_ROLES only)."""
        headers = auth_headers("consultant")
        resp = client.post(
            "/admin/users/invite",
            json={
                "email": "block-test@bowerag.test",
                "role": "consultant",
                "full_name": "Blocked Invite",
            },
            headers=headers,
        )
        assert resp.status_code == 403

    def test_consultant_cannot_modify_config(self, client):
        """Consultant must not change system config (ADMIN_ROLES only)."""
        headers = auth_headers("consultant")
        resp = client.patch(
            "/admin/config/feature.video_upload",
            json={"value": "false"},
            headers=headers,
        )
        assert resp.status_code == 403

    def test_non_customer_cannot_access_customer_portal(self, client):
        """Non-customer roles must not access customer report portal."""
        for role in ["org_admin", "admin_manager", "consultant"]:
            headers = auth_headers(role)
            resp = client.get("/customer/reports", headers=headers)
            assert resp.status_code == 403, (
                f"{role} should be DENIED from /customer/reports but got {resp.status_code}"
            )

    def test_403_response_structure(self, client):
        """All 403 responses should have consistent detail message."""
        headers = auth_headers("customer")
        resp = client.get("/products", headers=headers)
        assert resp.status_code == 403
        data = resp.json()
        assert "detail" in data
        assert "permission" in data["detail"].lower() or "access denied" in data["detail"].lower()

    def test_unauthenticated_gets_401(self, client):
        """No token at all should return 401, not 403."""
        resp = client.get("/products")
        assert resp.status_code == 401
        assert "Authorization" in resp.text or "authorization" in resp.text.lower()
