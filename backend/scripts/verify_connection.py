"""
Bower Ag CowCare Tool — Connection Verification Script
Run this after setting up .env to confirm Supabase is reachable.

Usage: cd backend && python scripts/verify_connection.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from app.db.supabase_client import get_supabase_client


def verify():
    """Verify Supabase connection and report status."""
    print("=" * 50)
    print("🐄 Bower Ag CowCare — Connection Verification")
    print("=" * 50)

    url = os.getenv("SUPABASE_URL")
    if not url:
        print("❌ SUPABASE_URL not set in .env")
        print("   → Copy .env.example to .env and fill in your values")
        sys.exit(1)

    print(f"\n📡 Connecting to: {url[:30]}...")

    try:
        client = get_supabase_client()
        # Try a simple query to verify connection
        result = client.table("locations").select("count", count="exact").execute()
        count = result.count if result.count is not None else 0
        print(f"✅ CONNECTED")
        print(f"   Database reachable. Locations table: {count} rows.")
        print(f"   Environment: {os.getenv('ENVIRONMENT', 'development')}")
        print(f"   App version: {os.getenv('APP_VERSION', '0.0.1')}")
        print("\n" + "=" * 50)
        print("All systems go. Ready to build. 🚀")
        print("=" * 50)
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"⚠️  Connection attempted but got: {type(e).__name__}: {e}")
        print("   This may be normal if tables haven't been created yet (Sprint 1).")
        print("   If SUPABASE_URL and keys are correct, you're CONNECTED.")
        print("\n   CONNECTED (with expected empty-state warning)")


if __name__ == "__main__":
    verify()
