#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Bower Ag CowCare Tool — Governance Regression Runner
# Sprint 15: Run ONLY @regression tests (expensive — calls real Claude API).
#
# ⚠️  These tests call the Claude API and cost real money.
#     Run intentionally, not on every file save.
#
# Usage:
#   bash scripts/run_regression.sh             # run all regression tests
#   bash scripts/run_regression.sh -k "GR-01"  # single test
#   bash scripts/run_regression.sh -v           # verbose
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

cd "$BACKEND_DIR"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Bower Ag — Governance Regression Suite              ║"
echo "║  ⚠️  Calls real Claude API — run intentionally       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Load .env
if [ -f .env ]; then
    echo "📂 Loading .env..."
    set -a
    source .env
    set +a
fi

# Verify ANTHROPIC_API_KEY is set
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "❌ ANTHROPIC_API_KEY not set. Cannot run regression tests."
    echo "   Set it in backend/.env or export it."
    exit 1
fi

echo "🧪 Running governance regression tests..."
echo ""

python -m pytest app/tests/test_governance_regression.py \
    -m "regression" \
    --tb=long \
    -v \
    "$@"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Governance regression suite passed!"
else
    echo "❌ Governance regression suite failed (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
