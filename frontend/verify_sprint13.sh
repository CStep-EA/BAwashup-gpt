#!/usr/bin/env bash
# Sprint 13 — Customer Portal verification script
# Checks all deliverables for Sprint 13

set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

check() {
  TOTAL=$((TOTAL + 1))
  if eval "$2" > /dev/null 2>&1; then
    echo "  ✅ $1"
    PASS=$((PASS + 1))
  else
    echo "  ❌ $1"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Sprint 13 — Customer Portal Verification"
echo "═══════════════════════════════════════════════════════════════"

# ─── Customer API Types (api.ts) ────────────────────────────────────
echo ""
echo "── Customer API Types ──────────────────────────"

check "CustomerReportSummary type exists" \
  "grep -q 'export interface CustomerReportSummary' src/lib/api.ts"

check "CustomerReportDetail type exists" \
  "grep -q 'export interface CustomerReportDetail' src/lib/api.ts"

check "CustomerReportSummary has report_id field" \
  "grep -A5 'interface CustomerReportSummary' src/lib/api.ts | grep -q 'report_id'"

check "CustomerReportSummary has has_download field" \
  "grep -A10 'interface CustomerReportSummary' src/lib/api.ts | grep -q 'has_download'"

check "CustomerReportDetail has report_content field" \
  "grep -A10 'interface CustomerReportDetail' src/lib/api.ts | grep -q 'report_content'"

check "CustomerReportDetail has download_url field" \
  "grep -A10 'interface CustomerReportDetail' src/lib/api.ts | grep -q 'download_url'"

check "fetchCustomerReports function exists" \
  "grep -q 'export async function fetchCustomerReports' src/lib/api.ts"

check "fetchCustomerReportDetail function exists" \
  "grep -q 'export async function fetchCustomerReportDetail' src/lib/api.ts"

check "Customer API calls /customer/reports endpoint" \
  "grep -q \"'/customer/reports'\" src/lib/api.ts"

# ─── CustomerLayout ──────────────────────────────────────────────────
echo ""
echo "── CustomerLayout ──────────────────────────────"

check "CustomerLayout.tsx exists" \
  "test -f src/layouts/CustomerLayout.tsx"

check "CustomerLayout exports named function" \
  "grep -q 'export function CustomerLayout' src/layouts/CustomerLayout.tsx"

check "CustomerLayout renders Outlet" \
  "grep -q '<Outlet' src/layouts/CustomerLayout.tsx"

check "CustomerLayout does NOT import Sidebar" \
  "! grep -q 'Sidebar' src/layouts/CustomerLayout.tsx"

check "CustomerLayout does NOT import BottomNav" \
  "! grep -q 'BottomNav' src/layouts/CustomerLayout.tsx"

check "CustomerLayout has sign-out button" \
  "grep -q 'customer-sign-out' src/layouts/CustomerLayout.tsx"

check "CustomerLayout has Bower Ag branding" \
  "grep -q 'Bower Ag' src/layouts/CustomerLayout.tsx"

check "CustomerLayout has footer with contact info" \
  "grep -q 'Contact your Bower Ag representative' src/layouts/CustomerLayout.tsx"

check "CustomerLayout shows customer_operation" \
  "grep -q 'customer_operation' src/layouts/CustomerLayout.tsx"

# ─── CustomerReportsPage ────────────────────────────────────────────
echo ""
echo "── CustomerReportsPage ─────────────────────────"

check "CustomerReportsPage.tsx exists" \
  "test -f src/pages/customer/CustomerReportsPage.tsx"

check "CustomerReportsPage has warm welcome" \
  "grep -q 'Welcome back' src/pages/customer/CustomerReportsPage.tsx"

check "CustomerReportsPage has empty state" \
  "grep -q 'customer-reports-empty' src/pages/customer/CustomerReportsPage.tsx"

check "CustomerReportsPage has loading skeleton" \
  "grep -q 'customer-reports-loading' src/pages/customer/CustomerReportsPage.tsx"

check "CustomerReportsPage has error state with retry" \
  "grep -q 'customer-reports-error' src/pages/customer/CustomerReportsPage.tsx"

check "CustomerReportsPage uses fetchCustomerReports" \
  "grep -q 'fetchCustomerReports' src/pages/customer/CustomerReportsPage.tsx"

check "CustomerReportsPage navigates to /my-reports/:id" \
  "grep -q '/my-reports/' src/pages/customer/CustomerReportsPage.tsx"

# ─── CustomerReportCard ─────────────────────────────────────────────
echo ""
echo "── CustomerReportCard ──────────────────────────"

check "CustomerReportCard.tsx exists" \
  "test -f src/components/customer/CustomerReportCard.tsx"

check "CustomerReportCard shows operation name" \
  "grep -q 'report-operation-name' src/components/customer/CustomerReportCard.tsx"

check "CustomerReportCard shows rep name" \
  "grep -q 'Prepared by' src/components/customer/CustomerReportCard.tsx"

check "CustomerReportCard has view button" \
  "grep -q 'View Report' src/components/customer/CustomerReportCard.tsx"

check "CustomerReportCard has download hint" \
  "grep -q 'download-hint' src/components/customer/CustomerReportCard.tsx"

# ─── CustomerReportViewPage ─────────────────────────────────────────
echo ""
echo "── CustomerReportViewPage ──────────────────────"

check "CustomerReportViewPage.tsx exists" \
  "test -f src/pages/customer/CustomerReportViewPage.tsx"

check "CustomerReportViewPage has back button" \
  "grep -q 'report-view-back' src/pages/customer/CustomerReportViewPage.tsx"

check "CustomerReportViewPage has report title" \
  "grep -q 'report-view-title' src/pages/customer/CustomerReportViewPage.tsx"

check "CustomerReportViewPage has section parser" \
  "grep -q 'parseReportSections' src/pages/customer/CustomerReportViewPage.tsx"

check "CustomerReportViewPage has sticky download bar" \
  "grep -q 'report-download-bar' src/pages/customer/CustomerReportViewPage.tsx"

check "CustomerReportViewPage has download button" \
  "grep -q 'Download Full Report' src/pages/customer/CustomerReportViewPage.tsx"

check "CustomerReportViewPage has loading state" \
  "grep -q 'report-view-loading' src/pages/customer/CustomerReportViewPage.tsx"

check "CustomerReportViewPage has error state" \
  "grep -q 'report-view-error' src/pages/customer/CustomerReportViewPage.tsx"

check "CustomerReportViewPage uses fetchCustomerReportDetail" \
  "grep -q 'fetchCustomerReportDetail' src/pages/customer/CustomerReportViewPage.tsx"

# ─── App.tsx Route Wiring ────────────────────────────────────────────
echo ""
echo "── App.tsx Route Wiring ────────────────────────"

check "App.tsx imports CustomerLayout" \
  "grep -q \"import { CustomerLayout }\" src/App.tsx"

check "App.tsx imports CustomerReportsPage" \
  "grep -q \"import { CustomerReportsPage }\" src/App.tsx"

check "App.tsx imports CustomerReportViewPage" \
  "grep -q \"import { CustomerReportViewPage }\" src/App.tsx"

check "App.tsx has /my-reports route" \
  "grep -q 'my-reports' src/App.tsx"

check "App.tsx has /my-reports/:reportId route" \
  "grep -q 'my-reports/:reportId' src/App.tsx"

check "App.tsx wraps customer routes in CustomerLayout" \
  "grep -q '<CustomerLayout' src/App.tsx"

check "Settings route is inside CustomerGuard (staff only)" \
  "awk '/CustomerGuard/,/\/Route>/{if(/SettingsPage/) found=1} END{exit !found}' src/App.tsx"

# ─── Backend: customer_reports.py ────────────────────────────────────
echo ""
echo "── Backend: customer_reports.py ─────────────────"

BE="../backend/app/api/customer_reports.py"

check "customer_reports.py exists" \
  "test -f $BE"

check "customer_reports.py has router prefix /customer" \
  "grep -q 'prefix=\"/customer\"' $BE"

check "customer_reports.py requires customer role" \
  "grep -q 'require_role.*customer' $BE"

check "GET /reports endpoint exists" \
  "grep -q '@router.get(\"/reports\"' $BE"

check "GET /reports/{report_id} endpoint exists" \
  "grep -q '@router.get(\"/reports/{report_id}\"' $BE"

check "Filters by shared_with_customer" \
  "grep -q 'shared_with_customer' $BE"

check "Filters by shared_with_user_ids" \
  "grep -q 'shared_with_user_ids' $BE"

check "Generates presigned URL" \
  "grep -q 'get_presigned_url' $BE"

check "Fires audit for list_reports" \
  "grep -q 'customer.list_reports' $BE"

check "Fires audit for view_report" \
  "grep -q 'customer.view_report' $BE"

check "CustomerReportSummary model has no location_code" \
  "! grep -A10 'class CustomerReportSummary' $BE | grep -q 'location_code'"

check "CustomerReportDetail model has report_content" \
  "grep -A10 'class CustomerReportDetail' $BE | grep -q 'report_content'"

# ─── Backend: main.py registration ──────────────────────────────────
echo ""
echo "── Backend: main.py registration ────────────────"

check "main.py imports customer_reports router" \
  "grep -q 'customer_reports' ../backend/app/main.py"

check "main.py includes customer_reports_router" \
  "grep -q 'customer_reports_router' ../backend/app/main.py"

# ─── Backend tests ──────────────────────────────────────────────────
echo ""
echo "── Backend tests ────────────────────────────────"

check "test_customer_portal.py exists" \
  "test -f ../backend/app/tests/test_customer_portal.py"

check "Test: customer list reports" \
  "grep -q 'test_customer_list_reports_returns_shared' ../backend/app/tests/test_customer_portal.py"

check "Test: consultant blocked from customer endpoint" \
  "grep -q 'test_consultant_cannot_access_customer_endpoint' ../backend/app/tests/test_customer_portal.py"

check "Test: customer view shared report" \
  "grep -q 'test_customer_view_shared_report' ../backend/app/tests/test_customer_portal.py"

check "Test: customer blocked from unshared report" \
  "grep -q 'test_customer_cannot_view_unshared_report' ../backend/app/tests/test_customer_portal.py"

check "Test: consultant blocked from customer detail" \
  "grep -q 'test_consultant_cannot_access_customer_report_detail' ../backend/app/tests/test_customer_portal.py"

check "Test: report not found" \
  "grep -q 'test_customer_report_not_found' ../backend/app/tests/test_customer_portal.py"

# ─── Frontend tests ──────────────────────────────────────────────────
echo ""
echo "── Frontend tests ───────────────────────────────"

check "CustomerPortal.test.tsx exists" \
  "test -f src/pages/customer/__tests__/CustomerPortal.test.tsx"

check "Test: CustomerLayout branded header" \
  "grep -q 'renders branded header' src/pages/customer/__tests__/CustomerPortal.test.tsx"

check "Test: warm welcome" \
  "grep -q 'warm welcome' src/pages/customer/__tests__/CustomerPortal.test.tsx"

check "Test: report list count" \
  "grep -q 'renders report list with correct count' src/pages/customer/__tests__/CustomerPortal.test.tsx"

check "Test: empty state" \
  "grep -q 'shows empty state when no reports shared' src/pages/customer/__tests__/CustomerPortal.test.tsx"

check "Test: report card" \
  "grep -q 'displays operation name, rep name' src/pages/customer/__tests__/CustomerPortal.test.tsx"

check "Test: report content sections" \
  "grep -q 'renders report content with sections' src/pages/customer/__tests__/CustomerPortal.test.tsx"

check "Test: error state and retry" \
  "grep -q 'shows error state and retry' src/pages/customer/__tests__/CustomerPortal.test.tsx"

check "Test: back button navigation" \
  "grep -q 'back button that navigates' src/pages/customer/__tests__/CustomerPortal.test.tsx"

# ─── Summary ─────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Results: $PASS/$TOTAL passed, $FAIL failed"
echo "═══════════════════════════════════════════════════════════════"
echo ""

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
