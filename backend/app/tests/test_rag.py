"""
Bower Ag CowCare Tool — RAG Advisory Endpoint Tests
Sprint 4: Tests for the advisory search endpoint.

Tests run against a LIVE server at localhost:8000.
Start the server before running:
    cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000

Tests validate:
  1. Bacteria/troubleshooting queries return troubleshooting domain results
  2. SDS/safety queries return sds domain results
  3. CIP flow/procedure queries return procedure domain results
  4. Irrelevant queries return empty results (below 0.70 threshold)
  + Customer blocked, no-auth blocked, invalid domain, domain filter

Usage:
  cd backend
  pytest app/tests/test_rag.py -v
"""

import os
import sys

import pytest
import requests as http

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv

load_dotenv()

from app.db.supabase_client import get_supabase_anon_client


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL = "http://localhost:8000"

TEST_USERS = {
    "consultant": {"email": "consultant@bowerag.test", "password": "TestConsult123!"},
    "customer": {"email": "customer@bowerag.test", "password": "TestCustomer123!"},
}

_token_cache: dict[str, str] = {}


def _get_token(role: str) -> str:
    """Sign in and cache JWT token per role."""
    if role in _token_cache:
        return _token_cache[role]

    anon = get_supabase_anon_client()
    creds = TEST_USERS[role]
    result = anon.auth.sign_in_with_password({
        "email": creds["email"],
        "password": creds["password"],
    })
    token = result.session.access_token
    _token_cache[role] = token
    return token


def _search(query: str, domain: str = None, limit: int = 5, role: str = "consultant"):
    """Call GET /advisory/search with auth via HTTP against the live server."""
    token = _get_token(role)
    params = {"q": query, "limit": limit}
    if domain:
        params["domain"] = domain
    return http.get(
        f"{BASE_URL}/advisory/search",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pre-flight: ensure server is running
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True, scope="session")
def _check_server():
    """Verify the backend server is running before tests."""
    try:
        r = http.get(f"{BASE_URL}/health", timeout=5)
        assert r.status_code == 200
    except http.ConnectionError:
        pytest.skip(
            "Backend server not running at localhost:8000. "
            "Start with: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Tests — 4 Required + 4 Bonus
# ─────────────────────────────────────────────────────────────────────────────

class TestRAGAdvisorySearch:
    """Sprint 4 RAG endpoint tests."""

    def test_bacteria_query(self):
        """Bacteria/SPC query returns troubleshooting domain results."""
        resp = _search("high bacteria count troubleshooting dairy SPC")
        assert resp.status_code == 200

        data = resp.json()
        assert data["count"] >= 1, "Expected at least 1 result for bacteria query"
        assert data["source"] == "advisory_rag"

        # At least one result in troubleshooting domain
        domains = [r["domain"] for r in data["results"]]
        assert "troubleshooting" in domains, (
            f"Expected 'troubleshooting' in domains, got: {domains}"
        )

        # Verify structure
        first = data["results"][0]
        assert "section_title" in first
        assert "content" in first
        assert "source_doc" in first
        assert "similarity_score" in first
        assert first["similarity_score"] >= 0.70

    def test_sds_query(self):
        """SDS/safety query returns sds domain results."""
        resp = _search("safety data sheet chemical handling PPE requirements dairy")
        assert resp.status_code == 200

        data = resp.json()
        assert data["count"] >= 1, "Expected at least 1 result for SDS query"

        domains = [r["domain"] for r in data["results"]]
        assert "sds" in domains, (
            f"Expected 'sds' in domains, got: {domains}"
        )

        for r in data["results"]:
            assert r["similarity_score"] >= 0.70

    def test_cip_flow_query(self):
        """CIP procedure query returns procedure domain results."""
        resp = _search("CIP alkaline wash procedure clean in place dairy milking system")
        assert resp.status_code == 200

        data = resp.json()
        assert data["count"] >= 1, "Expected at least 1 result for CIP query"

        domains = [r["domain"] for r in data["results"]]
        assert "procedure" in domains, (
            f"Expected 'procedure' in domains, got: {domains}"
        )

    def test_irrelevant_query(self):
        """'capital of France' returns 0 results (below 0.70 threshold)."""
        resp = _search("capital of France")
        assert resp.status_code == 200

        data = resp.json()
        assert data["count"] == 0, (
            f"Expected 0 results for irrelevant query, got {data['count']}. "
            f"Titles: {[r['section_title'] for r in data['results']]}"
        )
        assert data["results"] == []

    def test_domain_filter(self):
        """Domain filter restricts results to the specified domain only."""
        resp = _search(
            "dairy chemical product teat dip specifications",
            domain="product_info",
        )
        assert resp.status_code == 200

        data = resp.json()
        for r in data["results"]:
            assert r["domain"] == "product_info", (
                f"Expected domain 'product_info' but got '{r['domain']}'"
            )

    def test_customer_blocked(self):
        """Customer role is blocked from advisory search (403)."""
        resp = _search("bacteria troubleshooting", role="customer")
        assert resp.status_code == 403

    def test_no_auth_blocked(self):
        """Unauthenticated request returns 401."""
        resp = http.get(
            f"{BASE_URL}/advisory/search",
            params={"q": "test query"},
            timeout=10,
        )
        assert resp.status_code == 401

    def test_invalid_domain(self):
        """Invalid domain parameter returns 400."""
        resp = _search("test query", domain="invalid_domain")
        assert resp.status_code == 400
        assert "Invalid domain" in resp.json()["detail"]
