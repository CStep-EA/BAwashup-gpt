"""
Bower Ag CowCare Tool — Governance Endpoint Tests
Sprint 3: 8 required tests from Document A Section 11.2 + no-LLM assertion.

These tests run against the LIVE Supabase instance with real JWT tokens.
Test users are created in Supabase auth with specific roles.

Usage:
  cd backend
  pytest app/tests/test_governance.py -v
"""

import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv

load_dotenv()

from fastapi.testclient import TestClient

from app.main import app
from app.db.supabase_client import get_supabase_client, get_supabase_anon_client
from app.core.location_lock import location_lock_store


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

client = TestClient(app)

# Test user credentials (created during Sprint 3 setup)
TEST_USERS = {
    "org_admin": {"email": "admin@bowerag.test", "password": "TestAdmin123!"},
    "consultant": {"email": "consultant@bowerag.test", "password": "TestConsult123!"},
    "customer": {"email": "customer@bowerag.test", "password": "TestCustomer123!"},
}


# Token cache to avoid re-signing-in for every test
_token_cache: dict[str, str] = {}


def _get_token(role: str) -> str:
    """Sign in a test user and return the JWT access token.
    Cached per role to avoid excessive sign-in calls."""
    if role in _token_cache:
        return _token_cache[role]

    anon = get_supabase_anon_client()
    creds = TEST_USERS[role]
    result = anon.auth.sign_in_with_password({
        "email": creds["email"],
        "password": creds["password"],
    })
    token = result.session.access_token
    # Do NOT sign out — that revokes the token
    _token_cache[role] = token
    return token


def _auth_header(role: str) -> dict:
    """Return Authorization header for a role."""
    return {"Authorization": f"Bearer {_get_token(role)}"}


# ─────────────────────────────────────────────────────────────────────────────
# Test Data (from Sprint 2 migration)
# ─────────────────────────────────────────────────────────────────────────────

# Known product: Curiass (A/B) — teat_dip, sellable at all locations
CURIASS_NAME = "Curiass"

# Known product IDs (will be looked up dynamically)
_curiass_id = None
_es_chlorinated_id = None


def _get_curiass_id() -> str:
    """Get the Curiass product ID from DB."""
    global _curiass_id
    if _curiass_id is None:
        db = get_supabase_client()
        result = db.table("products").select("id").ilike("product_name", "%Curiass%").execute()
        assert result.data, "Curiass not found in products table — run Sprint 2 migrations first"
        _curiass_id = result.data[0]["id"]
    return _curiass_id


def _get_es_chlorinated_id() -> str:
    """Get ES Chlorinated CIP Detergent ID (not sellable at TURLOCK)."""
    global _es_chlorinated_id
    if _es_chlorinated_id is None:
        db = get_supabase_client()
        result = db.table("products").select("id").ilike("product_name", "%ES Chlorinated%").execute()
        assert result.data, "ES Chlorinated CIP Detergent not found — run Sprint 2 migrations first"
        _es_chlorinated_id = result.data[0]["id"]
    return _es_chlorinated_id


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: product_exists_found
# ─────────────────────────────────────────────────────────────────────────────

def test_product_exists_found():
    """GET /product/exists?name=Curiass should return exists:true."""
    response = client.get(
        "/product/exists",
        params={"name": CURIASS_NAME},
        headers=_auth_header("consultant"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["exists"] is True
    assert data["count"] >= 1
    assert len(data["products"]) >= 1
    assert any("Curiass" in p["product_name"] for p in data["products"])
    assert data["source"] == "governance_db"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: product_exists_not_found
# ─────────────────────────────────────────────────────────────────────────────

def test_product_exists_not_found():
    """GET /product/exists?name=XyzNonExistent should return exists:false."""
    response = client.get(
        "/product/exists",
        params={"name": "XyzNonExistentProduct99999"},
        headers=_auth_header("consultant"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["exists"] is False
    assert data["count"] == 0
    assert data["products"] == []


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: product_sellable_true
# ─────────────────────────────────────────────────────────────────────────────

def test_product_sellable_true():
    """GET /product/sellable for Curiass at EVANS should return sellable:true."""
    curiass_id = _get_curiass_id()
    response = client.get(
        "/product/sellable",
        params={"product_id": curiass_id, "location_code": "EVANS"},
        headers=_auth_header("consultant"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sellable"] is True
    assert data["location_code"] == "EVANS"
    assert data["source"] == "governance_db"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4: product_sellable_false
# ─────────────────────────────────────────────────────────────────────────────

def test_product_sellable_false():
    """GET /product/sellable for ES Chlorinated at TURLOCK should return sellable:false."""
    es_id = _get_es_chlorinated_id()
    response = client.get(
        "/product/sellable",
        params={"product_id": es_id, "location_code": "TURLOCK"},
        headers=_auth_header("consultant"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sellable"] is False
    assert "reason" in data


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5: pricing_returns_exact
# ─────────────────────────────────────────────────────────────────────────────

def test_pricing_returns_exact():
    """GET /pricing/lookup for Curiass at EVANS should return matching DB values."""
    curiass_id = _get_curiass_id()
    response = client.get(
        "/pricing/lookup",
        params={"product_id": curiass_id, "location_code": "EVANS"},
        headers=_auth_header("consultant"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert data["source"] == "governance_db"
    assert data["location_code"] == "EVANS"

    # Verify pricing values match the DB
    db = get_supabase_client()
    loc_result = db.table("locations").select("id").eq("branch_code", "EVANS").execute()
    evans_id = loc_result.data[0]["id"]

    db_pricing = (
        db.table("pricing")
        .select("price_per_unit,container_size")
        .eq("product_id", curiass_id)
        .eq("location_id", evans_id)
        .is_("superseded_date", "null")
        .execute()
    )

    # API should return same count as DB
    assert data["count"] == len(db_pricing.data)

    # Spot-check: find the 265 gal container and verify exact price
    api_prices = {p["container_size"]: float(p["price_per_unit"]) for p in data["pricing"]}
    db_prices = {p["container_size"]: float(p["price_per_unit"]) for p in db_pricing.data}
    for size, price in db_prices.items():
        assert size in api_prices, f"Container size '{size}' missing from API response"
        assert api_prices[size] == price, f"Price mismatch for {size}: API={api_prices[size]}, DB={price}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6: pricing_blocked_for_customer (403)
# ─────────────────────────────────────────────────────────────────────────────

def test_pricing_blocked_for_customer():
    """GET /pricing/lookup with customer JWT should return 403."""
    curiass_id = _get_curiass_id()
    response = client.get(
        "/pricing/lookup",
        params={"product_id": curiass_id, "location_code": "EVANS"},
        headers=_auth_header("customer"),
    )
    assert response.status_code == 403
    assert "denied" in response.json()["detail"].lower() or "role" in response.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# TEST 7: location_lock_enforced (409 on mismatch)
# ─────────────────────────────────────────────────────────────────────────────

def test_location_lock_enforced():
    """Pricing lookup with conflicting session location should return 409."""
    curiass_id = _get_curiass_id()
    session_id = f"test-lock-{uuid.uuid4()}"
    headers = _auth_header("consultant")

    # First request: EVANS — should succeed and lock session
    response1 = client.get(
        "/pricing/lookup",
        params={"product_id": curiass_id, "location_code": "EVANS"},
        headers={**headers, "X-Session-ID": session_id},
    )
    assert response1.status_code == 200

    # Second request: ULYSSES (different location) — should get 409
    # Need a product sellable at ULYSSES too
    response2 = client.get(
        "/pricing/lookup",
        params={"product_id": curiass_id, "location_code": "ULYSSES"},
        headers={**headers, "X-Session-ID": session_id},
    )
    assert response2.status_code == 409
    assert "locked" in response2.json()["detail"].lower()

    # Cleanup: clear the lock
    location_lock_store.clear_location(session_id)


# ─────────────────────────────────────────────────────────────────────────────
# TEST 8: no_auth_blocked (401 on all endpoints)
# ─────────────────────────────────────────────────────────────────────────────

def test_no_auth_blocked():
    """All governance endpoints should return 401 without auth."""
    endpoints = [
        ("/product/exists", {"name": "test"}),
        ("/product/sellable", {"product_id": str(uuid.uuid4()), "location_code": "EVANS"}),
        ("/pricing/lookup", {"product_id": str(uuid.uuid4()), "location_code": "EVANS"}),
        ("/governance/health", {}),
    ]

    for path, params in endpoints:
        response = client.get(path, params=params)
        assert response.status_code == 401, (
            f"Expected 401 for {path} without auth, got {response.status_code}: "
            f"{response.json()}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# BONUS TEST: governance_never_calls_llm
# ─────────────────────────────────────────────────────────────────────────────

def test_governance_never_calls_llm():
    """
    CRITICAL: Governance endpoints must NEVER call Claude API.
    Verify that no governance module imports anthropic.
    """
    import importlib
    import inspect
    import ast

    modules_to_check = [
        ("app.api.governance", "governance.py"),
        ("app.core.auth", "auth.py"),
        ("app.services.audit_service", "audit_service.py"),
        ("app.core.location_lock", "location_lock.py"),
    ]

    for module_path, filename in modules_to_check:
        mod = importlib.import_module(module_path)
        source = inspect.getsource(mod)

        # Parse the AST to find actual import statements (not comments)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "anthropic" not in alias.name.lower(), (
                        f"{filename} imports 'anthropic' — governance must not use LLM"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module and "anthropic" in node.module.lower():
                    raise AssertionError(
                        f"{filename} imports from 'anthropic' — governance must not use LLM"
                    )


# ─────────────────────────────────────────────────────────────────────────────
# BONUS TEST: governance_health_returns_counts
# ─────────────────────────────────────────────────────────────────────────────

def test_governance_health_returns_counts():
    """GET /governance/health with admin JWT should return all counts > 0."""
    response = client.get(
        "/governance/health",
        headers=_auth_header("org_admin"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db_connected"] is True
    assert data["product_count"] > 0
    assert data["sellability_count"] > 0
    assert data["pricing_count"] > 0
    assert data["location_count"] > 0
    assert data["active_pricing_count"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# BONUS TEST: pricing_blocked_for_unsellable_product
# ─────────────────────────────────────────────────────────────────────────────

def test_pricing_blocked_for_unsellable_product():
    """GET /pricing/lookup for unsellable product+location returns 403."""
    es_id = _get_es_chlorinated_id()
    response = client.get(
        "/pricing/lookup",
        params={"product_id": es_id, "location_code": "TURLOCK"},
        headers=_auth_header("consultant"),
    )
    assert response.status_code == 403
    assert "not sellable" in response.json()["detail"].lower()
