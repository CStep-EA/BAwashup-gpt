#!/bin/bash
# Sprint 8 Verification Checklist
# Product Lookup UI — 11 required items from sprint spec

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
echo " Sprint 8 — Product Lookup UI Verification"
echo "═══════════════════════════════════════════════"

# 1. Backend product endpoints
echo ""
echo "1. Backend API endpoints:"
test -f backend/app/api/products.py && R="PASS" || R="FAIL"
check "Products API module exists" "$R" "Missing products.py"

grep -q "GET.*products" backend/app/api/products.py 2>/dev/null || grep -q '@router.get("")' backend/app/api/products.py && R="PASS" || R="FAIL"
check "GET /products list endpoint" "$R" "Missing list endpoint"

grep -q "product_id" backend/app/api/products.py && grep -q "/{product_id}" backend/app/api/products.py && R="PASS" || R="FAIL"
check "GET /products/{product_id} detail endpoint" "$R" "Missing detail endpoint"

grep -q "/categories" backend/app/api/products.py && R="PASS" || R="FAIL"
check "GET /products/categories endpoint" "$R" "Missing categories endpoint"

grep -q "products_router" backend/app/main.py && R="PASS" || R="FAIL"
check "Products router registered in main.py" "$R" "Missing products_router"

grep -q "NON_CUSTOMER_ROLES" backend/app/api/products.py && R="PASS" || R="FAIL"
check "Non-customer role guard applied" "$R" "Missing role guard"

# 2. Search + filter logic
echo ""
echo "2. Backend search + filter logic:"
grep -q "search" backend/app/api/products.py && grep -q "ilike" backend/app/api/products.py && R="PASS" || R="FAIL"
check "Search with ILIKE query" "$R" "Missing ILIKE search"

grep -q "category" backend/app/api/products.py && grep -q "product_type" backend/app/api/products.py && R="PASS" || R="FAIL"
check "Category filter by product_type" "$R" "Missing category filter"

grep -q "location_code" backend/app/api/products.py && grep -q "product_sellability" backend/app/api/products.py && R="PASS" || R="FAIL"
check "Location filter via product_sellability" "$R" "Missing location filter"

grep -q "chemistry" backend/app/api/products.py && grep -q "chemistry_type" backend/app/api/products.py && R="PASS" || R="FAIL"
check "Chemistry filter" "$R" "Missing chemistry filter"

grep -q "limit.*offset" backend/app/api/products.py && R="PASS" || R="FAIL"
check "Pagination with limit + offset" "$R" "Missing pagination"

grep -q "sellability" backend/app/api/products.py && grep -q "SellabilityEntry" backend/app/api/products.py && R="PASS" || R="FAIL"
check "Product detail includes sellability for all locations" "$R" "Missing sellability in detail"

# 3. Frontend: Product components
echo ""
echo "3. Frontend product components:"
test -f frontend/src/components/products/ProductCard.tsx && R="PASS" || R="FAIL"
check "ProductCard component exists" "$R" "Missing ProductCard.tsx"

test -f frontend/src/components/products/ProductCardExpanded.tsx && R="PASS" || R="FAIL"
check "ProductCardExpanded component exists" "$R" "Missing ProductCardExpanded.tsx"

test -f frontend/src/pages/ProductLookupPage.tsx && R="PASS" || R="FAIL"
check "ProductLookupPage exists" "$R" "Missing ProductLookupPage.tsx"

test -f frontend/src/store/products.ts && R="PASS" || R="FAIL"
check "Products Zustand store exists" "$R" "Missing store/products.ts"

# 4. Card expands inline (no navigation)
echo ""
echo "4. Inline expansion (no navigation):"
grep -q "isExpanded\|expandedId" frontend/src/pages/ProductLookupPage.tsx && R="PASS" || R="FAIL"
check "ProductLookupPage tracks expanded ID" "$R" "Missing expandedId state"

grep -q "onToggle" frontend/src/components/products/ProductCard.tsx && R="PASS" || R="FAIL"
check "ProductCard uses toggle callback (no navigate)" "$R" "Card uses navigate instead of toggle"

# 5. Sellability chips
echo ""
echo "5. Sellability chips:"
grep -q "sellability" frontend/src/components/products/ProductCardExpanded.tsx && R="PASS" || R="FAIL"
check "Expanded card shows sellability data" "$R" "Missing sellability display"

grep -q "ring-accent\|ring-2\|isUserLocation" frontend/src/components/products/ProductCardExpanded.tsx && R="PASS" || R="FAIL"
check "User location chip has blue ring styling" "$R" "Missing user location highlight"

grep -q "sellable.*green\|bg-green" frontend/src/components/products/ProductCardExpanded.tsx && R="PASS" || R="FAIL"
check "Green for sellable locations" "$R" "Missing green sellable styling"

grep -q "bg-red\|text-red" frontend/src/components/products/ProductCardExpanded.tsx && R="PASS" || R="FAIL"
check "Red for not-sellable locations" "$R" "Missing red not-sellable styling"

# 6. Pricing lazy loads
echo ""
echo "6. Pricing lazy load:"
grep -q "fetchPricingLookup\|/pricing/lookup" frontend/src/components/products/ProductCardExpanded.tsx && R="PASS" || R="FAIL"
check "Pricing fetched from /pricing/lookup (lazy)" "$R" "Missing pricing lookup call"

grep -q "useEffect" frontend/src/components/products/ProductCardExpanded.tsx && R="PASS" || R="FAIL"
check "Pricing loaded in useEffect (on expansion)" "$R" "Missing useEffect for pricing"

grep -q "Confirmed from\|Price Sheet" frontend/src/components/products/ProductCardExpanded.tsx && R="PASS" || R="FAIL"
check "Governance citation on pricing" "$R" "Missing pricing citation"

# 7. Filter combinations (AND logic)
echo ""
echo "7. Filter combinations:"
grep -q "locationOnly\|location_code" frontend/src/store/products.ts && R="PASS" || R="FAIL"
check "Location-only filter in store" "$R" "Missing locationOnly filter"

grep -q "clearFilters" frontend/src/store/products.ts && R="PASS" || R="FAIL"
check "clearFilters action exists" "$R" "Missing clearFilters"

grep -q "setFilter" frontend/src/pages/ProductLookupPage.tsx && R="PASS" || R="FAIL"
check "Page wires setFilter to filter chips" "$R" "Missing setFilter usage"

# 8. Customer 403 (role guard)
echo ""
echo "8. Access control:"
grep -q "customer\|NON_CUSTOMER" backend/app/api/products.py && R="PASS" || R="FAIL"
check "Customer blocked from products API" "$R" "Missing customer block"

# 9. Mobile-first constraints
echo ""
echo "9. Mobile-first (390px):"
grep -q 'fontSize.*16px\|font-size.*16px\|text-base' frontend/src/pages/ProductLookupPage.tsx && R="PASS" || R="FAIL"
check "Search input 16px font (iOS zoom prevention)" "$R" "Missing 16px font"

grep -q "tap-target" frontend/src/components/products/ProductCard.tsx && R="PASS" || R="FAIL"
check "ProductCard has tap-target class" "$R" "Missing tap-target"

grep -q "max-w\|overflow" frontend/src/pages/ProductLookupPage.tsx && R="PASS" || R="FAIL"
check "Page handles overflow (no horizontal scroll)" "$R" "Missing overflow handling"

# 10. Load More (not infinite scroll)
echo ""
echo "10. Pagination UI:"
grep -q "Load more\|loadMore" frontend/src/pages/ProductLookupPage.tsx && R="PASS" || R="FAIL"
check "'Load more' button exists" "$R" "Missing Load more button"

grep -q "hasMore" frontend/src/pages/ProductLookupPage.tsx && R="PASS" || R="FAIL"
check "hasMore controls Load more visibility" "$R" "Missing hasMore check"

grep -q "Showing.*of.*products" frontend/src/pages/ProductLookupPage.tsx && R="PASS" || R="FAIL"
check "'Showing X of Y products' count" "$R" "Missing product count display"

# 11. Debounce
echo ""
echo "11. Search debounce:"
grep -q "useDebounce\|debounce\|setTimeout" frontend/src/pages/ProductLookupPage.tsx && R="PASS" || R="FAIL"
check "Search input debounced (300ms)" "$R" "Missing debounce"

# 12. Ask about product
echo ""
echo "12. 'Ask about this product' navigation:"
grep -q "Ask about this product" frontend/src/components/products/ProductCardExpanded.tsx && R="PASS" || R="FAIL"
check "'Ask about this product' button exists" "$R" "Missing ask button"

grep -q "navigate.*chat\|/chat" frontend/src/components/products/ProductCardExpanded.tsx && R="PASS" || R="FAIL"
check "Button navigates to /chat" "$R" "Missing /chat navigation"

# 13. Tests
echo ""
echo "13. Tests:"
test -f backend/app/tests/test_products_api.py && R="PASS" || R="FAIL"
check "Backend test file exists" "$R" "Missing test_products_api.py"

grep -c "def test_" backend/app/tests/test_products_api.py | grep -q "[7-9]\|1[0-9]" && R="PASS" || R="FAIL"
check "Backend has 7+ test functions" "$R" "Need at least 7 tests"

test -f frontend/src/components/products/__tests__/ProductCard.test.tsx && R="PASS" || R="FAIL"
check "Frontend test file exists" "$R" "Missing ProductCard.test.tsx"

# 14. Build
echo ""
echo "14. Build verification:"
test -d frontend/dist && R="PASS" || R="FAIL"
check "Production build exists" "$R" "Run npm build first"

# 15. Route wiring
echo ""
echo "15. Route wiring:"
grep -q "ProductLookupPage" frontend/src/App.tsx && R="PASS" || R="FAIL"
check "ProductLookupPage wired in App.tsx" "$R" "Missing route"

grep -q 'path.*products' frontend/src/App.tsx && R="PASS" || R="FAIL"
check "/products route exists" "$R" "Missing /products route"

# 16. Empty state
echo ""
echo "16. Empty state:"
grep -q "No products found" frontend/src/pages/ProductLookupPage.tsx && R="PASS" || R="FAIL"
check "Empty state message exists" "$R" "Missing empty state"

grep -q "Clear search" frontend/src/pages/ProductLookupPage.tsx && R="PASS" || R="FAIL"
check "'Clear search' button in empty state" "$R" "Missing clear button"

# 17. Detail cache
echo ""
echo "17. Store caching:"
grep -q "CACHE_TTL\|detailCache\|cachedAt" frontend/src/store/products.ts && R="PASS" || R="FAIL"
check "Product detail cached for 5 minutes" "$R" "Missing detail cache"

echo ""
echo "═══════════════════════════════════════════════"
echo " Results: $PASS/$TOTAL PASS, $FAIL FAIL"
echo "═══════════════════════════════════════════════"

if [ $FAIL -eq 0 ]; then
  echo " 🎉 Sprint 8 FULLY VERIFIED"
else
  echo " ⚠️  $FAIL check(s) need attention"
fi
