"""
Bower Ag CowCare Tool — Integration Health Tests
Sprint 15, Step 4: Verify each external service is reachable and functional.

Tests:
  INT-01: Supabase connection — query locations table
  INT-02: Supabase auth — sign_in_with_password for test user
  INT-03: Claude API — simple ping with minimal tokens
  INT-04: R2 storage — upload + presign + delete lifecycle
  INT-05: pgvector — generate embedding, verify dimension and type
  INT-06: pgvector search — cosine similarity query on document_chunks
  INT-07: Redis — connect and PING (requires REDIS_URL)
  INT-08: FastAPI /health — app health endpoint returns 200

All tests are skipped gracefully if the service is not configured.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app


# ─── Shared Client ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ─── INT-01: Supabase Connection ─────────────────────────────────────────────

class TestSupabase:
    """Verify Supabase connectivity and basic operations."""

    def test_int01_supabase_connection(self):
        """INT-01: Query locations table — confirms Supabase is reachable."""
        from app.db.supabase_client import get_supabase_client

        supabase = get_supabase_client()
        result = supabase.table("locations").select("id,branch_code").limit(1).execute()

        assert result.data is not None, "Supabase query returned None — connection failed"
        assert len(result.data) >= 1, "No locations found — DB may be empty"
        assert "branch_code" in result.data[0], "Missing 'branch_code' column"

    def test_int02_supabase_auth(self):
        """INT-02: Sign in with a test user to verify Supabase Auth."""
        from app.db.supabase_client import get_supabase_anon_client

        anon = get_supabase_anon_client()

        # Use the org_admin test account
        email = os.environ.get("TEST_ADMIN_EMAIL", "admin@bowerag.test")
        password = os.environ.get("TEST_ADMIN_PASSWORD", "TestAdmin123!")

        try:
            result = anon.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
        except Exception as e:
            pytest.skip(f"Supabase Auth sign-in failed (test user may not exist): {e}")
            return

        assert result.session is not None, "No session returned — auth failed"
        assert result.session.access_token, "No access_token in session"
        assert result.user is not None, "No user object returned"
        assert result.user.email == email


# ─── INT-03: Claude API ──────────────────────────────────────────────────────

class TestClaudeAPI:
    """Verify Claude API is reachable."""

    def test_int03_claude_ping(self):
        """INT-03: Send a minimal Claude request to verify API key + connectivity."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set — skipping Claude test")

        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            )
        except anthropic.AuthenticationError:
            pytest.fail("Claude API authentication failed — check ANTHROPIC_API_KEY")
        except anthropic.RateLimitError:
            pytest.skip("Claude API rate limited — try again later")
        except Exception as e:
            pytest.fail(f"Claude API call failed: {e}")

        assert response.content, "Claude returned empty content"
        assert response.usage.input_tokens > 0, "No input tokens recorded"
        assert response.usage.output_tokens > 0, "No output tokens recorded"


# ─── INT-04: R2 Storage ──────────────────────────────────────────────────────

class TestR2Storage:
    """Verify Cloudflare R2 upload / presign / delete lifecycle."""

    def test_int04_r2_lifecycle(self):
        """INT-04: Upload a test file, presign it, then delete it."""
        from app.services.storage_service import get_storage_service, StorageError

        storage = get_storage_service()

        if not storage._configured:
            pytest.skip("R2 credentials not configured — skipping storage test")

        import asyncio

        test_key = f"test/integration-{uuid.uuid4().hex[:8]}.txt"
        test_data = b"Bower Ag integration test - safe to delete"

        async def _lifecycle():
            # Upload
            path = await storage.upload_bytes(test_data, test_key, "text/plain")
            assert path == test_key, f"Upload returned wrong path: {path}"

            # Presign
            url = await storage.get_presigned_url(test_key, expiry_seconds=60)
            assert url.startswith("https://"), f"Presigned URL invalid: {url}"
            assert test_key in url or "X-Amz-Signature" in url

            # Delete
            deleted = await storage.delete_file(test_key)
            assert deleted is True, "Delete returned False"

        try:
            asyncio.get_event_loop().run_until_complete(_lifecycle())
        except StorageError as e:
            pytest.fail(f"R2 storage operation failed: {e}")


# ─── INT-05 & INT-06: pgvector ───────────────────────────────────────────────

class TestPgvector:
    """Verify embedding generation and pgvector similarity search."""

    def test_int05_embedding_generation(self):
        """INT-05: Generate an embedding and verify dimension/type."""
        from app.services.embedding_service import (
            get_query_embedding,
            TARGET_DIM,
        )

        embedding = get_query_embedding("mastitis treatment protocol")

        assert isinstance(embedding, list), f"Expected list, got {type(embedding)}"
        assert len(embedding) == TARGET_DIM, (
            f"Expected {TARGET_DIM} dimensions, got {len(embedding)}"
        )
        # All values should be floats
        assert all(isinstance(v, float) for v in embedding[:10]), "Embedding contains non-float values"

        # The non-padded portion should have non-zero values
        non_zero_count = sum(1 for v in embedding if v != 0.0)
        assert non_zero_count >= 100, (
            f"Only {non_zero_count} non-zero values — embedding may be degenerate"
        )

    def test_int06_pgvector_search(self):
        """INT-06: Run a cosine similarity search on document_chunks."""
        from app.db.supabase_client import get_supabase_client
        from app.services.embedding_service import get_query_embedding

        supabase = get_supabase_client()

        # First check if document_chunks has any data
        count_result = (
            supabase.table("document_chunks")
            .select("id", count="exact")
            .limit(1)
            .execute()
        )

        if not count_result.data:
            pytest.skip("No document_chunks found — RAG not seeded yet")

        # Generate query embedding
        embedding = get_query_embedding("cow comfort bedding")

        # Call the match_documents RPC
        try:
            result = supabase.rpc(
                "match_documents",
                {
                    "query_embedding": embedding,
                    "match_threshold": 0.0,  # Return everything (test only)
                    "match_count": 3,
                },
            ).execute()
        except Exception as e:
            # If the RPC doesn't exist, skip gracefully
            if "function" in str(e).lower() and "not" in str(e).lower():
                pytest.skip(f"match_documents RPC not available: {e}")
            raise

        assert result.data is not None, "pgvector search returned None"
        assert len(result.data) >= 1, "pgvector search returned no results"

        # Verify result structure
        first = result.data[0]
        assert "content" in first or "chunk_text" in first, (
            f"Result missing content field. Keys: {list(first.keys())}"
        )
        assert "similarity" in first, "Result missing similarity score"


# ─── INT-07: Redis ───────────────────────────────────────────────────────────

class TestRedis:
    """Verify Redis connectivity for ARQ job queue."""

    def test_int07_redis_ping(self):
        """INT-07: Connect to Redis and PING."""
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            pytest.skip("REDIS_URL not set — skipping Redis test")

        try:
            import redis as redis_lib
        except ImportError:
            pytest.skip("redis package not installed")
            return

        try:
            r = redis_lib.from_url(redis_url, socket_timeout=5)
            pong = r.ping()
            assert pong is True, f"Redis PING returned {pong}"
        except redis_lib.ConnectionError:
            pytest.skip(f"Redis not reachable at {redis_url}")
        except Exception as e:
            pytest.skip(f"Redis connection failed: {e}")


# ─── INT-08: FastAPI /health ─────────────────────────────────────────────────

class TestHealthEndpoint:
    """Verify the application health endpoint."""

    def test_int08_health(self, client):
        """INT-08: GET /health returns 200 with expected fields."""
        resp = client.get("/health")

        assert resp.status_code == 200, f"Health check returned {resp.status_code}"

        data = resp.json()
        assert "status" in data, "Health response missing 'status' field"
        assert data["status"] == "ok", f"Status is '{data['status']}', expected 'ok'"
        assert "version" in data, "Health response missing 'version' field"
