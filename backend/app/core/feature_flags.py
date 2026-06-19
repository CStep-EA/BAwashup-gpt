"""
Bower Ag CowCare Tool — Feature Flags
Sprint 14: Simple feature gate helper with 60-second cache.

Queries system_config table. Cached to reduce DB hits.
"""

import time
from typing import Optional

from fastapi import HTTPException, status

from app.db.supabase_client import get_supabase_client


# ─── Cache ───────────────────────────────────────────────────────────────────

_cache: dict[str, tuple[bool, float]] = {}
CACHE_TTL = 60  # seconds


def _is_truthy(value) -> bool:
    """Parse a JSONB value as a boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    if isinstance(value, (int, float)):
        return bool(value)
    return False


async def check_feature(key: str) -> bool:
    """
    Check if a feature flag is enabled.
    Returns True if the config key exists and its value is truthy.
    Cached for 60 seconds.
    """
    now = time.time()

    # Check cache
    if key in _cache:
        cached_value, cached_at = _cache[key]
        if now - cached_at < CACHE_TTL:
            return cached_value

    # Query DB
    try:
        client = get_supabase_client()
        result = (
            client.table("system_config")
            .select("value")
            .eq("key", key)
            .execute()
        )
    except Exception:
        # On DB error, return False (fail closed)
        return False

    if not result.data:
        _cache[key] = (False, now)
        return False

    value = _is_truthy(result.data[0].get("value"))
    _cache[key] = (value, now)
    return value


async def require_feature(key: str) -> None:
    """
    FastAPI-compatible check: raises 403 if the feature is disabled.
    Call this at the top of an endpoint handler.
    """
    if not await check_feature(key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature is not enabled. Contact your administrator.",
        )


def clear_feature_cache() -> None:
    """Clear the feature flag cache (used in tests)."""
    _cache.clear()
