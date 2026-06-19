#!/usr/bin/env python3
"""
Bower Ag CowCare Tool — R2 Storage Smoke Test
Sprint 9: Upload, presign, download, delete.

Usage: cd backend && python scripts/test_r2.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

import requests
from app.services.storage_service import get_storage_service, StorageError


async def main():
    passed = 0
    failed = 0

    print("═══════════════════════════════════════════════")
    print(" R2 Storage Smoke Test")
    print("═══════════════════════════════════════════════")

    try:
        storage = get_storage_service()
        if not storage._configured:
            print("  ⚠️  R2 credentials not configured — skipping live tests")
            print("  ℹ️  Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY in .env")
            print("\n  ✅ PASS — StorageService initialized (unconfigured mode)")
            sys.exit(0)
    except StorageError as e:
        print(f"  ❌ INIT FAILED: {e}")
        sys.exit(1)

    test_path = "_test/smoke_test.txt"
    test_data = b"hello bowerag"

    # ── Test 1: Upload ──
    print("\n1. Upload:")
    try:
        result = await storage.upload_bytes(test_data, test_path, "text/plain")
        assert result == test_path
        print(f"  ✅ PASS — uploaded to {result}")
        passed += 1
    except Exception as e:
        print(f"  ❌ FAIL — {e}")
        failed += 1

    # ── Test 2: Presigned URL + Download ──
    print("\n2. Presigned URL + Download:")
    try:
        url = await storage.get_presigned_url(test_path, expiry_seconds=300)
        assert url.startswith("https://"), f"URL doesn't start with https: {url[:60]}"

        resp = requests.get(url, timeout=10)
        assert resp.status_code == 200, f"Download returned {resp.status_code}"
        assert resp.content == test_data, f"Content mismatch: {resp.content!r}"

        print(f"  ✅ PASS — downloaded and verified ({len(resp.content)} bytes)")
        passed += 1
    except Exception as e:
        print(f"  ❌ FAIL — {e}")
        failed += 1

    # ── Test 3: Delete ──
    print("\n3. Delete:")
    try:
        ok = await storage.delete_file(test_path)
        assert ok, "delete_file returned False"
        print("  ✅ PASS — file deleted")
        passed += 1
    except Exception as e:
        print(f"  ❌ FAIL — {e}")
        failed += 1

    print("\n═══════════════════════════════════════════════")
    print(f" Results: {passed}/3 PASS, {failed} FAIL")
    print("═══════════════════════════════════════════════")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
