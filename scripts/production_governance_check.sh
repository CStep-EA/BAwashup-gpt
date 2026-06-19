#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Bower Ag CowCare Tool — Production Governance Quick Check
# Sprint 20: Verify governance endpoints are functioning in production.
#
# This does NOT call Claude API — it only checks that governance data
# is accessible and endpoints respond correctly.
#
# Usage:
#   export ADMIN_JWT="eyJ..."  # Get from browser DevTools after logging in
#   bash scripts/production_governance_check.sh
#
# Or with explicit URL:
#   API_URL=https://bawashup-gpt-production.up.railway.app \
#   ADMIN_JWT="eyJ..." \
#   bash scripts/production_governance_check.sh
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

API="${API_URL:-https://bawashup-gpt-production.up.railway.app}"
JWT="${ADMIN_JWT:-}"

PASS=0
FAIL=0
SKIP=0

pass() { echo "  [PASS] $1"; ((PASS++)); }
fail() { echo "  [FAIL] $1"; ((FAIL++)); }
skip() { echo "  [SKIP] $1"; ((SKIP++)); }

echo ""
echo "=== Production Governance Quick Check ==="
echo "API: $API"
echo ""

# ─── 1. Health endpoint confirms production ─────────────────────────────────
echo "--- 1. Environment Check ---"
ENV=$(curl -s "$API/health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('environment',''))" 2>/dev/null)
if [ "$ENV" = "production" ]; then
    pass "Running in production environment"
else
    fail "Expected environment=production, got: $ENV"
fi

# ─── 2. Unauthenticated governance access blocked ───────────────────────────
echo "--- 2. Governance Auth Guard ---"
GOV_NOAUTH=$(curl -s -o /dev/null -w "%{http_code}" "$API/governance/health")
if [ "$GOV_NOAUTH" = "401" ] || [ "$GOV_NOAUTH" = "403" ]; then
    pass "Governance health blocked without auth ($GOV_NOAUTH)"
else
    fail "Governance health returned $GOV_NOAUTH without auth (expected 401/403)"
fi

# ─── 3. Products endpoint requires auth ─────────────────────────────────────
echo "--- 3. Products Auth Guard ---"
PROD_NOAUTH=$(curl -s -o /dev/null -w "%{http_code}" "$API/products")
if [ "$PROD_NOAUTH" = "401" ] || [ "$PROD_NOAUTH" = "403" ]; then
    pass "Products endpoint blocked without auth ($PROD_NOAUTH)"
else
    fail "Products returned $PROD_NOAUTH without auth (expected 401/403)"
fi

# ─── 4. Conversation endpoint requires auth ─────────────────────────────────
echo "--- 4. Conversation Auth Guard ---"
CONV_NOAUTH=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST -H "Content-Type: application/json" \
    -d '{"message":"test","conversation_history":[]}' \
    "$API/conversation")
if [ "$CONV_NOAUTH" = "401" ] || [ "$CONV_NOAUTH" = "403" ]; then
    pass "Conversation endpoint blocked without auth ($CONV_NOAUTH)"
else
    fail "Conversation returned $CONV_NOAUTH without auth (expected 401/403)"
fi

# ─── 5. CORS: Only Vercel origin allowed ────────────────────────────────────
echo "--- 5. CORS Policy ---"
GOOD_ORIGIN=$(curl -s -D - -o /dev/null \
    -H "Origin: https://bawashup-gpt.vercel.app" \
    "$API/health" 2>&1 | grep -i "access-control-allow-origin" | tr -d '\r')
if echo "$GOOD_ORIGIN" | grep -q "bawashup-gpt.vercel.app"; then
    pass "CORS allows Vercel origin"
else
    fail "CORS did not return allow-origin for Vercel: $GOOD_ORIGIN"
fi

BAD_ORIGIN=$(curl -s -D - -o /dev/null \
    -H "Origin: https://evil.com" \
    "$API/health" 2>&1 | grep -i "access-control-allow-origin" | tr -d '\r')
if [ -z "$BAD_ORIGIN" ]; then
    pass "CORS blocks evil.com origin"
else
    fail "CORS allowed evil.com: $BAD_ORIGIN"
fi

# ─── 6-10. Authenticated checks (require JWT) ───────────────────────────────
if [ -z "$JWT" ]; then
    echo ""
    echo "--- Authenticated Tests (SKIPPED - set ADMIN_JWT) ---"
    skip "Governance health data check"
    skip "Product count > 0"
    skip "Pricing lookup responds"
    skip "Admin analytics accessible"
    skip "Audit log accessible"
else
    AUTH_HEADER="Authorization: Bearer $JWT"

    echo "--- 6. Governance Health Data ---"
    GOV_BODY=$(curl -s -H "$AUTH_HEADER" "$API/governance/health")
    GOV_STATUS=$?
    if echo "$GOV_BODY" | grep -q "product_count"; then
        PCOUNT=$(echo "$GOV_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('product_count',0))" 2>/dev/null)
        pass "Governance health: $PCOUNT products in DB"
    else
        fail "Governance health missing product_count: $GOV_BODY"
    fi

    echo "--- 7. Products Accessible ---"
    PROD_BODY=$(curl -s -H "$AUTH_HEADER" "$API/products?limit=1")
    if echo "$PROD_BODY" | grep -q "products"; then
        TCOUNT=$(echo "$PROD_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_count',0))" 2>/dev/null)
        pass "Products endpoint: $TCOUNT total products"
    else
        fail "Products endpoint error: $PROD_BODY"
    fi

    echo "--- 8. Admin Analytics ---"
    ANALYTICS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH_HEADER" "$API/admin/analytics/summary")
    if [ "$ANALYTICS_STATUS" = "200" ]; then
        pass "Admin analytics accessible"
    else
        fail "Admin analytics returned $ANALYTICS_STATUS"
    fi

    echo "--- 9. Audit Log ---"
    AUDIT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH_HEADER" "$API/admin/audit?limit=1")
    if [ "$AUDIT_STATUS" = "200" ]; then
        pass "Audit log accessible"
    else
        fail "Audit log returned $AUDIT_STATUS"
    fi

    echo "--- 10. Admin Config ---"
    CONFIG_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH_HEADER" "$API/admin/config")
    if [ "$CONFIG_STATUS" = "200" ]; then
        pass "Admin config accessible"
    else
        fail "Admin config returned $CONFIG_STATUS"
    fi
fi

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
    echo "  Results: $PASS/$TOTAL passed, $SKIP skipped"
    echo "  All governance checks passed!"
else
    echo "  Results: $PASS/$TOTAL passed, $FAIL FAILED, $SKIP skipped"
    echo "  Some governance checks failed!"
fi
echo "============================================"
echo ""

exit "$FAIL"
