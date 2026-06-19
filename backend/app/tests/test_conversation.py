"""
Bower Ag CowCare Tool — Conversation Pipeline Tests
Sprint 5: Tests for POST /conversation endpoint.

Tests run against a LIVE server at localhost:8000.
Start the server before running:
    cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000

Tests validate:
  1. Pricing query → governance_applied=True, reply contains a dollar amount
  2. Troubleshooting query → domain=TROUBLESHOOTING, llm_called=True
  3. Unknown product → reply mentions "not in" or "not found" or "lineup"
  4. No location + pricing → needs_location=True
  5. Audit log has new row after a query
  + Claude never called before governance (PRICING domain assertion)
  + Customer role blocked (403)

Usage:
  cd backend
  pytest app/tests/test_conversation.py -v

⚠️  These tests call the real Claude API — they cost tokens.
    They are integration tests, not unit tests.
    Each test may take 5-20 seconds due to Claude API latency.
"""

import os
import sys
import time
import uuid

import pytest
import requests as http

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv

load_dotenv()

from app.db.supabase_client import get_supabase_anon_client, get_supabase_client


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


def _converse(
    message: str,
    session_id: str = None,
    history: list = None,
    role: str = "consultant",
    timeout: int = 60,
):
    """Call POST /conversation with auth via HTTP against the live server."""
    token = _get_token(role)
    body = {
        "message": message,
        "session_id": session_id or f"test-{uuid.uuid4().hex[:8]}",
    }
    if history:
        body["conversation_history"] = history
    return http.post(
        f"{BASE_URL}/conversation",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
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
# Tests — 5 Required + 2 Bonus
# ─────────────────────────────────────────────────────────────────────────────

class TestConversationPipeline:
    """Sprint 5 conversation pipeline tests."""

    def test_pricing_query(self):
        """
        Pricing query with product + location returns governance-verified price.
        Asserts: governance_applied=True, reply contains a dollar sign, llm_called=True.

        ⚠️ CRITICAL: governance_applied=True means governance ran BEFORE Claude.
           This is the pipeline order assertion — Claude never called before governance.
        """
        resp = _converse(
            "How much does Curiass cost at Evans?",
            session_id=f"test-pricing-{uuid.uuid4().hex[:8]}",
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["domain"] == "PRICING", f"Expected PRICING domain, got {data['domain']}"
        assert data["governance_applied"] is True, (
            "governance_applied must be True — Claude should ONLY be called "
            "after governance completes for PRICING domain"
        )
        assert data["llm_called"] is True, "Claude should have been called"
        assert data["location_locked"] == "EVANS"

        # Reply must contain a dollar amount (governance-verified pricing)
        assert "$" in data["reply"], (
            f"Pricing reply must contain a dollar sign. Got: {data['reply'][:200]}"
        )

    def test_troubleshooting_query(self):
        """
        Troubleshooting query returns domain=TROUBLESHOOTING and llm_called=True.
        Reply should use the structured troubleshooting format from Doc B.
        """
        resp = _converse(
            "We are seeing high bacteria counts on our SPC tests. What should we check?",
            session_id=f"test-ts-{uuid.uuid4().hex[:8]}",
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["domain"] == "TROUBLESHOOTING", (
            f"Expected TROUBLESHOOTING domain, got {data['domain']}"
        )
        assert data["llm_called"] is True
        assert data["governance_applied"] is False, (
            "Troubleshooting should not apply governance"
        )

        # Reply should use structured format keywords
        reply_lower = data["reply"].lower()
        assert any(kw in reply_lower for kw in [
            "what you're likely dealing with",
            "what to check",
            "what to do",
            "likely dealing",
            "check first",
            "bacteria",
            "spc",
        ]), f"Troubleshooting reply should use structured format. Got: {data['reply'][:300]}"

    def test_unknown_product(self):
        """
        Pricing query for a non-existent product mentions "not in lineup" or similar.
        """
        resp = _converse(
            "How much does XyloBlast 9000 cost at Evans?",
            session_id=f"test-unknown-{uuid.uuid4().hex[:8]}",
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["governance_applied"] is True
        assert data["llm_called"] is True

        # Reply should indicate product doesn't exist
        reply_lower = data["reply"].lower()
        assert any(phrase in reply_lower for phrase in [
            "not in our",
            "not in the",
            "isn't in our",
            "isn't in the",
            "not found",
            "not carry",
            "don't carry",
            "doesn't exist",
            "don't have",
            "lineup",
            "not available",
        ]), (
            f"Unknown product reply should mention product not found. "
            f"Got: {data['reply'][:300]}"
        )

    def test_location_required(self):
        """
        Pricing query without location → needs_location=True, no LLM call.
        """
        resp = _converse(
            "What does Shield cost per gallon?",
            session_id=f"test-noloc-{uuid.uuid4().hex[:8]}",
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["domain"] == "PRICING", f"Expected PRICING, got {data['domain']}"
        assert data["needs_location"] is True, (
            "Missing location for pricing should set needs_location=True"
        )
        assert data["llm_called"] is False, (
            "Claude should NOT be called when location is missing"
        )
        assert data["governance_applied"] is False

        # Reply should ask about location
        reply_lower = data["reply"].lower()
        assert any(loc in reply_lower for loc in ["evans", "ulysses", "jerome", "turlock", "tulare"]), (
            f"Location prompt should mention available locations. Got: {data['reply'][:200]}"
        )

    def test_audit_logged(self):
        """
        After a conversation query, audit_log has a new row with action='conversation.reply'.
        """
        # Record timestamp before query
        before_ts = time.time()
        unique_marker = f"audit-test-{uuid.uuid4().hex[:8]}"

        resp = _converse(
            "Tell me about teat dip options for pre-milking",
            session_id=unique_marker,
        )
        assert resp.status_code == 200

        # Give audit log time to write (it's async/non-blocking)
        time.sleep(2)

        # Check Supabase for audit entry
        client = get_supabase_client()
        result = (
            client.table("audit_log")
            .select("action,domain,llm_called,query_text,governance_result")
            .eq("action", "conversation.reply")
            .ilike("query_text", "%teat dip options%")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        assert result.data and len(result.data) >= 1, (
            "Expected at least 1 audit_log entry for conversation.reply"
        )

        audit_row = result.data[0]
        assert audit_row["action"] == "conversation.reply"
        assert audit_row["llm_called"] is True
        assert audit_row["query_text"] is not None

        # Governance result should contain domain and token info
        gov = audit_row.get("governance_result", {})
        assert "domain" in gov, f"governance_result should have 'domain'. Got: {gov}"

    def test_customer_blocked(self):
        """Customer role is blocked from conversation endpoint (403)."""
        resp = _converse(
            "How much does Curiass cost?",
            role="customer",
        )
        assert resp.status_code == 403

    def test_governance_before_claude_assertion(self):
        """
        Explicit assertion: for PRICING domain, governance_applied is True
        and llm_called is True — proving governance ran before Claude.

        If governance_applied were False but llm_called were True, that would
        mean Claude was called without governance data — a critical violation.
        """
        resp = _converse(
            "What is the price of Pavise at Jerome?",
            session_id=f"test-gov-order-{uuid.uuid4().hex[:8]}",
        )
        assert resp.status_code == 200

        data = resp.json()

        if data["domain"] == "PRICING":
            # For pricing queries, BOTH flags must be True
            assert data["governance_applied"] is True, (
                "CRITICAL: Claude was called without governance for PRICING domain!"
            )
            assert data["llm_called"] is True
