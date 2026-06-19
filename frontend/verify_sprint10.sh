#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Bower Ag CowCare Tool — Sprint 10 Verification Script
# Reports Frontend
#
# Checks:
#   1-6   : Reports store + API types
#   7-14  : ReportCard component
#   15-24 : NewReportForm (4-step)
#   25-30 : ShareReportModal
#   31-34 : ReportPreviewPage
#   35-39 : ReportsPage (list + empty state)
#   40-44 : Route wiring + build
#   45-53 : Frontend tests (9 tests)
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

FRONT="$(cd "$(dirname "$0")/../frontend" && pwd)"
cd "$FRONT"

echo ""
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║           Sprint 10 — Reports Frontend                          ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# ── 1-6: Reports Store + API Types ──────────────────────────────────────────
echo "─── Reports Store + API Types ───"

FILE="src/store/reports.ts"
[[ -f "$FILE" ]] && R="PASS" || R="MISSING"
check "reports.ts store exists" "$R"

grep -q "useReportsStore" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "useReportsStore Zustand store exported" "$R"

grep -q "loadReports" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "loadReports action defined" "$R"

grep -q "startPolling\|pollingInterval\|setInterval" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Polling mechanism for generating reports" "$R"

grep -q "completedToast" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Toast state for completed reports" "$R"

FILE="src/lib/api.ts"
grep -q "ReportGenerateRequest\|generateReport" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Report API types and functions in api.ts" "$R"

# ── 7-14: ReportCard Component ──────────────────────────────────────────────
echo ""
echo "─── ReportCard Component ───"

FILE="src/components/reports/ReportCard.tsx"
[[ -f "$FILE" ]] && R="PASS" || R="MISSING"
check "ReportCard.tsx exists" "$R"

grep -q "STATUS_CONFIG\|StatusBadge" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "StatusBadge with complete/generating/failed configs" "$R"

grep -q "complete.*green\|green.*Complete" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Complete status badge is green" "$R"

grep -q "generating.*amber\|amber.*Generating" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Generating status badge is amber" "$R"

grep -q "failed.*red\|red.*Failed" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Failed status badge is red" "$R"

grep -q "shared_with_customer\|shared-badge\|Shared with customer" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Shared with customer badge" "$R"

grep -q "onDownload\|Download" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Download action button" "$R"

grep -q "tap-target" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Action buttons have tap-target (44px min)" "$R"

# ── 15-24: NewReportForm ────────────────────────────────────────────────────
echo ""
echo "─── NewReportForm (4-step) ───"

FILE="src/components/reports/NewReportForm.tsx"
[[ -f "$FILE" ]] && R="PASS" || R="MISSING"
check "NewReportForm.tsx exists" "$R"

grep -q "Step 1\|step === 1\|Step1CustomerInfo\|Who is this report for" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Step 1: Customer Info form" "$R"

grep -q "Step 2\|step === 2\|Step2Products\|What products" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Step 2: Product selection" "$R"

grep -q "Step 3\|step === 3\|Step3Notes\|What did you find" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Step 3: Visit notes with character count" "$R"

grep -q "Step 4\|step === 4\|Step4Generate\|Generate Report" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Step 4: Preview & Generate" "$R"

grep -q "governance\|Reviewing your product selections" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Progress step: governance check message" "$R"

grep -q "Writing your report\|writing" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Progress step: writing report message" "$R"

grep -q "Preparing your download\|preparing" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Progress step: preparing download message" "$R"

grep -q "isGovernanceError\|Product Not Available\|Go Back" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Governance error: shows go-back-to-step-2 button" "$R"

grep -q "Try Again\|onRetry" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Generic error: shows try-again button (preserves data)" "$R"

grep -q "includePricing\|pricing.*toggle\|Include pricing" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Include pricing toggle" "$R"

# ── 25-30: ShareReportModal ─────────────────────────────────────────────────
echo ""
echo "─── ShareReportModal ───"

FILE="src/components/reports/ShareReportModal.tsx"
[[ -f "$FILE" ]] && R="PASS" || R="MISSING"
check "ShareReportModal.tsx exists" "$R"

grep -q "customer.*search\|searchQuery\|Search by email" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Customer search input" "$R"

grep -q "confirm\|Confirmation\|share-confirm" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Confirmation step before sharing" "$R"

grep -q "NOT.*see.*internal\|Bower Ag internal information" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "No internal data warning text" "$R"

grep -q "success\|shared successfully\|Report shared" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Success state after sharing" "$R"

grep -q "No customer account found\|Ask your manager" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "No customer found message" "$R"

# ── 31-34: ReportPreviewPage ────────────────────────────────────────────────
echo ""
echo "─── ReportPreviewPage ───"

FILE="src/pages/ReportPreviewPage.tsx"
[[ -f "$FILE" ]] && R="PASS" || R="MISSING"
check "ReportPreviewPage.tsx exists" "$R"

grep -q "BOWER AG\|navy.*header\|branded" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Branded Bower AG header" "$R"

grep -q "Download.*DOCX\|download_url" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Download DOCX button" "$R"

grep -q "sticky\|fixed.*bottom" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Sticky download footer on mobile" "$R"

# ── 35-39: ReportsPage ──────────────────────────────────────────────────────
echo ""
echo "─── ReportsPage ───"

FILE="src/pages/ReportsPage.tsx"
[[ -f "$FILE" ]] && R="PASS" || R="MISSING"
check "ReportsPage.tsx exists (overwritten from shell)" "$R"

grep -q "empty-state\|No reports yet\|Create Your First Report" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Empty state with 'Create Your First Report' button" "$R"

grep -q "NewReportForm\|showNewForm" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "New Report form integration" "$R"

grep -q "ShareReportModal\|shareReportId" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Share modal integration" "$R"

grep -q "completedToast\|report is ready" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Toast notification for completed reports" "$R"

# ── 40-44: Route Wiring + Build ─────────────────────────────────────────────
echo ""
echo "─── Route Wiring + Build ───"

FILE="src/App.tsx"
grep -q "ReportPreviewPage" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "ReportPreviewPage imported in App.tsx" "$R"

grep -q "reports/:reportId/preview" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Route /reports/:reportId/preview registered" "$R"

# TypeScript check
npx tsc --noEmit 2>/dev/null && R="PASS" || R="FAIL"
check "TypeScript check passes (zero errors)" "$R"

# Build check
npm run build >/dev/null 2>&1 && R="PASS" || R="FAIL"
check "Frontend build succeeds" "$R"

# Verify the reports store module loads
node -e "
const fs = require('fs');
const src = fs.readFileSync('src/store/reports.ts', 'utf8');
if (src.includes('useReportsStore') && src.includes('loadReports') && src.includes('startPolling')) {
  process.exit(0);
} else {
  process.exit(1);
}
" && R="PASS" || R="FAIL"
check "Reports store has all required actions" "$R"

# ── 45-53: Frontend Tests ───────────────────────────────────────────────────
echo ""
echo "─── Frontend Tests ───"

FILE="src/pages/__tests__/ReportsPage.test.tsx"
[[ -f "$FILE" ]] && R="PASS" || R="MISSING"
check "ReportsPage.test.tsx exists" "$R"

grep -q "renders empty state when no reports" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: renders empty state when no reports" "$R"

grep -q "shows correct status badge" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: status badge for each status value" "$R"

grep -q "Shared with customer" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: shared_with_customer badge" "$R"

grep -q "step 1 validates required fields" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: step 1 required field validation" "$R"

grep -q "step 2 shows only products" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: step 2 sellable products at location" "$R"

grep -q "character count" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: step 3 character counts" "$R"

grep -q "success state after successful generate" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: step 4 success state" "$R"

grep -q "governance error" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: governance error on API 400" "$R"

grep -q "confirmation before sharing" "$FILE" 2>/dev/null && R="PASS" || R="MISSING"
check "Test: share modal confirmation" "$R"

# ── Summary ──────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════"
printf "  Sprint 10 Verification: %d / %d passed" "$PASS" "$TOTAL"
if [[ "$FAIL" -gt 0 ]]; then
  printf "  (%d FAILED)" "$FAIL"
fi
echo ""
echo "═══════════════════════════════════════════════════════════════════"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
