#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Bower Ag CowCare Tool - Vercel Frontend Smoke Test
# Sprint 19D: Run after Vercel deployment to verify frontend
# Usage: ./scripts/verify_vercel_deploy.sh https://your-project.vercel.app
# ─────────────────────────────────────────────────────────
set -euo pipefail

VERCEL_URL="${1:-}"
if [ -z "$VERCEL_URL" ]; then
    echo "Usage: $0 <vercel-url>"
    echo "Example: $0 https://bawashup-gpt.vercel.app"
    exit 1
fi

# Remove trailing slash
VERCEL_URL="${VERCEL_URL%/}"
BACKEND_URL="https://bawashup-gpt-production.up.railway.app"

PASS=0
FAIL=0
TOTAL=0

check() {
    local name="$1"
    local result="$2"
    TOTAL=$((TOTAL + 1))
    if [ "$result" = "true" ]; then
        echo -e "\033[32m[PASS]\033[0m $name"
        PASS=$((PASS + 1))
    else
        echo -e "\033[31m[FAIL]\033[0m $name"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "=== Bower Ag CowCare Tool - Vercel Smoke Test ==="
echo "Target: $VERCEL_URL"
echo ""

# --- Page Load ---
echo "--- Page Load ---"

status=$(curl -s -o /dev/null -w "%{http_code}" "$VERCEL_URL")
check "Homepage returns 200" "$([ "$status" = "200" ] && echo true || echo false)"

body=$(curl -s "$VERCEL_URL")
check "Homepage contains root div" "$(echo "$body" | grep -q 'id="root"' && echo true || echo false)"
check "Homepage contains app title" "$(echo "$body" | grep -q 'CowCare Tool' && echo true || echo false)"

# --- SPA Routing ---
echo ""
echo "--- SPA Routing (rewrites) ---"

status=$(curl -s -o /dev/null -w "%{http_code}" "$VERCEL_URL/login")
check "Deep link /login returns 200" "$([ "$status" = "200" ] && echo true || echo false)"

status=$(curl -s -o /dev/null -w "%{http_code}" "$VERCEL_URL/dashboard")
check "Deep link /dashboard returns 200" "$([ "$status" = "200" ] && echo true || echo false)"

status=$(curl -s -o /dev/null -w "%{http_code}" "$VERCEL_URL/products")
check "Deep link /products returns 200" "$([ "$status" = "200" ] && echo true || echo false)"

# --- Security Headers ---
echo ""
echo "--- Security Headers ---"

headers=$(curl -sI "$VERCEL_URL")
check "X-Content-Type-Options: nosniff" "$(echo "$headers" | grep -qi 'x-content-type-options.*nosniff' && echo true || echo false)"
check "X-Frame-Options: DENY" "$(echo "$headers" | grep -qi 'x-frame-options.*deny' && echo true || echo false)"
check "Referrer-Policy present" "$(echo "$headers" | grep -qi 'referrer-policy.*strict-origin' && echo true || echo false)"

# --- Static Assets ---
echo ""
echo "--- Static Assets ---"

status=$(curl -s -o /dev/null -w "%{http_code}" "$VERCEL_URL/favicon.svg")
check "Favicon accessible" "$([ "$status" = "200" ] && echo true || echo false)"

status=$(curl -s -o /dev/null -w "%{http_code}" "$VERCEL_URL/pwa-192x192.png")
check "PWA icon 192x192 accessible" "$([ "$status" = "200" ] && echo true || echo false)"

status=$(curl -s -o /dev/null -w "%{http_code}" "$VERCEL_URL/apple-touch-icon.png")
check "Apple touch icon accessible" "$([ "$status" = "200" ] && echo true || echo false)"

# --- PWA ---
echo ""
echo "--- PWA ---"

status=$(curl -s -o /dev/null -w "%{http_code}" "$VERCEL_URL/sw.js")
check "Service worker accessible" "$([ "$status" = "200" ] && echo true || echo false)"

sw_cache=$(curl -sI "$VERCEL_URL/sw.js" | grep -i cache-control)
check "Service worker no-cache header" "$(echo "$sw_cache" | grep -qi 'no-cache' && echo true || echo false)"

# --- Backend Connectivity ---
echo ""
echo "--- Backend Connectivity ---"

status=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health")
check "Railway backend /health reachable" "$([ "$status" = "200" ] && echo true || echo false)"

health_body=$(curl -s "$BACKEND_URL/health")
check "Railway backend returns status ok" "$(echo "$health_body" | grep -q '"ok"' && echo true || echo false)"

# --- Summary ---
echo ""
echo "============================================"
if [ "$FAIL" -eq 0 ]; then
    echo -e "\033[32mResults: $PASS/$TOTAL passed, $FAIL failed\033[0m"
    echo "All checks passed! Frontend is deployed correctly."
else
    echo -e "\033[31mResults: $PASS/$TOTAL passed, $FAIL failed\033[0m"
    echo "Some checks failed. See above for details."
fi
echo "============================================"

exit "$FAIL"
