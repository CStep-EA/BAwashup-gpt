"""
Bower Ag CowCare Tool — Location Lock Service
Sprint 3: Per-session location locking for governance enforcement.

Each session (identified by X-Session-ID header) is locked to one location.
Once locked, pricing queries for a different location return 409 Conflict
until the lock is explicitly cleared.

This prevents reps from accidentally mixing pricing between locations
during a single customer visit session.
"""

import threading
from datetime import datetime
from typing import Optional


class LocationLockStore:
    """
    Thread-safe in-memory location lock store.
    Maps session_id -> (location_code, locked_at, user_id).

    NOTE: In-memory = resets on server restart. Acceptable for MVP.
    Production could use Redis for persistence across restarts.
    """

    def __init__(self):
        self._locks: dict[str, dict] = {}
        self._lock = threading.Lock()

    def set_location(
        self,
        session_id: str,
        location_code: str,
        user_id: str,
    ) -> None:
        """Lock a session to a specific location."""
        with self._lock:
            self._locks[session_id] = {
                "location_code": location_code,
                "locked_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
            }

    def get_location(self, session_id: str) -> Optional[str]:
        """Get the locked location_code for a session, or None if not locked."""
        with self._lock:
            entry = self._locks.get(session_id)
            return entry["location_code"] if entry else None

    def get_lock_info(self, session_id: str) -> Optional[dict]:
        """Get full lock info for a session."""
        with self._lock:
            return self._locks.get(session_id)

    def clear_location(self, session_id: str) -> bool:
        """Clear the lock for a session. Returns True if lock existed."""
        with self._lock:
            return self._locks.pop(session_id, None) is not None

    def check_and_lock(
        self,
        session_id: str,
        location_code: str,
        user_id: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if session is already locked to a different location.

        Returns:
            (ok, existing_location_code)
            - (True, None) if no lock existed → lock now set
            - (True, location_code) if already locked to same location → OK
            - (False, existing_code) if locked to a different location → CONFLICT
        """
        with self._lock:
            entry = self._locks.get(session_id)

            if entry is None:
                # No lock — set it now
                self._locks[session_id] = {
                    "location_code": location_code,
                    "locked_at": datetime.utcnow().isoformat(),
                    "user_id": user_id,
                }
                return (True, None)

            if entry["location_code"] == location_code:
                # Same location — all good
                return (True, location_code)

            # Different location — CONFLICT
            return (False, entry["location_code"])

    @property
    def active_locks_count(self) -> int:
        """Number of active session locks (for monitoring)."""
        with self._lock:
            return len(self._locks)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton instance — shared across all requests
# ─────────────────────────────────────────────────────────────────────────────
location_lock_store = LocationLockStore()
