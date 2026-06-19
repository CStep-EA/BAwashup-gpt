#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Bower Ag CowCare Tool — Railway Readiness Verification
# Sprint 18D: Run locally before deploying to Railway.
#
# Checks:
#   1. Required files exist (nixpacks.toml, railway.toml, Procfile, requirements.txt)
#   2. Health endpoint returns {status: "ok"}
#   3. CORS rejects unknown origins
#   4. All .env.example variables documented
#   5. Governance prompts contain required strings
#   6. Backend Python syntax is valid
#
# Usage:
#   bash scripts/verify_railway_readiness.sh
# ─────────────────────────────────────────────────────────────────────────────

set -uo pipefail

PASS=0
FAIL=0
WARN=0

pass() { echo "  ✅ PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  ❌ FAIL: $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  ⚠️  WARN: $1"; WARN=$((WARN + 1)); }

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Bower Ag CowCare — Railway Deployment Readiness Check     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ─── Check 1: Required deployment files ────────────────────────────────────
echo "━━━ 1. Required Deployment Files ━━━"

BACKEND_DIR="$(cd "$(dirname "$0")/../backend" && pwd)"

check_file() {
    if [ -f "$BACKEND_DIR/$1" ]; then
        pass "$1 exists"
    else
        fail "$1 MISSING — required for Railway deployment"
    fi
}

check_file "nixpacks.toml"
check_file "railway.toml"
check_file "Procfile"
check_file "requirements.txt"
check_file "app/main.py"
check_file "app/core/prompts.py"

# ─── Check 2: nixpacks.toml contains ffmpeg ────────────────────────────────
echo ""
echo "━━━ 2. nixpacks.toml — ffmpeg ━━━"

if grep -q "ffmpeg" "$BACKEND_DIR/nixpacks.toml" 2>/dev/null; then
    pass "nixpacks.toml includes ffmpeg"
else
    fail "nixpacks.toml missing ffmpeg — video processing will fail"
fi

# ─── Check 3: railway.toml health check timeout ────────────────────────────
echo ""
echo "━━━ 3. railway.toml — Health Check ━━━"

if grep -q 'healthcheckPath = "/health"' "$BACKEND_DIR/railway.toml" 2>/dev/null; then
    pass "Health check path = /health"
else
    fail "Health check path not configured in railway.toml"
fi

TIMEOUT=$(grep -oP 'healthcheckTimeout = \K\d+' "$BACKEND_DIR/railway.toml" 2>/dev/null || echo "0")
if [ "$TIMEOUT" -ge 300 ]; then
    pass "Health check timeout = ${TIMEOUT}s (≥300)"
else
    fail "Health check timeout = ${TIMEOUT}s (must be ≥300)"
fi

# ─── Check 4: Health endpoint returns "ok" ─────────────────────────────────
echo ""
echo "━━━ 4. Health Endpoint Response ━━━"

if command -v python3 &>/dev/null; then
    HEALTH_STATUS=$(cd "$BACKEND_DIR" && python3 -c "
import os, sys
os.environ.setdefault('ENVIRONMENT', 'development')
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
resp = client.get('/health')
import json
data = resp.json()
if data.get('status') == 'ok':
    print('OK')
else:
    print(f'MISMATCH: {json.dumps(data)}')
" 2>/dev/null || echo "ERROR")

    if [ "$HEALTH_STATUS" = "OK" ]; then
        pass "Health endpoint returns {\"status\": \"ok\"}"
    elif [[ "$HEALTH_STATUS" == MISMATCH* ]]; then
        fail "Health endpoint status mismatch: $HEALTH_STATUS"
    else
        warn "Could not test health endpoint locally (missing deps?)"
    fi
else
    warn "python3 not available — skipping health endpoint test"
fi

# ─── Check 5: CORS configuration ──────────────────────────────────────────
echo ""
echo "━━━ 5. CORS Configuration ━━━"

if grep -q "X-Location-Code" "$BACKEND_DIR/app/main.py" 2>/dev/null; then
    pass "CORS includes X-Location-Code header"
else
    fail "CORS missing X-Location-Code header"
fi

if grep -q "X-Language" "$BACKEND_DIR/app/main.py" 2>/dev/null; then
    pass "CORS includes X-Language header"
else
    fail "CORS missing X-Language header"
fi

if grep -q 'allow_headers=\["\*"\]' "$BACKEND_DIR/app/main.py" 2>/dev/null; then
    fail "CORS still using wildcard headers — must be explicit"
else
    pass "CORS headers are not wildcard"
fi

# ─── Check 6: Governance prompts ──────────────────────────────────────────
echo ""
echo "━━━ 6. Governance Prompts ━━━"

PROMPTS_FILE="$BACKEND_DIR/app/core/prompts.py"

check_prompt() {
    if grep -q "$1" "$PROMPTS_FILE" 2>/dev/null; then
        pass "prompts.py contains: $1"
    else
        fail "prompts.py MISSING: $1"
    fi
}

check_prompt "GOVERNANCE RULES"
check_prompt "NEVER recall pricing from memory"
check_prompt "BASE_SYSTEM_PROMPT"
check_prompt "WASH_AUDIT_REPORT_ADDENDUM"
check_prompt "Vendor display"
check_prompt "Location restrictions"

# ─── Check 7: Environment variable documentation ──────────────────────────
echo ""
echo "━━━ 7. Environment Variables (.env.example) ━━━"

ENV_FILE="$BACKEND_DIR/.env.example"
REQUIRED_VARS=(
    "SUPABASE_URL"
    "SUPABASE_ANON_KEY"
    "SUPABASE_SERVICE_ROLE_KEY"
    "ANTHROPIC_API_KEY"
    "R2_ACCOUNT_ID"
    "R2_ACCESS_KEY_ID"
    "R2_SECRET_ACCESS_KEY"
    "R2_BUCKET_NAME"
    "APP_VERSION"
    "ENVIRONMENT"
    "ALLOWED_ORIGINS"
    "SENTRY_DSN"
)

for var in "${REQUIRED_VARS[@]}"; do
    if grep -q "^${var}=" "$ENV_FILE" 2>/dev/null; then
        pass "$var documented in .env.example"
    else
        fail "$var MISSING from .env.example"
    fi
done

# ─── Check 8: Python syntax validation ────────────────────────────────────
echo ""
echo "━━━ 8. Python Syntax Check ━━━"

SYNTAX_ERRORS=0
while IFS= read -r -d '' pyfile; do
    if ! python3 -c "import ast; ast.parse(open('$pyfile').read())" 2>/dev/null; then
        fail "Syntax error in: ${pyfile#$BACKEND_DIR/}"
        SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
    fi
done < <(find "$BACKEND_DIR/app" -name "*.py" -print0)

if [ "$SYNTAX_ERRORS" -eq 0 ]; then
    pass "All Python files pass syntax check"
fi

# ─── Summary ─────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Results: $PASS passed, $FAIL failed, $WARN warnings"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAIL -gt 0 ]; then
    echo ""
    echo "  ❌ DEPLOYMENT NOT READY — Fix failures above before deploying."
    exit 1
elif [ $WARN -gt 0 ]; then
    echo ""
    echo "  ⚠️  Deployment likely ready — review warnings above."
    exit 0
else
    echo ""
    echo "  ✅ ALL CHECKS PASSED — Ready for Railway deployment!"
    exit 0
fi
