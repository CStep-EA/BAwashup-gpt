/**
 * ProductsPage — Product catalog with search bar + card skeletons
 * Sprint 6: Shell only. Real data wiring in Sprint 8+.
 */

import { useState, useEffect } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Package, Search } from 'lucide-react'

function ProductsSkeleton() {
  return (
    <div className="space-y-4 p-4">
      {/* Search bar skeleton */}
      <Skeleton className="h-12 rounded-lg" />

      {/* Category tabs skeleton */}
      <div className="flex gap-2">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-8 w-20 rounded-full" />
        ))}
      </div>

      {/* Product cards skeleton */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Skeleton key={i} className="h-36 rounded-xl" />
        ))}
      </div>
    </div>
  )
}

export function ProductsPage() {
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 700)
    return () => clearTimeout(timer)
  }, [])

  if (loading) return <ProductsSkeleton />

  return (
    <div className="space-y-4 p-4">
      <div>
        <h2 className="text-xl font-bold text-navy">Products</h2>
        <p className="text-sm text-muted-foreground">
          Browse Bower Ag product catalog
        </p>
      </div>

      {/* Search bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search products…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-12 rounded-lg pl-10 text-base"
        />
      </div>

      {/* Category filter tabs */}
      <div className="flex gap-2 overflow-x-auto">
        {['All', 'Teat Dip', 'CIP Chemical', 'Detergent', 'Sanitizer'].map(
          (cat) => (
            <button
              key={cat}
              className="tap-target shrink-0 rounded-full border bg-white px-4 py-2 text-xs font-medium text-muted-foreground transition-colors first:border-accent first:bg-accent/10 first:text-accent hover:border-accent hover:text-accent"
            >
              {cat}
            </button>
          )
        )}
      </div>

      {/* Empty state */}
      <div className="rounded-xl border bg-white p-8 text-center">
        <Package className="mx-auto mb-3 h-10 w-10 text-gray-300" />
        <p className="font-medium text-navy">Product catalog loading soon</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Product data is pulled from governance. Full catalog browsing will
          be available in a future sprint.
        </p>
      </div>
    </div>
  )
}
