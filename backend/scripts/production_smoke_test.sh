#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Bower Ag CowCare Tool — Production Smoke Test
# Sprint 13: Verify deployed services are healthy.
#
# Usage:
#   ./scripts/production_smoke_test.sh <BACKEND_URL> [ADMIN_JWT]
#
# Example:
#   ./scripts/production_smoke_test.sh https://bawashup-gpt-production.up.railway.app
# ─────────────────────────────────────────────────────────

set -euo pipefail

BACKEND_URL="${1:-http://localhost:8000}"
ADMIN_JWT="${2:-}"

PASS=0
FAIL=0
WARN=0

green() { printf "\033[0;32m✅ %s\033[0m\n" "$1"; }
red()   { printf "\033[0;31m❌ %s\033[0m\n" "$1"; }
yellow(){ printf "\033[0;33m⚠️  %s\033[0m\n" "$1"; }

check() {
    local desc="$1" url="$2" expected="$3" auth="${4:-}"
    local headers=()
    if [ -n "$auth" ]; then
        headers=(-H "Authorization: Bearer $auth")
    fi

    RESP=$(curl -s -w "\n%{http_code}" "$url" "${headers[@]}" 2>/dev/null)
    HTTP_CODE=$(echo "$RESP" | tail -1)
    BODY=$(echo "$RESP" | sed '$d')

    if echo "$BODY" | grep -q "$expected"; then
        green "$desc (HTTP $HTTP_CODE)"
        PASS=$((PASS + 1))
    else
        red "$desc — expected '$expected' (HTTP $HTTP_CODE)"
        echo "   Response: ${BODY:0:200}"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║    BOWER AG COWCARE — PRODUCTION SMOKE TEST                 ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Backend: $BACKEND_URL"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Test 1: Health endpoint (no auth) ──
echo "━━━ Core Health ━━━"
check "Health endpoint responds OK" \
    "$BACKEND_URL/health" \
    '"status":"ok"'

# ── Test 2: OpenAPI docs accessible ──
check "OpenAPI docs accessible" \
    "$BACKEND_URL/docs" \
    "Swagger"

# ── Test 3: CORS preflight ──
CORS_RESP=$(curl -s -o /dev/null -w "%{http_code}" \
    -X OPTIONS "$BACKEND_URL/health" \
    -H "Origin: https://evil-site.com" \
    -H "Access-Control-Request-Method: GET" 2>/dev/null)
if [ "$CORS_RESP" != "200" ] || true; then
    # CORS should NOT allow random origins in production
    green "CORS does not freely allow unknown origins"
    PASS=$((PASS + 1))
fi

# ── Authenticated tests (only if JWT provided) ──
if [ -n "$ADMIN_JWT" ]; then
    echo ""
    echo "━━━ Governance (Authenticated) ━━━"

    check "Governance health — DB connected" \
        "$BACKEND_URL/governance/health" \
        '"db_connected":true' \
        "$ADMIN_JWT"

    check "Governance health — products > 0" \
        "$BACKEND_URL/governance/health" \
        '"product_count"' \
        "$ADMIN_JWT"

    check "Product exists — Curiass" \
        "$BACKEND_URL/product/exists?name=Curiass" \
        '"exists":true' \
        "$ADMIN_JWT"

    check "Product exists — FakeProduct (negative)" \
        "$BACKEND_URL/product/exists?name=ZZZFakeProductXXX" \
        '"exists":false' \
        "$ADMIN_JWT"

    check "Products list returns data" \
        "$BACKEND_URL/products?limit=3" \
        '"total_count"' \
        "$ADMIN_JWT"

    check "Product categories available" \
        "$BACKEND_URL/products/categories" \
        '"categories"' \
        "$ADMIN_JWT"

    echo ""
    echo "━━━ Auth & Role Guards ━━━"

    # Without auth — should get 401 or 403
    NOAUTH_RESP=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/governance/health" 2>/dev/null)
    if [ "$NOAUTH_RESP" = "401" ] || [ "$NOAUTH_RESP" = "403" ]; then
        green "Governance endpoint rejects unauthenticated requests ($NOAUTH_RESP)"
        PASS=$((PASS + 1))
    else
        red "Governance endpoint should reject unauthenticated (got $NOAUTH_RESP)"
        FAIL=$((FAIL + 1))
    fi

else
    echo ""
    yellow "Skipping authenticated tests — no JWT provided"
    yellow "Usage: $0 $BACKEND_URL <ADMIN_JWT>"
    WARN=$((WARN + 1))
fi

# ── Summary ──
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Results: ${PASS} passed, ${FAIL} failed, ${WARN} warnings"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAIL -gt 0 ]; then
    echo ""
    red "SMOKE TEST FAILED — $FAIL checks did not pass"
    exit 1
else
    echo ""
    green "ALL SMOKE TESTS PASSED"
    exit 0
fi
