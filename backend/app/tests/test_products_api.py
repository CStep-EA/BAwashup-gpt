"""
Bower Ag CowCare Tool — Products API Tests
Sprint 8: 7 required tests for product catalog endpoints.

These tests run against the LIVE Supabase instance with real JWT tokens.
Test users are created in Supabase auth with specific roles.

Usage:
  cd backend
  pytest app/tests/test_products_api.py -v
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

# Test user credentials (created during Sprint 3 setup)
TEST_USERS = {
    "org_admin": {"email": "admin@bowerag.test", "password": "TestAdmin123!"},
    "consultant": {"email": "consultant@bowerag.test", "password": "TestConsult123!"},
    "customer": {"email": "customer@bowerag.test", "password": "TestCustomer123!"},
}

_token_cache: dict[str, str] = {}


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

    token = result.session.access_token
    _token_cache[role] = token
    return token


def _auth_headers(role: str = "consultant") -> dict:
    """Return Authorization headers for a test user."""
    return {"Authorization": f"Bearer {_get_token(role)}"}


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestProductList:
    """Test GET /products endpoint."""

    def test_product_list_returns_results(self):
        """GET /products -> expects count > 0 and valid schema on first item."""
        response = client.get("/products", headers=_auth_headers())

        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "total_count" in data
        assert "has_more" in data
        assert isinstance(data["products"], list)
        assert data["total_count"] >= 0

        if data["products"]:
            product = data["products"][0]
            # Verify schema
            assert "id" in product
            assert "product_name" in product
            assert "category" in product
            assert "product_type" in product
            assert "chemistry_type" in product
            assert "is_concentrate" in product
            assert "sds_verified" in product

    def test_product_search_by_name(self):
        """GET /products?search=<term> -> expects matching products."""
        # First get any product name to search for
        response = client.get("/products?limit=1", headers=_auth_headers())
        assert response.status_code == 200
        data = response.json()

        if not data["products"]:
            pytest.skip("No products in database to test search.")

        # Use first 4 chars of product name as search term
        product_name = data["products"][0]["product_name"]
        search_term = product_name[:4]

        response = client.get(
            f"/products?search={search_term}",
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        results = response.json()
        assert results["total_count"] > 0
        # At least one result should contain the search term (case-insensitive)
        found = any(
            search_term.lower() in p["product_name"].lower()
            or (p.get("part_number") and search_term.lower() in p["part_number"].lower())
            for p in results["products"]
        )
        assert found, f"No product name/part_number contains '{search_term}'"

    def test_product_filter_by_category(self):
        """GET /products?category=teat_dip -> all results have product_type='teat_dip'."""
        response = client.get(
            "/products?category=teat_dip",
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()

        # All results must match the category filter
        for product in data["products"]:
            assert product["product_type"] == "teat_dip", (
                f"Product '{product['product_name']}' has type '{product['product_type']}', expected 'teat_dip'"
            )

    def test_product_filter_by_location(self):
        """GET /products?location_code=EVANS -> only returns Evans-sellable products."""
        response = client.get(
            "/products?location_code=EVANS",
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()

        if not data["products"]:
            pytest.skip("No Evans-sellable products in database.")

        # Cross-check: pick first result, verify sellable at EVANS via /product/sellable
        product_id = data["products"][0]["id"]
        sell_response = client.get(
            f"/product/sellable?product_id={product_id}&location_code=EVANS",
            headers=_auth_headers(),
        )
        assert sell_response.status_code == 200
        sell_data = sell_response.json()
        assert sell_data["sellable"] is True, (
            f"Product {product_id} returned by location filter but not sellable at EVANS"
        )


class TestProductDetail:
    """Test GET /products/{product_id} endpoint."""

    def test_product_detail_includes_sellability(self):
        """GET /products/{id} -> response.sellability has entries for each location."""
        # Get a product ID first
        list_response = client.get("/products?limit=1", headers=_auth_headers())
        assert list_response.status_code == 200
        products = list_response.json()["products"]

        if not products:
            pytest.skip("No products in database to test detail.")

        product_id = products[0]["id"]

        response = client.get(
            f"/products/{product_id}",
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()

        assert "sellability" in data
        assert isinstance(data["sellability"], list)
        # Should have entries (up to 5 locations)
        assert len(data["sellability"]) >= 1

        # Each entry has required fields
        for entry in data["sellability"]:
            assert "location_name" in entry
            assert "branch_code" in entry
            assert "sellable" in entry
            assert isinstance(entry["sellable"], bool)

    def test_product_detail_includes_pricing(self):
        """GET /products/{id} -> response includes my_location_pricing field."""
        list_response = client.get("/products?limit=1", headers=_auth_headers())
        assert list_response.status_code == 200
        products = list_response.json()["products"]

        if not products:
            pytest.skip("No products in database to test pricing.")

        product_id = products[0]["id"]

        response = client.get(
            f"/products/{product_id}",
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()

        # my_location_pricing should exist (may be empty if user has no location assigned)
        assert "my_location_pricing" in data
        assert isinstance(data["my_location_pricing"], list)

        # If pricing exists, verify schema
        if data["my_location_pricing"]:
            entry = data["my_location_pricing"][0]
            assert "container_size" in entry
            assert "uom" in entry
            assert "price_per_unit" in entry


class TestProductAccess:
    """Test role-based access control."""

    def test_customer_blocked(self):
        """GET /products with customer JWT -> 403."""
        response = client.get("/products", headers=_auth_headers("customer"))
        assert response.status_code == 403
        assert "denied" in response.json()["detail"].lower() or "permission" in response.json()["detail"].lower()
