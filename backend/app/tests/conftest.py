"""
Bower Ag CowCare Tool — Shared Test Fixtures
Sprint 15: Centralized fixtures for all backend test suites.

Fixtures (session-scoped tokens, function-scoped data):
  supabase_client       — Supabase admin (service_role) client
  test_client           — FastAPI TestClient
  org_admin_headers     — Authorization headers for org_admin
  admin_manager_headers — Authorization headers for admin_manager
  consultant_headers    — Authorization headers for consultant
  customer_headers      — Authorization headers for customer
  test_location_evans   — EVANS location row from DB
  test_location_kansas  — ULYSSES location row from DB
  known_product         — Product sellable at EVANS
  known_product_not_in_kansas — Product NOT sellable at ULYSSES

All tokens come from real Supabase test accounts.
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


# ─── Test user credentials ────────────────────────────────────────────────────

TEST_USERS = {
    "org_admin": {"email": "admin@bowerag.test", "password": "TestAdmin123!"},
    "admin_manager": {"email": "manager@bowerag.test", "password": "TestManager123!"},
    "consultant": {"email": "consultant@bowerag.test", "password": "TestConsult123!"},
    "customer": {"email": "customer@bowerag.test", "password": "TestCustomer123!"},
}

# Caches (session-scoped — populated once)
_token_cache: dict[str, str] = {}
_user_id_cache: dict[str, str] = {}


def _sign_in(role: str) -> tuple[str, str]:
    """Sign in a test user, return (access_token, user_id)."""
    if role in _token_cache:
        return _token_cache[role], _user_id_cache[role]

    anon = get_supabase_anon_client()
    creds = TEST_USERS[role]
    try:
        result = anon.auth.sign_in_with_password({
            "email": creds["email"],
            "password": creds["password"],
        })
    except Exception as e:
        pytest.skip(f"Could not sign in test user '{role}': {e}")
        return "", ""

    if not result.session:
        pytest.skip(f"No session for test user '{role}'. Ensure user exists in Supabase.")

    _token_cache[role] = result.session.access_token
    _user_id_cache[role] = result.user.id
    return _token_cache[role], _user_id_cache[role]


# ─── Core fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def supabase_client():
    """Supabase admin client (service_role key)."""
    return get_supabase_client()


@pytest.fixture(scope="session")
def test_client():
    """FastAPI TestClient — shared across entire session."""
    return TestClient(app)


@pytest.fixture(scope="session")
def org_admin_headers() -> dict:
    """Authorization headers for org_admin test user."""
    token, _ = _sign_in("org_admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def org_admin_user_id() -> str:
    """User ID of org_admin test user."""
    _, uid = _sign_in("org_admin")
    return uid


@pytest.fixture(scope="session")
def admin_manager_headers() -> dict:
    """Authorization headers for admin_manager test user."""
    token, _ = _sign_in("admin_manager")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def consultant_headers() -> dict:
    """Authorization headers for consultant test user."""
    token, _ = _sign_in("consultant")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def consultant_user_id() -> str:
    """User ID of consultant test user."""
    _, uid = _sign_in("consultant")
    return uid


@pytest.fixture(scope="session")
def customer_headers() -> dict:
    """Authorization headers for customer test user."""
    token, _ = _sign_in("customer")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def customer_user_id() -> str:
    """User ID of customer test user."""
    _, uid = _sign_in("customer")
    return uid


# ─── Location fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_location_evans(supabase_client):
    """EVANS location row from the locations table."""
    result = (
        supabase_client.table("locations")
        .select("*")
        .eq("branch_code", "EVANS")
        .limit(1)
        .execute()
    )
    if not result.data:
        pytest.skip("EVANS location not found in DB.")
    return result.data[0]


@pytest.fixture(scope="session")
def test_location_kansas(supabase_client):
    """ULYSSES location row from the locations table."""
    result = (
        supabase_client.table("locations")
        .select("*")
        .eq("branch_code", "ULYSSES")
        .limit(1)
        .execute()
    )
    if not result.data:
        pytest.skip("ULYSSES location not found in DB.")
    return result.data[0]


# ─── Product fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def known_product(supabase_client, test_location_evans):
    """A product that is verified sellable at EVANS."""
    evans_id = test_location_evans["id"]

    # Find a product with sellable=true at EVANS
    sell_result = (
        supabase_client.table("product_sellability")
        .select("product_id")
        .eq("location_id", evans_id)
        .eq("sellable", True)
        .limit(1)
        .execute()
    )
    if not sell_result.data:
        pytest.skip("No sellable product found at EVANS.")

    product_id = sell_result.data[0]["product_id"]
    prod_result = (
        supabase_client.table("products")
        .select("*")
        .eq("id", product_id)
        .limit(1)
        .execute()
    )
    if not prod_result.data:
        pytest.skip("Product row not found for sellable product at EVANS.")
    return prod_result.data[0]


@pytest.fixture(scope="session")
def known_product_not_in_kansas(supabase_client, test_location_kansas):
    """A product where sellable=false at ULYSSES."""
    kansas_id = test_location_kansas["id"]

    sell_result = (
        supabase_client.table("product_sellability")
        .select("product_id")
        .eq("location_id", kansas_id)
        .eq("sellable", False)
        .limit(1)
        .execute()
    )
    if not sell_result.data:
        pytest.skip("No non-sellable product found at ULYSSES.")

    product_id = sell_result.data[0]["product_id"]
    prod_result = (
        supabase_client.table("products")
        .select("*")
        .eq("id", product_id)
        .limit(1)
        .execute()
    )
    if not prod_result.data:
        pytest.skip("Product row not found for non-sellable product at ULYSSES.")
    return prod_result.data[0]


# ─── Convenience helpers (importable by test files) ───────────────────────────

def get_test_token(role: str) -> str:
    """Get JWT token for a test role — callable outside fixtures."""
    token, _ = _sign_in(role)
    return token


def get_test_user_id(role: str) -> str:
    """Get user ID for a test role."""
    _, uid = _sign_in(role)
    return uid


def auth_headers(role: str) -> dict:
    """Build auth headers for a role."""
    return {"Authorization": f"Bearer {get_test_token(role)}"}
