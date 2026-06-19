#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Sprint 11 — Admin Portal Backend Verification Script
# Checks all endpoint files, route registrations, role guards,
# test assertions, and structural requirements.
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
cd "$(dirname "$0")"

PASS=0
FAIL=0

check() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        printf "  ✅ %2d. %s\n" $((PASS + FAIL + 1)) "$desc"
        PASS=$((PASS + 1))
    else
        printf "  ❌ %2d. %s\n" $((PASS + FAIL + 1)) "$desc"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║           Sprint 11 — Admin Portal Backend                      ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"

# ─── Analytics Endpoints ───
echo ""
echo "─── Admin Analytics Endpoints ───"
check "admin_analytics.py exists" test -f app/api/admin_analytics.py
check "GET /admin/analytics/summary endpoint" grep -q "def analytics_summary" app/api/admin_analytics.py
check "GET /admin/analytics/top_products endpoint" grep -q "def top_products" app/api/admin_analytics.py
check "GET /admin/analytics/usage_by_day endpoint" grep -q "def usage_by_day" app/api/admin_analytics.py
check "Summary returns total_queries field" grep -q "total_queries" app/api/admin_analytics.py
check "Summary returns governance_blocks field" grep -q "governance_blocks" app/api/admin_analytics.py
check "Summary returns thumbs_up/thumbs_down" grep -q "thumbs_up" app/api/admin_analytics.py
check "Summary returns open_bugs count" grep -q "open_bugs" app/api/admin_analytics.py
check "Analytics uses ADMIN_ROLES guard" grep -q "require_role(ADMIN_ROLES)" app/api/admin_analytics.py
check "Top products uses ILIKE matching" grep -q "pname_lower in qt" app/api/admin_analytics.py

# ─── User Management Endpoints ───
echo ""
echo "─── Admin User Management Endpoints ───"
check "admin_users.py exists" test -f app/api/admin_users.py
check "GET /admin/users endpoint" grep -q "def list_users" app/api/admin_users.py
check "POST /admin/users/invite endpoint" grep -q "def invite_user" app/api/admin_users.py
check "PATCH /admin/users/{user_id} endpoint" grep -q "def update_user" app/api/admin_users.py
check "DELETE /admin/users/{user_id} endpoint" grep -q "def deactivate_user" app/api/admin_users.py
check "Guard: cannot create org_admin" grep -q 'role.*org_admin.*400\|org_admin.*400\|Cannot invite.*org_admin' app/api/admin_users.py
check "Guard: admin_manager cannot assign admin_manager" grep -q 'admin_manager.*cannot.*admin_manager\|Admin managers cannot invite' app/api/admin_users.py
check "Guard: cannot deactivate yourself" grep -q 'cannot deactivate your own\|Cannot deactivate your own' app/api/admin_users.py
check "Guard: org_admin users are immutable" grep -q 'immutable' app/api/admin_users.py
check "Invite uses fire_and_forget_audit" grep -q "fire_and_forget_audit" app/api/admin_users.py
check "Update logs before/after values" grep -q '"before"' app/api/admin_users.py
check "Deactivate bans in auth" grep -q "ban_duration" app/api/admin_users.py
check "Auth admin email join for list" grep -q "list_users" app/api/admin_users.py

# ─── System Config Endpoints ───
echo ""
echo "─── Admin Config Endpoints ───"
check "admin_config.py exists" test -f app/api/admin_config.py
check "GET /admin/config endpoint" grep -q "def list_config" app/api/admin_config.py
check "PATCH /admin/config/{key} endpoint" grep -q "def update_config" app/api/admin_config.py
check "editable_by guard enforced" grep -q "editable_by.*org_admin.*org_admin\|editable_by.*==.*org_admin" app/api/admin_config.py
check "Config update logs to audit" grep -q "config_updated" app/api/admin_config.py

# ─── Bug Report Endpoints ───
echo ""
echo "─── Admin Bug Report Endpoints ───"
check "admin_bugs.py exists" test -f app/api/admin_bugs.py
check "GET /admin/bugs endpoint" grep -q "def list_bugs" app/api/admin_bugs.py
check "GET /admin/bugs/{bug_id} endpoint" grep -q "def get_bug" app/api/admin_bugs.py
check "PATCH /admin/bugs/{bug_id} endpoint" grep -q "def update_bug" app/api/admin_bugs.py
check "GET /admin/bugs/export endpoint" grep -q "def export_bugs" app/api/admin_bugs.py
check "Resolve auto-sets resolved_at" grep -q "resolved_at" app/api/admin_bugs.py
check "CSV export is StreamingResponse" grep -q "StreamingResponse" app/api/admin_bugs.py
check "Sort by severity (critical first)" grep -q "SEVERITY_ORDER" app/api/admin_bugs.py
check "CSV has correct header columns" grep -q '"id", "title", "severity", "status", "reporter_name"' app/api/admin_bugs.py

# ─── Version Log Endpoints ───
echo ""
echo "─── Admin Version Log Endpoints ───"
check "admin_versions.py exists" test -f app/api/admin_versions.py
check "GET /admin/versions endpoint" grep -q "def list_versions" app/api/admin_versions.py
check "POST /admin/versions endpoint (org_admin only)" grep -q 'require_role.*org_admin' app/api/admin_versions.py
check "Version tag validation (vX.Y.Z)" grep -q 'v\\d.*\\d.*\\d' app/api/admin_versions.py
check "POST sets deployed_by" grep -q "deployed_by.*user.id" app/api/admin_versions.py
check "GET /admin/versions/export endpoint" grep -q "def export_versions" app/api/admin_versions.py
check "Version CSV is StreamingResponse" grep -q "StreamingResponse" app/api/admin_versions.py

# ─── Audit Log Endpoints ───
echo ""
echo "─── Admin Audit Log Endpoints (org_admin only) ───"
check "admin_audit.py exists" test -f app/api/admin_audit.py
check "GET /admin/audit endpoint" grep -q "def list_audit_logs" app/api/admin_audit.py
check "GET /admin/audit/export endpoint" grep -q "def export_audit_logs" app/api/admin_audit.py
check "Audit restricted to org_admin only" grep -q 'require_role.*org_admin' app/api/admin_audit.py
check "Audit returns user profile info" grep -q "user_name\|profiles_map" app/api/admin_audit.py
check "Audit CSV is StreamingResponse" grep -q "StreamingResponse" app/api/admin_audit.py

# ─── Router Registration ───
echo ""
echo "─── Router Registration in main.py ───"
check "admin_analytics_router imported" grep -q "admin_analytics_router" app/main.py
check "admin_users_router imported" grep -q "admin_users_router" app/main.py
check "admin_config_router imported" grep -q "admin_config_router" app/main.py
check "admin_bugs_router imported" grep -q "admin_bugs_router" app/main.py
check "admin_versions_router imported" grep -q "admin_versions_router" app/main.py
check "admin_audit_router imported" grep -q "admin_audit_router" app/main.py

# ─── Test File ───
echo ""
echo "─── Admin API Tests ───"
check "test_admin_api.py exists" test -f app/tests/test_admin_api.py
check "Test: analytics summary valid schema" grep -q "test_analytics_summary_returns_valid_schema" app/tests/test_admin_api.py
check "Test: analytics blocked for consultant" grep -q "test_analytics_blocked_for_consultant" app/tests/test_admin_api.py
check "Test: invite user success" grep -q "test_invite_user_success" app/tests/test_admin_api.py
check "Test: cannot invite org_admin" grep -q "test_cannot_invite_org_admin" app/tests/test_admin_api.py
check "Test: admin_manager cannot invite admin_manager" grep -q "test_admin_manager_cannot_invite_admin_manager" app/tests/test_admin_api.py
check "Test: cannot deactivate self" grep -q "test_cannot_deactivate_self" app/tests/test_admin_api.py
check "Test: cannot change org_admin role" grep -q "test_cannot_change_org_admin_role" app/tests/test_admin_api.py
check "Test: config list returns all keys" grep -q "test_config_list_returns_all_keys" app/tests/test_admin_api.py
check "Test: admin_manager cannot edit org_admin config" grep -q "test_admin_manager_cannot_edit_org_admin_only_config" app/tests/test_admin_api.py
check "Test: org_admin can edit any config" grep -q "test_org_admin_can_edit_any_config" app/tests/test_admin_api.py
check "Test: bug list returns results" grep -q "test_bug_list_returns_results" app/tests/test_admin_api.py
check "Test: bug resolve sets resolved_at" grep -q "test_bug_resolve_sets_resolved_at" app/tests/test_admin_api.py
check "Test: bug export returns CSV" grep -q "test_bug_export_returns_csv" app/tests/test_admin_api.py
check "Test: audit blocked for admin_manager" grep -q "test_audit_log_blocked_for_admin_manager" app/tests/test_admin_api.py
check "Test: audit accessible for org_admin" grep -q "test_audit_log_accessible_for_org_admin" app/tests/test_admin_api.py

# ─── Run Tests ───
echo ""
echo "─── Running pytest ───"
check "All admin API tests pass" python -m pytest app/tests/test_admin_api.py -q --tb=no

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  Sprint 11 Verification: $PASS / $((PASS + FAIL)) passed"
echo "═══════════════════════════════════════════════════════════════════"
