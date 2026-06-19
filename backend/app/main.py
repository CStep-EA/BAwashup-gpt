"""
Bower Ag CowCare Tool — FastAPI Backend
Sprint 16: Production hardening — CORS lockdown, startup validation, Sentry.

Governance-first: pricing comes from DB, never from LLM memory.
"""

import logging
import os
import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("bowerag.startup")

# ─── Sentry (optional — only if DSN configured) ─────────────────────────────
_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=_sentry_dsn,
            traces_sample_rate=0.1,
            environment=os.getenv("ENVIRONMENT", "development"),
            release=os.getenv("APP_VERSION", "0.0.1"),
        )
        logger.info("[Sentry] Initialized with trace sampling at 10%%")
    except ImportError:
        logger.warning("[Sentry] sentry-sdk not installed — monitoring disabled")
    except Exception as e:
        logger.warning(f"[Sentry] Failed to initialize: {e}")


# ─── CORS Configuration ─────────────────────────────────────────────────────

def _build_cors_origins() -> list[str]:
    """
    Build the CORS allowed origins list based on environment.

    Production: only the explicitly listed ALLOWED_ORIGINS.
    Development: ALLOWED_ORIGINS + localhost dev servers.
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    raw = os.getenv("ALLOWED_ORIGINS", "")

    origins: list[str] = []
    if raw:
        origins = [o.strip() for o in raw.split(",") if o.strip()]

    if env != "production":
        # Development: also allow local dev servers
        dev_origins = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ]
        for d in dev_origins:
            if d not in origins:
                origins.append(d)

    if not origins:
        logger.warning(
            "[CORS] No origins configured. "
            "Set ALLOWED_ORIGINS in production or ENVIRONMENT=development for localhost."
        )

    return origins


# ─── Startup Validation ─────────────────────────────────────────────────────

async def _startup_checks():
    """
    Run production readiness checks on startup.
    Log each result. Critical failures log errors but do NOT crash the app.
    """
    version = os.getenv("APP_VERSION", "0.0.1")
    env = os.getenv("ENVIRONMENT", "development")
    logger.info(f"[Startup] Bower Ag CowCare API v{version} ({env})")

    # Check 1: Supabase connection — query locations table
    try:
        from app.db.supabase_client import get_supabase_client
        client = get_supabase_client()
        result = client.table("locations").select("id").execute()
        count = len(result.data) if result.data else 0
        if count >= 5:
            logger.info(f"[Startup] ✅ Supabase: {count} locations found")
        else:
            logger.error(
                f"[Startup] ⚠️ Supabase: only {count} locations found (expected ≥5)"
            )
    except Exception as e:
        logger.error(f"[Startup] ❌ Supabase connection failed: {e}")

    # Check 2: ffmpeg availability
    try:
        proc = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            version_line = proc.stdout.split("\n")[0] if proc.stdout else "unknown"
            logger.info(f"[Startup] ✅ ffmpeg: {version_line}")
        else:
            logger.warning(f"[Startup] ⚠️ ffmpeg returned exit code {proc.returncode}")
    except FileNotFoundError:
        logger.warning("[Startup] ⚠️ ffmpeg not found — video processing unavailable")
    except Exception as e:
        logger.warning(f"[Startup] ⚠️ ffmpeg check failed: {e}")

    # Check 3: Claude API key
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if api_key:
        logger.info("[Startup] ✅ ANTHROPIC_API_KEY is set")
    else:
        logger.error("[Startup] ❌ ANTHROPIC_API_KEY is empty — chat will fail")

    # Check 4: R2 bucket reachable
    try:
        from app.services.storage_service import get_storage_service
        storage = get_storage_service()
        if storage._configured:
            # Quick test: try to generate a presigned URL for a test path
            url = await storage.get_presigned_url("__startup_check__", expiry_seconds=60)
            if url:
                logger.info("[Startup] ✅ R2 storage: bucket reachable")
        else:
            logger.warning("[Startup] ⚠️ R2 storage: credentials not configured")
    except Exception as e:
        logger.warning(f"[Startup] ⚠️ R2 storage check failed: {e}")

    # Check 5: Redis (non-critical)
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        try:
            import redis as redis_lib
            r = redis_lib.from_url(redis_url, socket_timeout=5)
            r.ping()
            logger.info("[Startup] ✅ Redis: connected")
        except Exception as e:
            logger.warning(f"[Startup] ⚠️ Redis: not reachable ({e})")
    else:
        logger.warning("[Startup] ⚠️ REDIS_URL not set — video worker queue unavailable")

    logger.info("[Startup] Startup validation complete.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — run startup checks, then serve."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    await _startup_checks()
    yield
    logger.info("[Shutdown] Bower Ag CowCare API shutting down.")


# ─── Application ─────────────────────────────────────────────────────────────

from app.api.governance import router as governance_router
from app.api.rag import router as rag_router
from app.api.conversation import router as conversation_router
from app.api.session import router as session_router
from app.api.products import router as products_router
from app.api.reports import router as reports_router
from app.api.admin_analytics import router as admin_analytics_router
from app.api.admin_users import router as admin_users_router
from app.api.admin_config import router as admin_config_router
from app.api.admin_bugs import router as admin_bugs_router
from app.api.admin_versions import router as admin_versions_router
from app.api.admin_audit import router as admin_audit_router
from app.api.customer_reports import router as customer_reports_router
from app.api.media import router as media_router

app = FastAPI(
    title="Bower Ag CowCare API",
    description="Expert system for dairy cow care — governance-first, mobile-first.",
    version=os.getenv("APP_VERSION", "0.0.1"),
    lifespan=lifespan,
)

# CORS — environment-aware origin restriction
# Only add CORS middleware if there are configured origins.
# In production with no ALLOWED_ORIGINS set, no CORS headers = blocked.
_cors_origins = _build_cors_origins()
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Location-Code",
            "X-Language",
        ],
    )

# ─── Routers ───
app.include_router(governance_router)
app.include_router(rag_router)
app.include_router(conversation_router)
app.include_router(session_router)
app.include_router(products_router)
app.include_router(reports_router)
app.include_router(admin_analytics_router)
app.include_router(admin_users_router)
app.include_router(admin_config_router)
app.include_router(admin_bugs_router)
app.include_router(admin_versions_router)
app.include_router(admin_audit_router)
app.include_router(customer_reports_router)
app.include_router(media_router)


@app.get("/health")
async def health_check():
    """Health check — confirms the API is running. Used by Railway + monitoring."""
    return {
        "status": "ok",
        "service": "bowerag-cowcare-api",
        "version": os.getenv("APP_VERSION", "0.1.0-beta"),
        "environment": os.getenv("ENVIRONMENT", "development"),
    }
