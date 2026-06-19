#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Bower Ag CowCare Tool — Full Test Suite Runner
# Sprint 12: Runs backend + frontend tests and reports combined results.
#
# Usage:
#   ./scripts/run_all_tests.sh
# ─────────────────────────────────────────────────────────────────────────────

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

PASS=0
FAIL=0

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        BOWER AG COWCARE TOOL — FULL TEST SUITE              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Backend tests ──
echo "━━━ Backend Tests (pytest) ━━━"
cd "$ROOT_DIR/backend"

# Load .env if present
if [ -f .env ]; then
    set -a
    source .env 2>/dev/null
    set +a
fi

if python -m pytest app/tests/ -m "not regression" --tb=short -q 2>&1; then
    echo "✅ Backend tests passed"
    PASS=$((PASS + 1))
else
    echo "❌ Backend tests failed"
    FAIL=$((FAIL + 1))
fi

echo ""

# ── Frontend unit tests ──
echo "━━━ Frontend Tests (vitest) ━━━"
cd "$ROOT_DIR/frontend"

if npx vitest run --reporter=verbose 2>&1; then
    echo "✅ Frontend tests passed"
    PASS=$((PASS + 1))
else
    echo "❌ Frontend tests failed"
    FAIL=$((FAIL + 1))
fi

echo ""

# ── Frontend TypeScript check ──
echo "━━━ TypeScript Check ━━━"
if npx tsc --noEmit 2>&1; then
    echo "✅ TypeScript: no errors"
    PASS=$((PASS + 1))
else
    echo "❌ TypeScript check failed"
    FAIL=$((FAIL + 1))
fi

echo ""

# ── Summary ──
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL=$((PASS + FAIL))
echo "  Results: ${PASS}/${TOTAL} test suites passed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAIL -gt 0 ]; then
    echo ""
    echo "❌ FULL SUITE FAILED — $FAIL suite(s) did not pass"
    exit 1
else
    echo ""
    echo "✅ ALL TEST SUITES PASSED"
    exit 0
fi
