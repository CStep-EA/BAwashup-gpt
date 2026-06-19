/**
 * ProductCardExpanded — Expanded inline detail view with sellability + pricing.
 * Sprint 8: Lazy-loads pricing on expand, shows sellability chips for all 5 locations.
 *
 * ⚠️ Pricing comes ONLY from /pricing/lookup — lazy loaded, never from product detail.
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { MessageCircle, Loader2 } from 'lucide-react'
import type { ProductDetailResponse, PricingLookupResponse } from '@/lib/api'
import { fetchPricingLookup } from '@/lib/api'
import { useChatStore, LOCATIONS } from '@/store/chat'

// ─── Sellability Chip ────────────────────────────────────────────────────────

interface SellChipProps {
  locationName: string
  branchCode: string
  sellable: boolean
  isUserLocation: boolean
}

function SellChip({ locationName, branchCode, sellable, isUserLocation }: SellChipProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
        sellable
          ? 'bg-green-50 text-green-700'
          : 'bg-red-50 text-red-600'
      } ${isUserLocation ? 'ring-2 ring-accent ring-offset-1' : ''}`}
      title={`${locationName} (${branchCode}): ${sellable ? 'Sellable' : 'Not sellable'}`}
    >
      {sellable ? '✓' : '✕'}
      <span className="max-w-[60px] truncate">{locationName.split(' ')[0]}</span>
    </span>
  )
}

// ─── Pricing Table ───────────────────────────────────────────────────────────

interface PricingSectionProps {
  productId: string
  locationCode: string | null
  sellableAtUserLocation: boolean
}

function PricingSection({ productId, locationCode, sellableAtUserLocation }: PricingSectionProps) {
  const [pricing, setPricing] = useState<PricingLookupResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!locationCode || !sellableAtUserLocation) return

    let cancelled = false
    setLoading(true)
    setError(null)

    fetchPricingLookup(productId, locationCode)
      .then((data) => {
        if (!cancelled) setPricing(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load pricing')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [productId, locationCode, sellableAtUserLocation])

  if (!locationCode) {
    return (
      <p className="text-sm text-muted-foreground italic">
        Set your location to see pricing.
      </p>
    )
  }

  if (!sellableAtUserLocation) {
    return (
      <p className="text-sm text-muted-foreground italic">
        Contact your manager for current pricing at {LOCATIONS[locationCode] || locationCode}.
      </p>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading pricing...
      </div>
    )
  }

  if (error) {
    return (
      <p className="text-sm text-red-600">
        {error.includes('403') ? `Contact your manager for current pricing at ${LOCATIONS[locationCode] || locationCode}.` : error}
      </p>
    )
  }

  if (!pricing || pricing.pricing.length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic">
        Contact your manager for current pricing at {LOCATIONS[locationCode] || locationCode}.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {/* Pricing table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="pb-1 pr-3">Container</th>
              <th className="pb-1 pr-3">Price/Unit</th>
              <th className="pb-1">Extended</th>
            </tr>
          </thead>
          <tbody>
            {pricing.pricing.map((row) => (
              <tr key={row.id} className="border-b border-gray-100">
                <td className="py-1.5 pr-3 font-medium">{row.container_size} {row.uom}</td>
                <td className="py-1.5 pr-3">${row.price_per_unit.toFixed(2)}</td>
                <td className="py-1.5">
                  {row.extended_price ? `$${row.extended_price.toFixed(2)}` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Governance citation */}
      <p className="text-xs italic text-gray-400">
        Confirmed from {pricing.location} Price Sheet — effective {pricing.effective_date || 'current'}
      </p>
    </div>
  )
}

// ─── Main Component ──────────────────────────────────────────────────────────

interface ProductCardExpandedProps {
  detail: ProductDetailResponse
  userLocationCode: string | null
}

export function ProductCardExpanded({ detail, userLocationCode }: ProductCardExpandedProps) {
  const navigate = useNavigate()
  const { addUserMessage } = useChatStore()

  const sellableAtUserLocation = userLocationCode
    ? detail.sellability.some(
        (s) => s.branch_code === userLocationCode && s.sellable
      )
    : false

  function handleAskAboutProduct() {
    const message = `Tell me more about ${detail.product_name} for my location`
    addUserMessage(message)
    navigate('/chat')
  }

  return (
    <div className="mt-3 space-y-4 border-t pt-3">
      {/* Full details */}
      {(detail.emollient_pct || detail.emollient_type || detail.notes) && (
        <div className="space-y-1">
          {detail.emollient_pct && (
            <p className="text-sm text-navy">
              <span className="font-medium">Emollient:</span> {detail.emollient_pct}%
              {detail.emollient_type && ` (${detail.emollient_type})`}
            </p>
          )}
          {detail.notes && (
            <p className="text-sm text-muted-foreground">{detail.notes}</p>
          )}
        </div>
      )}

      {/* Sellability row */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Sellability by Location
        </p>
        <div className="flex flex-wrap gap-1.5">
          {detail.sellability.map((entry) => (
            <SellChip
              key={entry.branch_code}
              locationName={entry.location_name}
              branchCode={entry.branch_code}
              sellable={entry.sellable}
              isUserLocation={entry.branch_code === userLocationCode}
            />
          ))}
        </div>
      </div>

      {/* Pricing section — lazy loaded */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Pricing
        </p>
        <PricingSection
          productId={detail.id}
          locationCode={userLocationCode}
          sellableAtUserLocation={sellableAtUserLocation}
        />
      </div>

      {/* Ask about this product */}
      <button
        type="button"
        onClick={handleAskAboutProduct}
        className="tap-target flex w-full items-center justify-center gap-2 rounded-lg border border-accent bg-accent/5 px-4 py-3 text-sm font-medium text-accent transition-colors hover:bg-accent/10"
      >
        <MessageCircle className="h-4 w-4" />
        Ask about this product
      </button>
    </div>
  )
}
