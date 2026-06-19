#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Bower Ag CowCare Tool — Backend Test Runner
# Sprint 15: Run backend unit + integration tests (excludes regression).
#
# Usage:
#   bash backend/scripts/run_tests.sh           # all backend tests (no regression)
#   bash backend/scripts/run_tests.sh -v         # verbose
#   bash backend/scripts/run_tests.sh -k "role"  # filter by keyword
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Bower Ag CowCare Tool — Backend Tests              ║"
echo "║  Excludes @regression (use run_regression.sh)       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Load .env if present
if [ -f .env ]; then
    echo "📂 Loading .env..."
    set -a
    source .env
    set +a
fi

# Run all tests EXCEPT those marked @regression
echo "🧪 Running backend tests (excluding regression)..."
echo ""

python -m pytest app/tests/ \
    -m "not regression" \
    --tb=short \
    -q \
    "$@"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Backend tests passed!"
else
    echo "❌ Backend tests failed (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
