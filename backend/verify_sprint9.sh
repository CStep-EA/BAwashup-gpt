#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Bower Ag CowCare Tool — Sprint 9 Verification Script
# Report Generator Backend
#
# Checks:
#   1-5   : Storage service (storage_service.py)
#   6-10  : Migration SQL (004_reports.sql)
#   11-18 : Report builder (report_builder.py)
#   19-30 : Reports API endpoints (reports.py)
#   31-38 : Backend tests (test_reports.py)
#   39-42 : Integration & registration
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PASS=0; FAIL=0; TOTAL=0

check() {
  TOTAL=$((TOTAL + 1))
  local label="$1"; local result="$2"
  if [[ "$result" == "PASS" ]]; then
    PASS=$((PASS + 1))
    printf "  ✅ %2d. %s\n" "$TOTAL" "$label"
  else
    FAIL=$((FAIL + 1))
    printf "  ❌ %2d. %s  [%s]\n" "$TOTAL" "$label" "$result"
  fi
}

BACK="$(cd "$(dirname "$0")/../backend" && pwd)"
cd "$BACK"

echo ""
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║           Sprint 9 — Report Generator Backend                   ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# ── 1-5: Storage Service ──────────────────────────────────────────────────
echo "─── Storage Service (storage_service.py) ───"

FILE="app/services/storage_service.py"
[[ -f "$FILE" ]] && R="PASS" || R="MISSING"
check "storage_service.py exists" "$R"

grep -q "class StorageService" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "StorageService class defined" "$R"

grep -q "_configured" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Graceful _configured guard for missing credentials" "$R"

grep -q "async def upload_bytes" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "upload_bytes method" "$R"

grep -q "async def get_presigned_url" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "get_presigned_url method" "$R"

# ── 6-10: Migration SQL ──────────────────────────────────────────────────
echo ""
echo "─── Migration SQL (004_reports.sql) ───"

FILE="scripts/migrations/004_reports.sql"
[[ -f "$FILE" ]] && R="PASS" || R="MISSING"
check "004_reports.sql exists" "$R"

grep -q "CREATE TABLE.*reports" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "CREATE TABLE reports statement" "$R"

grep -q "CHECK.*status.*IN\|status.*CHECK" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Status CHECK constraint (generating/complete/failed/deleted)" "$R"

grep -q "CREATE POLICY" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "RLS policies defined" "$R"

grep -q "customer_shared_reports\|shared_with_customer" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Customer shared reports RLS policy" "$R"

# ── 11-18: Report Builder ────────────────────────────────────────────────
echo ""
echo "─── Report Builder (report_builder.py) ───"

FILE="app/services/report_builder.py"
[[ -f "$FILE" ]] && R="PASS" || R="MISSING"
check "report_builder.py exists" "$R"

grep -q "def build_report_docx" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "build_report_docx function defined" "$R"

grep -q "python-docx\|from docx\|import docx" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Uses python-docx library" "$R"

grep -q "cover.*page\|BOWER AG\|cover_page" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Cover page generation" "$R"

grep -q "pricing.*table\|pricing_table\|add_table" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Pricing table in DOCX" "$R"

grep -q "_parse_report_sections\|section.*header\|## " "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Section parsing (## headers)" "$R"

grep -q "About Bower Ag\|about.*bower\|BOWER" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "About Bower Ag section support" "$R"

# Verify DOCX generation works
python -c "
from app.services.report_builder import build_report_docx
from docx import Document
import io
content = '''## A Quick Note
Test intro.
## What We Found
Findings here.
## Our Recommendations
Recs here.
## What Happens Next
Next steps.
## About Bower Ag
About text.'''
result = build_report_docx('Farm','Op','Evans','Rep','Title','2026-05-14',content,[],False)
doc = Document(io.BytesIO(result))
assert len(doc.paragraphs) >= 3
print('OK')
" 2>/dev/null && R="PASS" || R="FAIL"
check "DOCX generation produces valid file" "$R"

# ── 19-30: Reports API ──────────────────────────────────────────────────
echo ""
echo "─── Reports API Endpoints (reports.py) ───"

FILE="app/api/reports.py"
[[ -f "$FILE" ]] && R="PASS" || R="MISSING"
check "reports.py exists" "$R"

grep -q "router = APIRouter" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "APIRouter defined" "$R"

grep -q 'prefix="/reports"' "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Router prefix is /reports" "$R"

grep -q "async def generate_report" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "POST /reports/generate endpoint" "$R"

grep -q "async def list_reports" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "GET /reports endpoint (list)" "$R"

grep -q "async def get_report" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "GET /reports/{report_id} endpoint (detail)" "$R"

grep -q "async def share_report" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "POST /reports/{report_id}/share endpoint" "$R"

grep -q "async def delete_report" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "DELETE /reports/{report_id} endpoint" "$R"

# Pipeline step checks
grep -q "STEP A\|Validate location\|branch_code" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Step A: Location validation in pipeline" "$R"

grep -q "STEP B\|Governance check\|product_sellability" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Step B: Governance check every product" "$R"

grep -q "call_claude\|STEP D" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Step D: Claude API call for content generation" "$R"

grep -q "build_report_docx\|STEP E" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Step E: DOCX build via report_builder" "$R"

grep -q "upload_bytes\|STEP F\|R2" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Step F: R2 upload" "$R"

# ── 31-38: Backend Tests ─────────────────────────────────────────────────
echo ""
echo "─── Backend Tests (test_reports.py) ───"

FILE="app/tests/test_reports.py"
[[ -f "$FILE" ]] && R="PASS" || R="MISSING"
check "test_reports.py exists" "$R"

grep -q "test_r2_upload_download_delete" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: R2 upload/download/delete" "$R"

grep -q "test_report_generate_success" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: Report generate success" "$R"

grep -q "test_report_governance_blocks_unsellable" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: Governance blocks unsellable product" "$R"

grep -q "test_report_content_humanized" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: Report content humanized (no forbidden phrases)" "$R"

grep -q "test_report_docx_is_valid_file" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: DOCX valid file" "$R"

grep -q "test_report_list_returns_only_own" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: Report list returns only own" "$R"

grep -q "test_report_share_enables_customer_access" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: Share enables customer access" "$R"

grep -q "test_customer_cannot_generate_report" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: Customer cannot generate report (403)" "$R"

# ── 39-42: Integration & Registration ────────────────────────────────────
echo ""
echo "─── Integration & Registration ───"

MAIN="app/main.py"
grep -q "reports" "$MAIN" 2>/dev/null && R="PASS" || R="MISSING"
check "reports_router imported in main.py" "$R"

grep -q "include_router.*report" "$MAIN" 2>/dev/null && R="PASS" || R="MISSING"
check "reports_router registered with app.include_router()" "$R"

# Verify imports work
python -c "from app.api.reports import router; print(len(router.routes))" 2>/dev/null | grep -q "[0-9]" && R="PASS" || R="FAIL"
check "Reports router imports without error" "$R"

# Verify route count (5 endpoints)
ROUTE_COUNT=$(python -c "from app.api.reports import router; print(len(router.routes))" 2>/dev/null || echo "0")
[[ "$ROUTE_COUNT" -ge 5 ]] && R="PASS" || R="EXPECTED 5, GOT $ROUTE_COUNT"
check "Reports router has >= 5 routes" "$R"

# ── Summary ──────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════"
printf "  Sprint 9 Verification: %d / %d passed" "$PASS" "$TOTAL"
if [[ "$FAIL" -gt 0 ]]; then
  printf "  (%d FAILED)" "$FAIL"
fi
echo ""
echo "═══════════════════════════════════════════════════════════════════"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
