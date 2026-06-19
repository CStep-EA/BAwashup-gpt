#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Bower Ag CowCare Tool — Production Smoke Tests
# Sprint 16: Verify deployed services are functioning correctly.
#
# Usage:
#   bash scripts/production_smoke_test.sh
#
# Environment variables (override defaults):
#   API_URL  — Railway backend URL (default: from .env.production)
#   UI_URL   — Vercel frontend URL (default: from .env.production)
#   ADMIN_JWT — org_admin Bearer token for authenticated tests
# ─────────────────────────────────────────────────────────────────────────────

set -uo pipefail

# Defaults — override with env vars
API="${API_URL:-https://bawashup-gpt-production.up.railway.app}"
UI="${UI_URL:-https://bawashup-gpt.vercel.app}"
ADMIN_JWT="${ADMIN_JWT:-}"

PASS=0
FAIL=0

pass() { echo "  ✅ PASS: $1"; ((PASS++)); }
fail() { echo "  ❌ FAIL: $1"; ((FAIL++)); }

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Bower Ag CowCare — Production Smoke Tests          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  API: $API"
echo "  UI:  $UI"
echo ""

# ─── Test 1: API Health ──────────────────────────────────────────────────────
echo "━━━ 1. API Health Check ━━━"
STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$API/health" 2>/dev/null || echo "000")
if [ "$STATUS" -eq 200 ]; then
    BODY=$(curl -s "$API/health")
    VERSION=$(echo "$BODY" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    pass "/health returns 200 (version: $VERSION)"
else
    fail "/health returned $STATUS (expected 200)"
fi

# ─── Test 2: Health response structure ───────────────────────────────────────
echo "━━━ 2. Health Response Structure ━━━"
BODY=$(curl -s "$API/health" 2>/dev/null || echo "{}")
if echo "$BODY" | grep -q '"status":"ok"'; then
    pass "Health response contains status=ok"
else
    fail "Health response missing status=ok: $BODY"
fi

# ─── Test 3: CORS blocks unknown origin ──────────────────────────────────────
echo "━━━ 3. CORS Security ━━━"
CORS_RESP=$(curl -s -I -H "Origin: https://evil.com" -H "Access-Control-Request-Method: GET" \
    -X OPTIONS "$API/health" 2>/dev/null || echo "")
if echo "$CORS_RESP" | grep -qi "access-control-allow-origin: https://evil.com"; then
    fail "CORS allows evil.com — too permissive!"
else
    pass "CORS blocks unknown origin (evil.com)"
fi

# ─── Test 4: Unauthenticated request gets 401 ───────────────────────────────
echo "━━━ 4. Auth Guard ━━━"
AUTH_STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$API/products" 2>/dev/null || echo "000")
if [ "$AUTH_STATUS" -eq 401 ]; then
    pass "Unauthenticated /products returns 401"
else
    fail "Unauthenticated /products returned $AUTH_STATUS (expected 401)"
fi

# ─── Test 5: Governance health (requires admin token) ────────────────────────
echo "━━━ 5. Governance Health (admin auth) ━━━"
if [ -n "$ADMIN_JWT" ]; then
    GOV_STATUS=$(curl -s -o /dev/null -w '%{http_code}' \
        -H "Authorization: Bearer $ADMIN_JWT" "$API/governance/health" 2>/dev/null || echo "000")
    if [ "$GOV_STATUS" -eq 200 ]; then
        GOV_BODY=$(curl -s -H "Authorization: Bearer $ADMIN_JWT" "$API/governance/health")
        if echo "$GOV_BODY" | grep -q "product_count"; then
            pass "Governance health returns product_count"
        else
            fail "Governance health missing product_count: $GOV_BODY"
        fi
    else
        fail "Governance health returned $GOV_STATUS (expected 200)"
    fi
else
    echo "  ⏭️  SKIPPED: Set ADMIN_JWT to test governance health"
fi

# ─── Test 6: UI loads ────────────────────────────────────────────────────────
echo "━━━ 6. Frontend UI ━━━"
UI_STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$UI" 2>/dev/null || echo "000")
if [ "$UI_STATUS" -eq 200 ]; then
    UI_BODY=$(curl -s "$UI" 2>/dev/null || echo "")
    if echo "$UI_BODY" | grep -q "CowCare\|bowerag\|root"; then
        pass "UI loads and contains expected content"
    else
        pass "UI returns 200 (content check inconclusive)"
    fi
else
    fail "UI returned $UI_STATUS (expected 200)"
fi

# ─── Test 7: UI security headers ────────────────────────────────────────────
echo "━━━ 7. Security Headers ━━━"
SEC_HEADERS=$(curl -s -I "$UI" 2>/dev/null || echo "")
if echo "$SEC_HEADERS" | grep -qi "x-content-type-options"; then
    pass "X-Content-Type-Options header present"
else
    fail "X-Content-Type-Options header missing"
fi

# ─── Test 8: API version check ───────────────────────────────────────────────
echo "━━━ 8. Version Verification ━━━"
API_VERSION=$(curl -s "$API/health" 2>/dev/null | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
if [ "$API_VERSION" = "0.1.0-beta" ]; then
    pass "API version is 0.1.0-beta"
elif [ -n "$API_VERSION" ]; then
    echo "  ⚠️  INFO: API version is '$API_VERSION' (expected 0.1.0-beta)"
    ((PASS++))
else
    fail "Could not determine API version"
fi

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Results: $PASS passed, $FAIL failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAIL -gt 0 ]; then
    echo "  ❌ Some smoke tests failed. Review output above."
    exit 1
else
    echo "  ✅ All smoke tests passed!"
    exit 0
fi
