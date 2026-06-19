#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# verify_sprint12.sh — Bower Ag CowCare Tool Sprint 12 Verification
# Admin Portal Frontend — 65 checks
# ──────────────────────────────────────────────────────────────────────────────
set -uo pipefail
PASS=0; FAIL=0
check() { if eval "$2" >/dev/null 2>&1; then echo "  ✅  $1"; PASS=$((PASS + 1)); else echo "  ❌  $1"; FAIL=$((FAIL + 1)); fi; }

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " Sprint 12 — Admin Portal Frontend Verification"
echo "═══════════════════════════════════════════════════════════════"

# ── 1. Admin API Types & Functions (api.ts) ─────────────────────────────────
echo ""
echo "── 1. Admin API Types & Functions ──"
check "AnalyticsSummary type exists" "grep -q 'export interface AnalyticsSummary' frontend/src/lib/api.ts"
check "TopProduct type exists" "grep -q 'export interface TopProduct' frontend/src/lib/api.ts"
check "DailyUsage type exists" "grep -q 'export interface DailyUsage' frontend/src/lib/api.ts"
check "AdminUserItem type exists" "grep -q 'export interface AdminUserItem' frontend/src/lib/api.ts"
check "ConfigItem type exists" "grep -q 'export interface ConfigItem' frontend/src/lib/api.ts"
check "AdminBugReport type exists" "grep -q 'export interface AdminBugReport' frontend/src/lib/api.ts"
check "VersionLogItem type exists" "grep -q 'export interface VersionLogItem' frontend/src/lib/api.ts"
check "AuditLogEntry type exists" "grep -q 'export interface AuditLogEntry' frontend/src/lib/api.ts"
check "fetchAnalyticsSummary function" "grep -q 'export async function fetchAnalyticsSummary' frontend/src/lib/api.ts"
check "fetchTopProducts function" "grep -q 'export async function fetchTopProducts' frontend/src/lib/api.ts"
check "fetchUsageByDay function" "grep -q 'export async function fetchUsageByDay' frontend/src/lib/api.ts"
check "fetchAdminUsers function" "grep -q 'export async function fetchAdminUsers' frontend/src/lib/api.ts"
check "inviteUser function" "grep -q 'export async function inviteUser' frontend/src/lib/api.ts"
check "updateUser function" "grep -q 'export async function updateUser' frontend/src/lib/api.ts"
check "deactivateUser function" "grep -q 'export async function deactivateUser' frontend/src/lib/api.ts"
check "fetchAdminConfig function" "grep -q 'export async function fetchAdminConfig' frontend/src/lib/api.ts"
check "updateConfig function" "grep -q 'export async function updateConfig' frontend/src/lib/api.ts"
check "fetchAdminBugs function" "grep -q 'export async function fetchAdminBugs' frontend/src/lib/api.ts"
check "fetchAdminBugDetail function" "grep -q 'export async function fetchAdminBugDetail' frontend/src/lib/api.ts"
check "updateAdminBug function" "grep -q 'export async function updateAdminBug' frontend/src/lib/api.ts"
check "getAdminBugsExportUrl function" "grep -q 'export function getAdminBugsExportUrl' frontend/src/lib/api.ts"
check "fetchAdminVersions function" "grep -q 'export async function fetchAdminVersions' frontend/src/lib/api.ts"
check "createVersion function" "grep -q 'export async function createVersion' frontend/src/lib/api.ts"
check "fetchAuditLog function" "grep -q 'export async function fetchAuditLog' frontend/src/lib/api.ts"
check "getAuditExportUrl function" "grep -q 'export function getAuditExportUrl' frontend/src/lib/api.ts"

# ── 2. AdminDashboard Page ──────────────────────────────────────────────────
echo ""
echo "── 2. AdminDashboard ──"
check "AdminDashboard file exists" "test -f frontend/src/pages/admin/AdminDashboard.tsx"
check "Uses fetchAnalyticsSummary" "grep -q 'fetchAnalyticsSummary' frontend/src/pages/admin/AdminDashboard.tsx"
check "Uses fetchTopProducts" "grep -q 'fetchTopProducts' frontend/src/pages/admin/AdminDashboard.tsx"
check "Uses fetchUsageByDay" "grep -q 'fetchUsageByDay' frontend/src/pages/admin/AdminDashboard.tsx"
check "LineChart import (Recharts)" "grep -q 'LineChart' frontend/src/pages/admin/AdminDashboard.tsx"
check "BarChart import (Recharts)" "grep -q 'BarChart' frontend/src/pages/admin/AdminDashboard.tsx"
check "Date range selector (7d/14d/30d/90d)" "grep -q 'DATE_RANGES' frontend/src/pages/admin/AdminDashboard.tsx"
check "8 MetricCard components" "grep -c 'MetricCard' frontend/src/pages/admin/AdminDashboard.tsx | grep -qE '^(9|[1-9][0-9])'"

# ── 3. AdminUsers Page ──────────────────────────────────────────────────────
echo ""
echo "── 3. AdminUsers ──"
check "AdminUsers file exists" "test -f frontend/src/pages/admin/AdminUsers.tsx"
check "Uses fetchAdminUsers" "grep -q 'fetchAdminUsers' frontend/src/pages/admin/AdminUsers.tsx"
check "Uses inviteUser" "grep -q 'inviteUser' frontend/src/pages/admin/AdminUsers.tsx"
check "Uses deactivateUser" "grep -q 'deactivateUser' frontend/src/pages/admin/AdminUsers.tsx"
check "Role badges (ROLE_COLORS)" "grep -q 'ROLE_COLORS' frontend/src/pages/admin/AdminUsers.tsx"
check "Invite modal" "grep -q 'inviteOpen' frontend/src/pages/admin/AdminUsers.tsx"
check "Edit modal" "grep -q 'editUser' frontend/src/pages/admin/AdminUsers.tsx"
check "Deactivate dialog" "grep -q 'deactivateTarget' frontend/src/pages/admin/AdminUsers.tsx"

# ── 4. AdminConfig Page ─────────────────────────────────────────────────────
echo ""
echo "── 4. AdminConfig ──"
check "AdminConfig file exists" "test -f frontend/src/pages/admin/AdminConfig.tsx"
check "Uses fetchAdminConfig" "grep -q 'fetchAdminConfig' frontend/src/pages/admin/AdminConfig.tsx"
check "Uses updateConfig" "grep -q 'updateConfig' frontend/src/pages/admin/AdminConfig.tsx"
check "editable_by guard (canEdit)" "grep -q 'canEdit' frontend/src/pages/admin/AdminConfig.tsx"
check "Maintenance mode confirmation" "grep -q 'maintenanceConfirm' frontend/src/pages/admin/AdminConfig.tsx"
check "Toggle components" "grep -q 'ToggleLeft\|ToggleRight' frontend/src/pages/admin/AdminConfig.tsx"

# ── 5. AdminBugs Page ───────────────────────────────────────────────────────
echo ""
echo "── 5. AdminBugs ──"
check "AdminBugs file exists" "test -f frontend/src/pages/admin/AdminBugs.tsx"
check "Uses fetchAdminBugs" "grep -q 'fetchAdminBugs' frontend/src/pages/admin/AdminBugs.tsx"
check "Uses updateAdminBug" "grep -q 'updateAdminBug' frontend/src/pages/admin/AdminBugs.tsx"
check "Severity badges (SEVERITY_COLORS)" "grep -q 'SEVERITY_COLORS' frontend/src/pages/admin/AdminBugs.tsx"
check "Detail panel (selectedBug)" "grep -q 'selectedBug' frontend/src/pages/admin/AdminBugs.tsx"
check "CSV export" "grep -q 'getAdminBugsExportUrl' frontend/src/pages/admin/AdminBugs.tsx"

# ── 6. AdminVersions Page ───────────────────────────────────────────────────
echo ""
echo "── 6. AdminVersions ──"
check "AdminVersions file exists" "test -f frontend/src/pages/admin/AdminVersions.tsx"
check "Uses fetchAdminVersions" "grep -q 'fetchAdminVersions' frontend/src/pages/admin/AdminVersions.tsx"
check "Uses createVersion" "grep -q 'createVersion' frontend/src/pages/admin/AdminVersions.tsx"
check "Accordion (VersionAccordionItem)" "grep -q 'VersionAccordionItem' frontend/src/pages/admin/AdminVersions.tsx"
check "org_admin check for create" "grep -q 'isOrgAdmin' frontend/src/pages/admin/AdminVersions.tsx"
check "CSV export" "grep -q 'getVersionsExportUrl' frontend/src/pages/admin/AdminVersions.tsx"

# ── 7. AuditLogPage ─────────────────────────────────────────────────────────
echo ""
echo "── 7. AuditLogPage ──"
check "AuditLogPage file exists" "test -f frontend/src/pages/admin/AuditLogPage.tsx"
check "Uses fetchAuditLog" "grep -q 'fetchAuditLog' frontend/src/pages/admin/AuditLogPage.tsx"
check "Uses getAuditExportUrl" "grep -q 'getAuditExportUrl' frontend/src/pages/admin/AuditLogPage.tsx"
check "Filter controls" "grep -q 'showFilters' frontend/src/pages/admin/AuditLogPage.tsx"

# ── 8. Routing & Navigation ─────────────────────────────────────────────────
echo ""
echo "── 8. Routing & Navigation ──"
check "AuditLogPage imported in App.tsx" "grep -q 'AuditLogPage' frontend/src/App.tsx"
check "Audit route in App.tsx" "grep -q 'admin/audit' frontend/src/App.tsx"
check "Audit nav in Sidebar" "grep -q 'admin/audit' frontend/src/components/layout/Sidebar.tsx"
check "orgAdminOnly filter in Sidebar" "grep -q 'orgAdminOnly' frontend/src/components/layout/Sidebar.tsx"

# ── 9. Tests ────────────────────────────────────────────────────────────────
echo ""
echo "── 9. Tests ──"
check "Test file exists" "test -f frontend/src/pages/admin/__tests__/AdminPortal.test.tsx"
check "11 test definitions" "grep -c 'test(' frontend/src/pages/admin/__tests__/AdminPortal.test.tsx | grep -q '11'"

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " Results: $PASS PASS / $FAIL FAIL / $((PASS + FAIL)) TOTAL"
echo "═══════════════════════════════════════════════════════════════"
if [ "$FAIL" -eq 0 ]; then
  echo " 🎉 All Sprint 12 checks passed!"
else
  echo " ⚠️  $FAIL check(s) failed."
fi
echo ""
