/**
 * ProductCard — Collapsed product card for the catalog list.
 * Sprint 8: Mobile-first, shows name, badges, chevron to expand.
 *
 * Category badges: teat_dip=blue, chemical=teal, cip=amber
 * Usage timing badges: PRE / POST / BOTH
 */

import { ChevronRight } from 'lucide-react'
import type { ProductSummary } from '@/lib/api'

// ─── Badge Colors ────────────────────────────────────────────────────────────

const CATEGORY_COLORS: Record<string, string> = {
  teat_dip: 'bg-blue-100 text-blue-700',
  chemical: 'bg-teal-100 text-teal-700',
  cip: 'bg-amber-100 text-amber-700',
}

const TIMING_LABELS: Record<string, string> = {
  pre: 'PRE',
  post: 'POST',
  both: 'BOTH',
}

// ─── Component ───────────────────────────────────────────────────────────────

interface ProductCardProps {
  product: ProductSummary
  isExpanded: boolean
  onToggle: () => void
}

export function ProductCard({ product, isExpanded, onToggle }: ProductCardProps) {
  const categoryColor = CATEGORY_COLORS[product.product_type] || 'bg-gray-100 text-gray-700'
  const categoryLabel = product.category || product.product_type

  return (
    <button
      type="button"
      onClick={onToggle}
      className={`tap-target w-full rounded-xl border bg-white p-4 text-left transition-all ${
        isExpanded ? 'border-accent/30 shadow-md' : 'border-gray-200 shadow-sm hover:shadow-md'
      }`}
      aria-expanded={isExpanded}
      aria-label={`${product.product_name}. Tap to ${isExpanded ? 'collapse' : 'expand'}`}
    >
      <div className="flex items-start justify-between gap-3">
        {/* Left content */}
        <div className="min-w-0 flex-1">
          {/* Product name */}
          <h3 className="text-base font-bold text-navy leading-snug">
            {product.product_name}
          </h3>

          {/* Badges row */}
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {/* Category badge */}
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${categoryColor}`}>
              {categoryLabel.replace('_', ' ')}
            </span>

            {/* Usage timing badge (teat dip only) */}
            {product.usage_timing && (
              <span className="inline-flex items-center rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">
                {TIMING_LABELS[product.usage_timing] || product.usage_timing.toUpperCase()}
              </span>
            )}

            {/* RTU / Concentrate badge */}
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
              product.is_concentrate ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'
            }`}>
              {product.is_concentrate ? 'Concentrate' : 'RTU'}
            </span>

            {/* SDS verified */}
            {product.sds_verified && (
              <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                SDS ✓
              </span>
            )}
          </div>

          {/* Chemistry type */}
          {product.chemistry_type && (
            <p className="mt-1.5 text-[13px] text-muted-foreground">
              {product.chemistry_type}
              {product.germicide_type && ` · ${product.germicide_type}`}
            </p>
          )}
        </div>

        {/* Expand chevron */}
        <div className="flex-shrink-0 pt-1">
          <ChevronRight
            className={`h-5 w-5 text-gray-400 transition-transform duration-200 ${
              isExpanded ? 'rotate-90' : ''
            }`}
          />
        </div>
      </div>
    </button>
  )
}
