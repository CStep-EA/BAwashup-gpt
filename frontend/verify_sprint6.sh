#!/bin/bash
# Sprint 6 Verification Checklist
# Tests structure, routing, guards, mobile-first, and PWA

PASS=0
FAIL=0
TOTAL=0

check() {
  TOTAL=$((TOTAL + 1))
  local desc="$1"
  local result="$2"
  if [ "$result" = "PASS" ]; then
    echo "  ✅ $desc"
    PASS=$((PASS + 1))
  else
    echo "  ❌ $desc -- $3"
    FAIL=$((FAIL + 1))
  fi
}

echo "═══════════════════════════════════════════════"
echo " Sprint 6 — React App Shell Verification"
echo "═══════════════════════════════════════════════"

# 1. Login page renders at 390px (no iOS zoom)
echo ""
echo "1. Login page mobile-first (390px):"
# Check for 16px font-size prevention
grep -q "font-size: 16px" frontend/src/index.css && R1="PASS" || R1="FAIL"
check "iOS zoom prevention (16px input font)" "$R1" "Missing font-size: 16px in index.css"

# Check login page has h-[52px] button
grep -q "h-\[52px\]" frontend/src/pages/LoginPage.tsx && R2="PASS" || R2="FAIL"
check "52px navy sign-in button" "$R2" "Missing h-[52px] in LoginPage.tsx"

# Check viewport meta prevents zoom
grep -q "maximum-scale=1.0" frontend/index.html && R3="PASS" || R3="FAIL"
check "Viewport maximum-scale=1.0" "$R3" "Missing maximum-scale in index.html"

# Check h-12 inputs (48px tap targets)
grep -q "h-12" frontend/src/pages/LoginPage.tsx && R4="PASS" || R4="FAIL"
check "48px+ input height (h-12)" "$R4" "Missing h-12 inputs"

# 2. Login redirects by role
echo ""
echo "2. Login redirects by role:"
grep -q "customer.*my-reports" frontend/src/pages/LoginPage.tsx && R5="PASS" || R5="FAIL"
check "Customer -> /my-reports redirect" "$R5" "Missing customer redirect logic"

grep -q "getLandingRoute" frontend/src/pages/LoginPage.tsx && R6="PASS" || R6="FAIL"
check "Role-based landing route function" "$R6" "Missing getLandingRoute"

# 3. Bottom nav visible at 390px, hidden at lg+
echo ""
echo "3. Bottom nav responsive:"
grep -q "lg:hidden" frontend/src/components/layout/BottomNav.tsx && R7="PASS" || R7="FAIL"
check "BottomNav hidden at lg+ (lg:hidden)" "$R7" "Missing lg:hidden"

grep -q "fixed bottom-0" frontend/src/components/layout/BottomNav.tsx && R8="PASS" || R8="FAIL"
check "BottomNav fixed at bottom" "$R8" "Missing fixed bottom-0"

# 4. Sidebar visible at lg+, hidden on mobile
echo ""
echo "4. Sidebar responsive:"
grep -q "hidden.*lg:flex" frontend/src/components/layout/Sidebar.tsx && R9="PASS" || R9="FAIL"
check "Sidebar hidden mobile, visible lg+ (hidden lg:flex)" "$R9" "Missing hidden lg:flex"

grep -q "w-64" frontend/src/components/layout/Sidebar.tsx && R10="PASS" || R10="FAIL"
check "Sidebar 256px width (w-64)" "$R10" "Missing w-64"

# 5. Admin routes return 403 (not redirect) for consultant
echo ""
echo "5. Admin route 403 behavior:"
grep -q "ForbiddenPage" frontend/src/components/guards/RoleGuard.tsx && R11="PASS" || R11="FAIL"
check "RoleGuard renders ForbiddenPage (not redirect)" "$R11" "Missing ForbiddenPage"

grep -q "allowedRoles.*org_admin.*admin" frontend/src/App.tsx && R12="PASS" || R12="FAIL"
check "Admin routes restricted to org_admin + admin" "$R12" "Missing admin role guard"

# 6. PWA installable
echo ""
echo "6. PWA configuration:"
test -f frontend/public/pwa-192x192.png && R13="PASS" || R13="FAIL"
check "PWA icon 192x192 exists" "$R13" "Missing pwa-192x192.png"

test -f frontend/public/pwa-512x512.png && R14="PASS" || R14="FAIL"
check "PWA icon 512x512 exists" "$R14" "Missing pwa-512x512.png"

test -f frontend/public/cow-icon.svg && R15="PASS" || R15="FAIL"
check "Cow icon SVG exists" "$R15" "Missing cow-icon.svg"

grep -q "registerType.*autoUpdate" frontend/vite.config.ts && R16="PASS" || R16="FAIL"
check "VitePWA autoUpdate registered" "$R16" "Missing autoUpdate in vite.config"

grep -q "display.*standalone" frontend/vite.config.ts && R17="PASS" || R17="FAIL"
check "PWA manifest display: standalone" "$R17" "Missing standalone in manifest"

grep -q "navigateFallback" frontend/vite.config.ts && R18="PASS" || R18="FAIL"
check "Workbox navigateFallback for SPA" "$R18" "Missing navigateFallback"

# 7. Skeleton loaders
echo ""
echo "7. Skeleton loaders on all pages:"
for page in DashboardPage ChatPage ProductsPage ReportsPage MyReportsPage SettingsPage; do
  grep -q "Skeleton" "frontend/src/pages/${page}.tsx" && R="PASS" || R="FAIL"
  check "${page} has skeleton loader" "$R" "Missing Skeleton import in ${page}"
done

# Admin pages
for page in AdminDashboard AdminUsers AdminConfig AdminBugs AdminVersions; do
  grep -q "Skeleton" "frontend/src/pages/admin/${page}.tsx" && R="PASS" || R="FAIL"
  check "${page} has skeleton loader" "$R" "Missing Skeleton import in ${page}"
done

# Build check
echo ""
echo "8. Build verification:"
test -d frontend/dist && R19="PASS" || R19="FAIL"
check "Production build exists (dist/)" "$R19" "Run 'npm run build' first"

test -f frontend/dist/sw.js && R20="PASS" || R20="FAIL"
check "Service worker generated (sw.js)" "$R20" "Missing sw.js in dist"

# Route guard structure
echo ""
echo "9. Three-tier route guards:"
test -f frontend/src/components/guards/AuthGuard.tsx && R21="PASS" || R21="FAIL"
check "AuthGuard exists" "$R21" "Missing AuthGuard.tsx"

test -f frontend/src/components/guards/RoleGuard.tsx && R22="PASS" || R22="FAIL"
check "RoleGuard exists" "$R22" "Missing RoleGuard.tsx"

test -f frontend/src/components/guards/CustomerGuard.tsx && R23="PASS" || R23="FAIL"
check "CustomerGuard exists" "$R23" "Missing CustomerGuard.tsx"

# Auth store
echo ""
echo "10. Auth store completeness:"
grep -q "signInWithPassword" frontend/src/store/auth.ts && R24="PASS" || R24="FAIL"
check "Auth store login via signInWithPassword" "$R24" "Missing signInWithPassword"

grep -q "onAuthStateChange" frontend/src/store/auth.ts && R25="PASS" || R25="FAIL"
check "Auth state change listener" "$R25" "Missing onAuthStateChange"

grep -q "BrowserRouter" frontend/src/main.tsx && R26="PASS" || R26="FAIL"
check "BrowserRouter in main.tsx" "$R26" "Missing BrowserRouter"

echo ""
echo "═══════════════════════════════════════════════"
echo " Results: $PASS/$TOTAL PASS, $FAIL FAIL"
echo "═══════════════════════════════════════════════"

if [ $FAIL -eq 0 ]; then
  echo " 🎉 Sprint 6 FULLY VERIFIED"
else
  echo " ⚠️  $FAIL check(s) need attention"
fi
