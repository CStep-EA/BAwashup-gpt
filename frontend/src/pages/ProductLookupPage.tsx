/**
 * ProductLookupPage — Full product catalog with governance-verified sellability and pricing.
 * Sprint 8: Mobile-first (390px), one-handed barn use, debounced search, inline expand.
 *
 * ⚠️ Pricing lazy-loads on card expand via /pricing/lookup — never on page load.
 * ⚠️ Filters are AND logic — all active filters apply simultaneously.
 * ⚠️ No horizontal scroll at 390px. Font-size 16px on inputs (iOS zoom prevention).
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { Search, X, SlidersHorizontal, Loader2 } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { ProductCard } from '@/components/products/ProductCard'
import { ProductCardExpanded } from '@/components/products/ProductCardExpanded'
import { useProductsStore } from '@/store/products'
import { useChatStore } from '@/store/chat'
import type { ProductDetailResponse } from '@/lib/api'

// ─── Debounce hook ───────────────────────────────────────────────────────────

function useDebounce(value: string, delay: number) {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return debounced
}

// ─── Filter Bar ──────────────────────────────────────────────────────────────

interface FilterBarProps {
  isOpen: boolean
  onToggle: () => void
}

function FilterBar({ isOpen, onToggle }: FilterBarProps) {
  const { filters, categories, setFilter, clearFilters } = useProductsStore()

  const activeCount = [filters.category, filters.chemistry, filters.locationOnly]
    .filter(Boolean).length

  const categoryOptions = [
    { value: null, label: 'All' },
    { value: 'teat_dip', label: 'Teat Dip' },
    { value: 'chemical', label: 'Chemical' },
    { value: 'cip', label: 'CIP' },
  ]

  return (
    <div className="space-y-2">
      {/* Filter toggle button */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onToggle}
          className="tap-target flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium text-navy transition-colors hover:bg-gray-50"
        >
          <SlidersHorizontal className="h-4 w-4" />
          Filter
          {activeCount > 0 && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent text-[10px] font-bold text-white">
              {activeCount}
            </span>
          )}
        </button>

        {activeCount > 0 && (
          <button
            type="button"
            onClick={clearFilters}
            className="text-sm text-accent hover:underline"
          >
            Clear all filters
          </button>
        )}
      </div>

      {/* Expanded filters */}
      {isOpen && (
        <div className="space-y-3 rounded-xl border bg-gray-50 p-3">
          {/* Row 1: Category */}
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
              Category
            </p>
            <div className="flex flex-wrap gap-1.5">
              {categoryOptions.map((opt) => (
                <button
                  key={opt.label}
                  type="button"
                  onClick={() => setFilter('category', opt.value)}
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                    filters.category === opt.value
                      ? 'bg-accent text-white'
                      : 'border bg-white text-gray-600 hover:border-accent hover:text-accent'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Row 2: Chemistry types */}
          {categories && categories.chemistry_types.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                Chemistry
              </p>
              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => setFilter('chemistry', null)}
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                    !filters.chemistry
                      ? 'bg-accent text-white'
                      : 'border bg-white text-gray-600 hover:border-accent hover:text-accent'
                  }`}
                >
                  All
                </button>
                {categories.chemistry_types.map((chem) => (
                  <button
                    key={chem}
                    type="button"
                    onClick={() => setFilter('chemistry', chem)}
                    className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                      filters.chemistry === chem
                        ? 'bg-accent text-white'
                        : 'border bg-white text-gray-600 hover:border-accent hover:text-accent'
                    }`}
                  >
                    {chem}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Row 3: Location filter toggle */}
          <div className="flex items-center justify-between rounded-lg border bg-white px-3 py-2.5">
            <span className="text-sm font-medium text-navy">
              Only show products at my location
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={filters.locationOnly}
              onClick={() => setFilter('locationOnly', !filters.locationOnly)}
              className={`relative h-6 w-11 rounded-full transition-colors ${
                filters.locationOnly ? 'bg-accent' : 'bg-gray-300'
              }`}
            >
              <span
                className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                  filters.locationOnly ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>
      )}

      {/* Active filter chips */}
      {activeCount > 0 && !isOpen && (
        <div className="flex flex-wrap gap-1.5">
          {filters.category && (
            <span className="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2.5 py-1 text-xs font-medium text-accent">
              {filters.category.replace('_', ' ')}
              <button
                type="button"
                onClick={() => setFilter('category', null)}
                className="ml-0.5 hover:text-accent/70"
                aria-label="Remove category filter"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          )}
          {filters.chemistry && (
            <span className="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2.5 py-1 text-xs font-medium text-accent">
              {filters.chemistry}
              <button
                type="button"
                onClick={() => setFilter('chemistry', null)}
                className="ml-0.5 hover:text-accent/70"
                aria-label="Remove chemistry filter"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          )}
          {filters.locationOnly && (
            <span className="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2.5 py-1 text-xs font-medium text-accent">
              My location only
              <button
                type="button"
                onClick={() => setFilter('locationOnly', false)}
                className="ml-0.5 hover:text-accent/70"
                aria-label="Remove location filter"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Loading Skeleton ────────────────────────────────────────────────────────

function ProductsSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <Skeleton key={i} className="h-[100px] rounded-xl" />
      ))}
    </div>
  )
}

// ─── Empty State ─────────────────────────────────────────────────────────────

function EmptyState({ searchTerm, onClear }: { searchTerm: string; onClear: () => void }) {
  return (
    <div className="rounded-xl border bg-white p-8 text-center">
      <Search className="mx-auto mb-3 h-10 w-10 text-gray-300" />
      <p className="font-medium text-navy">
        No products found{searchTerm ? ` for "${searchTerm}"` : ''}.
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        Try a different name or chemistry type, or remove your filters.
      </p>
      <button
        type="button"
        onClick={onClear}
        className="mt-4 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90"
      >
        Clear search
      </button>
    </div>
  )
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export function ProductLookupPage() {
  const [searchInput, setSearchInput] = useState('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [expandedDetail, setExpandedDetail] = useState<ProductDetailResponse | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const {
    products,
    totalCount,
    hasMore,
    isLoading,
    isLoadingMore,
    error,
    filters,
    search: doSearch,
    setFilter,
    clearFilters,
    loadMore,
    loadProduct,
    loadCategories,
  } = useProductsStore()

  const { locationCode } = useChatStore()

  // Debounce search input
  const debouncedSearch = useDebounce(searchInput, 300)

  // Sync debounced search to store
  useEffect(() => {
    if (debouncedSearch !== filters.search) {
      setFilter('search', debouncedSearch)
    }
  }, [debouncedSearch])

  // Initial load
  useEffect(() => {
    loadCategories()
    doSearch({ resetOffset: true })
  }, [])

  // Handle card expansion with lazy detail load
  const handleToggle = useCallback(async (productId: string) => {
    if (expandedId === productId) {
      setExpandedId(null)
      setExpandedDetail(null)
      return
    }

    setExpandedId(productId)
    setDetailLoading(true)

    const detail = await loadProduct(productId)
    setExpandedDetail(detail)
    setDetailLoading(false)
  }, [expandedId, loadProduct])

  // Clear search
  function handleClear() {
    setSearchInput('')
    clearFilters()
  }

  // Get user location code from chat store or auth store
  const userLocationCode = locationCode || null

  return (
    <div className="flex h-full flex-col">
      {/* Fixed search header */}
      <div className="sticky top-0 z-10 space-y-3 bg-gray-50 p-4 pb-3">
        {/* Title */}
        <div>
          <h2 className="text-xl font-bold text-navy">Products</h2>
          <p className="text-sm text-muted-foreground">
            Bower Ag product catalog — governance verified
          </p>
        </div>

        {/* Search bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search products, chemistry, part number..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="h-12 w-full rounded-lg border bg-white pl-10 pr-10 text-base outline-none ring-accent/50 transition-shadow focus:ring-2"
            style={{ fontSize: '16px' }}
          />
          {searchInput && (
            <button
              type="button"
              onClick={() => setSearchInput('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          {isLoading && (
            <Loader2 className="absolute right-10 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-accent" />
          )}
        </div>

        {/* Filter bar */}
        <FilterBar isOpen={filtersOpen} onToggle={() => setFiltersOpen(!filtersOpen)} />
      </div>

      {/* Scrollable results */}
      <div className="flex-1 overflow-y-auto p-4 pt-0">
        {/* Error banner */}
        {error && (
          <div className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Loading state */}
        {isLoading && products.length === 0 && <ProductsSkeleton />}

        {/* Empty state */}
        {!isLoading && products.length === 0 && (
          <EmptyState searchTerm={filters.search} onClear={handleClear} />
        )}

        {/* Product list */}
        {products.length > 0 && (
          <div className="space-y-3">
            {products.map((product) => (
              <div key={product.id}>
                <ProductCard
                  product={product}
                  isExpanded={expandedId === product.id}
                  onToggle={() => handleToggle(product.id)}
                />

                {/* Expanded detail — inline, no navigation */}
                {expandedId === product.id && (
                  <div className="rounded-b-xl border border-t-0 border-accent/20 bg-white px-4 pb-4">
                    {detailLoading ? (
                      <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Loading product details...
                      </div>
                    ) : expandedDetail ? (
                      <ProductCardExpanded
                        detail={expandedDetail}
                        userLocationCode={userLocationCode}
                      />
                    ) : (
                      <p className="py-4 text-sm text-red-600">
                        Failed to load product details.
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}

            {/* Pagination info + Load More */}
            <div className="py-4 text-center">
              <p className="text-sm text-muted-foreground">
                Showing {products.length} of {totalCount} products
              </p>
              {hasMore && (
                <button
                  type="button"
                  onClick={loadMore}
                  disabled={isLoadingMore}
                  className="mt-3 rounded-lg border border-accent bg-white px-6 py-2.5 text-sm font-medium text-accent transition-colors hover:bg-accent/5 disabled:opacity-50"
                >
                  {isLoadingMore ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading...
                    </span>
                  ) : (
                    'Load more'
                  )}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
