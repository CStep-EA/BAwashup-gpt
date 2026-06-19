#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Bower Ag CowCare Tool — Full Test Suite Runner
# Sprint 15: Run ALL tests — backend, frontend, and optionally E2E + regression.
#
# Usage:
#   bash scripts/run_all_tests.sh                  # backend + frontend unit
#   bash scripts/run_all_tests.sh --regression     # include regression
#   bash scripts/run_all_tests.sh --e2e            # include Playwright E2E
#   bash scripts/run_all_tests.sh --all            # everything
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse flags
RUN_REGRESSION=false
RUN_E2E=false

for arg in "$@"; do
    case "$arg" in
        --regression) RUN_REGRESSION=true ;;
        --e2e) RUN_E2E=true ;;
        --all) RUN_REGRESSION=true; RUN_E2E=true ;;
        *) ;;
    esac
done

TOTAL_EXIT=0

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Bower Ag CowCare Tool — Full Test Suite            ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Flags: regression=$RUN_REGRESSION  e2e=$RUN_E2E"
echo ""

# ────────────────────────────────────────────────────────────────────────────
# 1. Backend Unit + Integration Tests
# ────────────────────────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 1/4  Backend Tests (excluding regression)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$PROJECT_ROOT/backend"

if [ -f .env ]; then
    set -a; source .env; set +a
fi

python -m pytest app/tests/ -m "not regression" --tb=short -q || TOTAL_EXIT=1

echo ""

# ────────────────────────────────────────────────────────────────────────────
# 2. Frontend Unit Tests (Vitest)
# ────────────────────────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎨 2/4  Frontend Unit Tests (Vitest)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$PROJECT_ROOT/frontend"
npx vitest run --reporter=default || TOTAL_EXIT=1

echo ""

# ────────────────────────────────────────────────────────────────────────────
# 3. Governance Regression (optional — costs real API calls)
# ────────────────────────────────────────────────────────────────────────────
if [ "$RUN_REGRESSION" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔬 3/4  Governance Regression (Claude API)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    cd "$PROJECT_ROOT/backend"
    python -m pytest app/tests/test_governance_regression.py \
        -m "regression" --tb=long -v || TOTAL_EXIT=1
    echo ""
else
    echo "⏭️  3/4  Governance Regression — SKIPPED (use --regression)"
    echo ""
fi

# ────────────────────────────────────────────────────────────────────────────
# 4. Playwright E2E (optional — requires dev servers running)
# ────────────────────────────────────────────────────────────────────────────
if [ "$RUN_E2E" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 4/4  Playwright E2E Tests"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    cd "$PROJECT_ROOT/frontend"
    npx playwright test --reporter=list || TOTAL_EXIT=1
    echo ""
else
    echo "⏭️  4/4  Playwright E2E — SKIPPED (use --e2e)"
    echo ""
fi

# ────────────────────────────────────────────────────────────────────────────
# Summary
# ────────────────────────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $TOTAL_EXIT -eq 0 ]; then
    echo "✅ All test suites PASSED!"
else
    echo "❌ Some test suites FAILED — check output above."
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit $TOTAL_EXIT
