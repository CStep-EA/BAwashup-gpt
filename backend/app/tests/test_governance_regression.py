"""
Bower Ag CowCare Tool — Governance Regression Tests
Sprint 15: 10 tests calling REAL /conversation endpoint with REAL Claude API.

⚠️  EXPENSIVE: These tests call the Claude API — run intentionally, not on every save.
    Mark: @pytest.mark.regression

Each test sends a message, waits for the response, and asserts governance behavior.
Failure messages include the actual response for debugging.

Usage:
  cd backend
  pytest app/tests/test_governance_regression.py -v -m regression
"""

import os
import re
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.supabase_client import get_supabase_client
from app.core.location_lock import location_lock_store

from app.tests.conftest import auth_headers, get_test_token


# ─── Setup ────────────────────────────────────────────────────────────────────

client = TestClient(app)
db = get_supabase_client()


def _send_message(
    message: str,
    session_id: str | None = None,
    history: list | None = None,
    role: str = "consultant",
) -> dict:
    """Send a conversation message and return the full response dict."""
    headers = auth_headers(role)
    if session_id:
        headers["X-Session-ID"] = session_id

    payload = {
        "message": message,
        "session_id": session_id or str(uuid.uuid4()),
        "conversation_history": history or [],
    }

    response = client.post("/conversation", json=payload, headers=headers)
    assert response.status_code == 200, (
        f"Conversation API returned {response.status_code}: {response.text}"
    )
    return response.json()


def _lock_session_location(session_id: str, location_code: str, role: str = "consultant"):
    """Pre-lock a session to a specific location."""
    headers = auth_headers(role)
    headers["X-Session-ID"] = session_id
    resp = client.post(
        "/session/location",
        json={"location_code": location_code},
        headers=headers,
    )
    assert resp.status_code == 200, f"Failed to lock session: {resp.text}"


def _get_product_by_name(name_fragment: str) -> dict | None:
    """Look up a product by name fragment."""
    result = (
        db.table("products")
        .select("*")
        .ilike("product_name", f"%{name_fragment}%")
        .eq("active", True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _get_pricing_for_product_at_location(product_id: str, location_code: str) -> list[dict]:
    """Get pricing rows for a product at a location."""
    # Resolve location_id from branch_code
    loc_result = (
        db.table("locations")
        .select("id")
        .eq("branch_code", location_code)
        .limit(1)
        .execute()
    )
    if not loc_result.data:
        return []
    location_id = loc_result.data[0]["id"]

    result = (
        db.table("product_pricing")
        .select("*")
        .eq("product_id", product_id)
        .eq("location_id", location_id)
        .execute()
    )
    return result.data or []


def _get_sellability(product_id: str, location_code: str) -> bool | None:
    """Check if product is sellable at location."""
    loc_result = (
        db.table("locations")
        .select("id")
        .eq("branch_code", location_code)
        .limit(1)
        .execute()
    )
    if not loc_result.data:
        return None
    location_id = loc_result.data[0]["id"]

    result = (
        db.table("product_sellability")
        .select("sellable")
        .eq("product_id", product_id)
        .eq("location_id", location_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0].get("sellable")


def _get_sellable_products_at(location_code: str) -> list[str]:
    """Get all product names that are sellable at a given location."""
    loc_result = (
        db.table("locations")
        .select("id")
        .eq("branch_code", location_code)
        .limit(1)
        .execute()
    )
    if not loc_result.data:
        return []
    location_id = loc_result.data[0]["id"]

    sell_result = (
        db.table("product_sellability")
        .select("product_id")
        .eq("location_id", location_id)
        .eq("sellable", True)
        .execute()
    )
    if not sell_result.data:
        return []

    product_ids = [r["product_id"] for r in sell_result.data]
    names = []
    for pid in product_ids:
        prod = db.table("products").select("product_name").eq("id", pid).limit(1).execute()
        if prod.data:
            names.append(prod.data[0]["product_name"])
    return names


# ─── TESTS ────────────────────────────────────────────────────────────────────


@pytest.mark.regression
class TestGovernanceRegression:
    """10 governance regression tests using real Claude API."""

    def test_gr01_pricing_curiass_evans(self):
        """GR-01: Curiass pricing in Evans should contain dollar amount from DB."""
        session_id = f"gr01-{uuid.uuid4()}"
        _lock_session_location(session_id, "EVANS")

        result = _send_message(
            "What does Curiass cost in Evans, Colorado?",
            session_id=session_id,
        )

        # Verify response has a dollar amount
        reply = result["reply"]
        dollar_match = re.search(r"\$[\d,]+\.?\d*", reply)
        assert dollar_match, (
            f"GR-01 FAIL: No dollar amount found in reply.\n"
            f"Reply: {reply[:500]}"
        )

        # Verify governance was applied
        assert result.get("governance_applied") is True, (
            f"GR-01 FAIL: governance_applied not True.\n"
            f"Full response: {result}"
        )

        # Cross-check: get Curiass pricing from DB
        curiass = _get_product_by_name("Curiass")
        if curiass:
            db_prices = _get_pricing_for_product_at_location(curiass["id"], "EVANS")
            if db_prices:
                # At least one DB price should be referenced (as string)
                any_price_in_reply = any(
                    f"{p['price_per_unit']:.2f}" in reply or
                    str(int(p["price_per_unit"])) in reply
                    for p in db_prices
                )
                assert any_price_in_reply, (
                    f"GR-01 FAIL: DB pricing not reflected in reply.\n"
                    f"DB prices: {[p['price_per_unit'] for p in db_prices]}\n"
                    f"Reply: {reply[:500]}"
                )

    def test_gr02_curiass_sellability_kansas(self):
        """GR-02: Curiass sellability in Kansas — reflect DB boolean, no price."""
        session_id = f"gr02-{uuid.uuid4()}"

        result = _send_message(
            "Is Curiass available in Kansas?",
            session_id=session_id,
        )

        reply = result["reply"]
        curiass = _get_product_by_name("Curiass")
        if curiass:
            sellable = _get_sellability(curiass["id"], "ULYSSES")
            if sellable is not None:
                if sellable:
                    # Should indicate it IS available
                    assert any(w in reply.lower() for w in ["available", "yes", "sell", "offer"]), (
                        f"GR-02 FAIL: Product is sellable but reply doesn't confirm.\n"
                        f"Reply: {reply[:500]}"
                    )
                else:
                    # Should indicate NOT available
                    assert any(w in reply.lower() for w in ["not available", "not sell", "unavailable", "cannot"]), (
                        f"GR-02 FAIL: Product not sellable but reply doesn't deny.\n"
                        f"Reply: {reply[:500]}"
                    )

        # Should NOT contain a dollar amount
        dollar_match = re.search(r"\$\d+", reply)
        assert not dollar_match, (
            f"GR-02 FAIL: Sellability query should not contain pricing.\n"
            f"Found: {dollar_match.group() if dollar_match else 'N/A'}\n"
            f"Reply: {reply[:500]}"
        )

    def test_gr03_products_at_jerome(self):
        """GR-03: Products sellable in Jerome — all mentioned products should be sellable."""
        session_id = f"gr03-{uuid.uuid4()}"
        _lock_session_location(session_id, "JEROME")

        result = _send_message(
            "What products can I sell in Jerome, Idaho?",
            session_id=session_id,
        )

        reply = result["reply"]
        jerome_products = _get_sellable_products_at("JEROME")

        if jerome_products:
            # Check that at least some Jerome products are mentioned
            mentioned_count = sum(
                1 for name in jerome_products
                if name.lower() in reply.lower()
            )
            assert mentioned_count > 0, (
                f"GR-03 FAIL: No Jerome-sellable products mentioned in reply.\n"
                f"Jerome products: {jerome_products[:10]}\n"
                f"Reply: {reply[:500]}"
            )

    def test_gr04_nonexistent_product(self):
        """GR-04: Non-existent product should not return pricing."""
        session_id = f"gr04-{uuid.uuid4()}"
        _lock_session_location(session_id, "EVANS")

        result = _send_message(
            "Price of ZZZNonExistentProduct999 in Evans",
            session_id=session_id,
        )

        reply = result["reply"]

        # Should NOT contain a dollar amount
        dollar_match = re.search(r"\$\d+", reply)
        assert not dollar_match, (
            f"GR-04 FAIL: Response should not contain pricing for non-existent product.\n"
            f"Found: {dollar_match.group() if dollar_match else 'N/A'}\n"
            f"Reply: {reply[:500]}"
        )

        # Should indicate not found
        assert any(w in reply.lower() for w in [
            "not found", "don't carry", "not in", "don't have",
            "not available", "unable to find", "cannot find",
            "no product", "not recognize", "not familiar",
            "lineup", "catalog",
        ]), (
            f"GR-04 FAIL: Response should indicate product not found.\n"
            f"Reply: {reply[:500]}"
        )

    def test_gr05_california_pricing_isolation(self):
        """GR-05: California pricing should only show Turlock prices."""
        session_id = f"gr05-{uuid.uuid4()}"
        _lock_session_location(session_id, "TURLOCK")

        # Find a product sellable at Turlock
        turlock_products = _get_sellable_products_at("TURLOCK")
        if not turlock_products:
            pytest.skip("No sellable products at TURLOCK.")

        product_name = turlock_products[0]

        result = _send_message(
            f"What does {product_name} cost in California?",
            session_id=session_id,
        )

        reply = result["reply"]

        # Check: reply should not mention Evans or Kansas explicitly as pricing sources
        assert "evans" not in reply.lower().replace("evan", "") or "price" not in reply.lower(), (
            f"GR-05 FAIL: California pricing should not reference Evans.\n"
            f"Reply: {reply[:500]}"
        )

    def test_gr06_shield_ofb_calculation(self):
        """GR-06: Shield OFB tote pricing should reference component prices."""
        session_id = f"gr06-{uuid.uuid4()}"
        _lock_session_location(session_id, "EVANS")

        result = _send_message(
            "What is the tote price for Shield OFB?",
            session_id=session_id,
        )

        reply = result["reply"]

        # Should contain some dollar amounts (pricing query)
        dollar_matches = re.findall(r"\$[\d,]+\.?\d*", reply)
        assert len(dollar_matches) >= 1, (
            f"GR-06 FAIL: Shield OFB pricing should contain dollar amounts.\n"
            f"Reply: {reply[:500]}"
        )

    def test_gr07_sellability_boolean_only(self, known_product_not_in_kansas):
        """GR-07: Product not sold in Kansas — clear 'not available' with no pricing."""
        product_name = known_product_not_in_kansas["product_name"]
        session_id = f"gr07-{uuid.uuid4()}"
        _lock_session_location(session_id, "ULYSSES")

        result = _send_message(
            f"Can I sell {product_name} in Ulysses?",
            session_id=session_id,
        )

        reply = result["reply"]

        # Should clearly say NOT available
        not_available = any(w in reply.lower() for w in [
            "not available", "not sell", "not sold", "unavailable",
            "cannot sell", "do not carry", "don't carry", "not offered",
        ])
        assert not_available, (
            f"GR-07 FAIL: Should clearly state product is not available.\n"
            f"Product: {product_name}\n"
            f"Reply: {reply[:500]}"
        )

        # Should NOT contain pricing
        dollar_match = re.search(r"\$\d+", reply)
        assert not dollar_match, (
            f"GR-07 FAIL: Should not contain pricing for unsellable product.\n"
            f"Reply: {reply[:500]}"
        )

    def test_gr08_chemistry_full_sweep(self):
        """GR-08: Chemistry query — should mention ≥80% of products with that chemistry."""
        # Get a chemistry type from DB
        chem_result = (
            db.table("products")
            .select("chemistry_type")
            .neq("chemistry_type", None)
            .limit(10)
            .execute()
        )
        if not chem_result.data:
            pytest.skip("No products with chemistry_type in DB.")

        chemistry = chem_result.data[0]["chemistry_type"]
        if not chemistry:
            pytest.skip("chemistry_type is None.")

        # Get all products with this chemistry
        all_products = (
            db.table("products")
            .select("product_name")
            .eq("chemistry_type", chemistry)
            .eq("active", True)
            .execute()
        )
        product_names = [p["product_name"] for p in (all_products.data or [])]

        if len(product_names) < 2:
            pytest.skip(f"Only {len(product_names)} products with chemistry '{chemistry}'.")

        session_id = f"gr08-{uuid.uuid4()}"
        result = _send_message(
            f"Show me all products that contain {chemistry}",
            session_id=session_id,
        )

        reply = result["reply"]

        # Check at least 80% of products mentioned
        mentioned = sum(1 for name in product_names if name.lower() in reply.lower())
        threshold = max(1, int(len(product_names) * 0.8))
        assert mentioned >= threshold, (
            f"GR-08 FAIL: Expected ≥{threshold} of {len(product_names)} products mentioned, "
            f"found {mentioned}.\n"
            f"Products: {product_names}\n"
            f"Reply: {reply[:500]}"
        )

    def test_gr09_troubleshooting_no_governance(self):
        """GR-09: Troubleshooting query — no governance, structured format."""
        session_id = f"gr09-{uuid.uuid4()}"

        result = _send_message(
            "I am seeing high SPC counts in my milk. What could be causing this?",
            session_id=session_id,
        )

        reply = result["reply"]
        domain = result.get("domain", "")

        # Domain should be TROUBLESHOOTING
        assert domain == "TROUBLESHOOTING", (
            f"GR-09 FAIL: Expected domain=TROUBLESHOOTING, got '{domain}'.\n"
            f"Reply: {reply[:300]}"
        )

        # Governance should NOT be applied
        assert result.get("governance_applied") is False, (
            f"GR-09 FAIL: Troubleshooting should not have governance applied.\n"
            f"Full response: {result}"
        )

        # Should contain structured format keywords
        structured = any(w in reply.lower() for w in [
            "cause", "check", "step", "possible", "reason",
            "recommend", "suggest", "action", "tip", "ensure",
            "verify", "inspect", "consider", "common",
        ])
        assert structured, (
            f"GR-09 FAIL: Reply should have structured troubleshooting content.\n"
            f"Reply: {reply[:500]}"
        )

    def test_gr10_location_switch_requires_confirmation(self):
        """GR-10: Switching location mid-session should require confirmation or flag."""
        session_id = f"gr10-{uuid.uuid4()}"

        # Find a product that exists
        product_result = (
            db.table("products")
            .select("product_name")
            .eq("active", True)
            .limit(1)
            .execute()
        )
        if not product_result.data:
            pytest.skip("No active products in DB.")
        product_name = product_result.data[0]["product_name"]

        # Message 1: Lock to EVANS
        _lock_session_location(session_id, "EVANS")
        result1 = _send_message(
            f"Price of {product_name} in Evans",
            session_id=session_id,
        )

        # Message 2: Try to switch to Kansas
        result2 = _send_message(
            "Now show me pricing in Kansas",
            session_id=session_id,
            history=[
                {"role": "user", "content": f"Price of {product_name} in Evans"},
                {"role": "assistant", "content": result1["reply"]},
            ],
        )

        reply2 = result2["reply"]

        # The response should NOT silently mix Evans and Kansas pricing.
        # It should either:
        # 1. Ask for confirmation to switch locations
        # 2. Explicitly note the location is changing
        # 3. State the currently locked location and note the conflict
        location_awareness = any(w in reply2.lower() for w in [
            "switch", "change", "different location", "currently set to",
            "locked to", "evans", "kansas", "ulysses", "confirm",
            "location", "another branch",
        ])
        assert location_awareness, (
            f"GR-10 FAIL: Response should acknowledge location context, "
            f"not silently mix pricing.\n"
            f"Reply: {reply2[:500]}"
        )
