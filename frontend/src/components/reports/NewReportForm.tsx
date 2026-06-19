/**
 * NewReportForm — Multi-step report generation form.
 * Sprint 10: 4 steps — Customer Info, Select Products, Visit Notes, Preview & Generate.
 *
 * Mobile: Full-screen modal. Desktop: Side panel.
 * Progress steps are simulated client-side for better UX.
 * On failure: preserves all user data, never navigates away.
 */

import { useState, useEffect, useCallback, useMemo } from 'react'
import { X, ChevronLeft, ChevronRight, Check, Loader2, AlertCircle, Search } from 'lucide-react'
import { LOCATIONS } from '@/store/chat'
import { useAuthStore } from '@/store/auth'
import type { ProductSummary } from '@/lib/api'
import { fetchProducts, fetchPricingLookup, generateReport } from '@/lib/api'
import type { ReportGenerateResponse } from '@/lib/api'

// ─── Types ───────────────────────────────────────────────────────────────────

interface CustomerInfo {
  customerName: string
  operationName: string
  locationCode: string
  repName: string
  repTitle: string
}

interface PricingPreview {
  product_name: string
  container: string
  price_per_unit: number
}

type GenerateStatus = 'idle' | 'governance' | 'writing' | 'preparing' | 'success' | 'error'

// ─── Props ───────────────────────────────────────────────────────────────────

interface NewReportFormProps {
  onClose: () => void
  onSuccess: (result: ReportGenerateResponse) => void
}

// ─── Progress Messages ───────────────────────────────────────────────────────

const PROGRESS_MESSAGES: Record<string, string> = {
  governance: 'Reviewing your product selections...',
  writing: 'Writing your report...',
  preparing: 'Preparing your download...',
}

// ─── Component ───────────────────────────────────────────────────────────────

export function NewReportForm({ onClose, onSuccess }: NewReportFormProps) {
  const { profile } = useAuthStore()

  // ── Form state ──
  const [step, setStep] = useState(1)

  // Step 1: Customer info
  const [customer, setCustomer] = useState<CustomerInfo>({
    customerName: '',
    operationName: '',
    locationCode: profile?.location_id ? '' : '',
    repName: profile?.full_name || '',
    repTitle: 'Bower Ag Consultant',
  })

  // Step 2: Products
  const [products, setProducts] = useState<ProductSummary[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [productSearch, setProductSearch] = useState('')
  const [loadingProducts, setLoadingProducts] = useState(false)
  const [includePricing, setIncludePricing] = useState(false)
  const [pricingPreview, setPricingPreview] = useState<PricingPreview[]>([])
  const [loadingPricing, setLoadingPricing] = useState(false)

  // Step 3: Notes
  const [findings, setFindings] = useState('')
  const [recommendations, setRecommendations] = useState('')

  // Step 4: Generate
  const [generateStatus, setGenerateStatus] = useState<GenerateStatus>('idle')
  const [generateResult, setGenerateResult] = useState<ReportGenerateResponse | null>(null)
  const [generateError, setGenerateError] = useState<string | null>(null)
  const [isGovernanceError, setIsGovernanceError] = useState(false)

  // ── Load products when location changes ──
  useEffect(() => {
    if (!customer.locationCode) return
    setLoadingProducts(true)
    fetchProducts({ location_code: customer.locationCode, limit: 100 })
      .then((res) => {
        setProducts(res.products)
        // Clear selections that aren't available at new location
        setSelectedIds((prev) => {
          const available = new Set(res.products.map((p) => p.id))
          return new Set([...prev].filter((id) => available.has(id)))
        })
      })
      .catch(() => setProducts([]))
      .finally(() => setLoadingProducts(false))
  }, [customer.locationCode])

  // ── Load pricing preview when toggle or selection changes ──
  useEffect(() => {
    if (!includePricing || selectedIds.size === 0 || !customer.locationCode) {
      setPricingPreview([])
      return
    }

    setLoadingPricing(true)
    const promises = [...selectedIds].map(async (pid) => {
      try {
        const res = await fetchPricingLookup(pid, customer.locationCode)
        const product = products.find((p) => p.id === pid)
        return (res.pricing || []).map((pr) => ({
          product_name: product?.product_name || 'Product',
          container: `${pr.container_size} ${pr.uom}`,
          price_per_unit: pr.price_per_unit,
        }))
      } catch {
        return []
      }
    })

    Promise.all(promises)
      .then((results) => setPricingPreview(results.flat()))
      .finally(() => setLoadingPricing(false))
  }, [includePricing, selectedIds, customer.locationCode, products])

  // ── Validation ──
  const step1Valid =
    customer.customerName.trim().length > 0 &&
    customer.operationName.trim().length > 0 &&
    customer.locationCode.length > 0 &&
    customer.repName.trim().length > 0

  const step2Valid = selectedIds.size >= 1
  const step3Valid = findings.trim().length > 0 && recommendations.trim().length > 0

  // ── Product search ──
  const filteredProducts = useMemo(() => {
    const term = productSearch.toLowerCase()
    if (!term) return products
    return products.filter(
      (p) =>
        p.product_name.toLowerCase().includes(term) ||
        (p.chemistry_type && p.chemistry_type.toLowerCase().includes(term)) ||
        p.category.toLowerCase().includes(term),
    )
  }, [products, productSearch])

  // Sort: selected first
  const sortedProducts = useMemo(() => {
    return [...filteredProducts].sort((a, b) => {
      const aSelected = selectedIds.has(a.id) ? 0 : 1
      const bSelected = selectedIds.has(b.id) ? 0 : 1
      return aSelected - bSelected
    })
  }, [filteredProducts, selectedIds])

  const toggleProduct = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  // ── Generate report ──
  const handleGenerate = async () => {
    setGenerateStatus('governance')
    setGenerateError(null)
    setIsGovernanceError(false)

    // Simulated Step 1: governance check (show for 1s before API call)
    await new Promise((r) => setTimeout(r, 1000))
    setGenerateStatus('writing')

    try {
      const result = await generateReport({
        customer_name: customer.customerName,
        operation_name: customer.operationName,
        location_code: customer.locationCode,
        product_ids: [...selectedIds],
        findings,
        recommendations,
        rep_name: customer.repName,
        rep_title: customer.repTitle,
        include_pricing: includePricing,
      })

      // Step 3: preparing (0.5s after API returns)
      setGenerateStatus('preparing')
      await new Promise((r) => setTimeout(r, 500))

      setGenerateStatus('success')
      setGenerateResult(result)
      onSuccess(result)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong'
      // Check if it's a governance (400) error
      const is400 = message.includes('API 400')
      setIsGovernanceError(is400)
      setGenerateError(
        is400
          ? message.replace(/^API 400:\s*/, '').replace(/.*"detail":\s*"/, '').replace(/".*$/, '')
          : 'Something went wrong building your report. Please try again.',
      )
      setGenerateStatus('error')
    }
  }

  // ── Step navigation ──
  const canGoNext =
    (step === 1 && step1Valid) ||
    (step === 2 && step2Valid) ||
    (step === 3 && step3Valid)

  const goNext = () => {
    if (canGoNext && step < 4) setStep(step + 1)
  }
  const goBack = () => {
    if (step > 1) setStep(step - 1)
  }

  // ── Render ──
  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-end bg-black/40">
      {/* Backdrop click to close (only if not generating) */}
      <div
        className="hidden lg:block lg:flex-1"
        onClick={generateStatus === 'idle' || generateStatus === 'error' ? onClose : undefined}
      />

      {/* Panel: full-screen mobile, side panel desktop */}
      <div className="flex w-full flex-col bg-white lg:max-w-lg lg:shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-3">
            {step > 1 && generateStatus === 'idle' && (
              <button onClick={goBack} className="tap-target rounded-lg p-1 hover:bg-gray-100">
                <ChevronLeft className="h-5 w-5 text-gray-600" />
              </button>
            )}
            <h2 className="text-lg font-bold text-navy">New Report</h2>
          </div>

          {/* Step indicator */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Step {step} of 4
            </span>
            <button
              onClick={onClose}
              className="tap-target rounded-lg p-1.5 hover:bg-gray-100"
              aria-label="Close"
            >
              <X className="h-5 w-5 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-1 bg-gray-100">
          <div
            className="h-full bg-accent transition-all duration-300"
            style={{ width: `${(step / 4) * 100}%` }}
          />
        </div>

        {/* Content area */}
        <div className="flex-1 overflow-y-auto p-4">
          {step === 1 && (
            <Step1CustomerInfo
              customer={customer}
              onChange={setCustomer}
            />
          )}
          {step === 2 && (
            <Step2Products
              products={sortedProducts}
              selectedIds={selectedIds}
              onToggle={toggleProduct}
              search={productSearch}
              onSearchChange={setProductSearch}
              loading={loadingProducts}
              locationCode={customer.locationCode}
              includePricing={includePricing}
              onIncludePricingChange={setIncludePricing}
              pricingPreview={pricingPreview}
              loadingPricing={loadingPricing}
            />
          )}
          {step === 3 && (
            <Step3Notes
              findings={findings}
              recommendations={recommendations}
              onFindingsChange={setFindings}
              onRecommendationsChange={setRecommendations}
            />
          )}
          {step === 4 && (
            <Step4Generate
              customer={customer}
              selectedProducts={products.filter((p) => selectedIds.has(p.id))}
              includePricing={includePricing}
              findings={findings}
              recommendations={recommendations}
              status={generateStatus}
              result={generateResult}
              error={generateError}
              isGovernanceError={isGovernanceError}
              onGenerate={handleGenerate}
              onGoBack={() => setStep(2)}
              onRetry={handleGenerate}
              onClose={onClose}
            />
          )}
        </div>

        {/* Footer with Next button (Steps 1-3 only, not during generation) */}
        {step < 4 && (
          <div className="border-t p-4">
            <button
              onClick={goNext}
              disabled={!canGoNext}
              className="tap-target flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Step 1: Customer Info ──────────────────────────────────────────────────

function Step1CustomerInfo({
  customer,
  onChange,
}: {
  customer: CustomerInfo
  onChange: (c: CustomerInfo) => void
}) {
  const update = (key: keyof CustomerInfo, value: string) => {
    onChange({ ...customer, [key]: value })
  }

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-base font-bold text-navy">Who is this report for?</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Enter the customer and visit details.
        </p>
      </div>

      <div className="space-y-4">
        <FieldInput
          label="Customer / Farm Name"
          value={customer.customerName}
          onChange={(v) => update('customerName', v)}
          placeholder="e.g., Green Valley Dairy"
          required
        />
        <FieldInput
          label="Operation Name"
          value={customer.operationName}
          onChange={(v) => update('operationName', v)}
          placeholder="e.g., Green Valley Main Facility"
          required
        />

        <div>
          <label className="mb-1.5 block text-sm font-medium text-navy">
            Location <span className="text-red-500">*</span>
          </label>
          <select
            value={customer.locationCode}
            onChange={(e) => update('locationCode', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-base text-navy outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
            data-testid="location-select"
          >
            <option value="">Select a location...</option>
            {Object.entries(LOCATIONS).map(([code, name]) => (
              <option key={code} value={code}>
                {name} ({code})
              </option>
            ))}
          </select>
        </div>

        <FieldInput
          label="Your Name (as rep)"
          value={customer.repName}
          onChange={(v) => update('repName', v)}
          placeholder="Your full name"
          required
        />
        <FieldInput
          label="Your Title"
          value={customer.repTitle}
          onChange={(v) => update('repTitle', v)}
          placeholder="Bower Ag Consultant"
        />
      </div>
    </div>
  )
}

// ─── Step 2: Select Products ────────────────────────────────────────────────

function Step2Products({
  products,
  selectedIds,
  onToggle,
  search,
  onSearchChange,
  loading,
  locationCode,
  includePricing,
  onIncludePricingChange,
  pricingPreview,
  loadingPricing,
}: {
  products: ProductSummary[]
  selectedIds: Set<string>
  onToggle: (id: string) => void
  search: string
  onSearchChange: (s: string) => void
  loading: boolean
  locationCode: string
  includePricing: boolean
  onIncludePricingChange: (v: boolean) => void
  pricingPreview: PricingPreview[]
  loadingPricing: boolean
}) {
  const locationName = LOCATIONS[locationCode] || locationCode

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-bold text-navy">What products are in their program?</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Only products available at {locationName} are shown.
        </p>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search products..."
          className="w-full rounded-lg border border-gray-300 py-2.5 pl-10 pr-3 text-base outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
        />
      </div>

      {/* Selected count */}
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center rounded-full bg-accent/10 px-2.5 py-0.5 text-xs font-semibold text-accent">
          {selectedIds.size} product{selectedIds.size !== 1 ? 's' : ''} selected
        </span>
        {selectedIds.size === 0 && (
          <span className="text-xs text-muted-foreground">Select at least 1 product</span>
        )}
      </div>

      {/* Product list */}
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-accent" />
        </div>
      ) : (
        <div className="space-y-2" data-testid="product-select-list">
          {products.map((p) => {
            const isSelected = selectedIds.has(p.id)
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => onToggle(p.id)}
                className={`w-full rounded-xl border-2 p-3 text-left transition-all ${
                  isSelected
                    ? 'border-accent bg-accent/5 shadow-sm'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center gap-3">
                  {/* Checkbox */}
                  <div
                    className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition-colors ${
                      isSelected ? 'border-accent bg-accent' : 'border-gray-300'
                    }`}
                  >
                    {isSelected && <Check className="h-3 w-3 text-white" />}
                  </div>
                  {/* Product info */}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-navy">{p.product_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {p.category.replace('_', ' ')}
                      {p.chemistry_type && ` · ${p.chemistry_type}`}
                    </p>
                  </div>
                </div>
              </button>
            )
          })}
          {products.length === 0 && !loading && (
            <p className="py-4 text-center text-sm text-muted-foreground">
              No products found at this location.
            </p>
          )}
        </div>
      )}

      {/* Include pricing toggle */}
      <div className="flex items-center justify-between rounded-lg border border-gray-200 p-3">
        <div>
          <p className="text-sm font-medium text-navy">Include pricing in report</p>
          <p className="text-xs text-muted-foreground">Pricing for selected products at this location</p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={includePricing}
          onClick={() => onIncludePricingChange(!includePricing)}
          className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${
            includePricing ? 'bg-accent' : 'bg-gray-300'
          }`}
          data-testid="pricing-toggle"
        >
          <span
            className={`inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform ${
              includePricing ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {/* Pricing preview */}
      {includePricing && selectedIds.size > 0 && (
        <div className="rounded-lg border border-gray-200 overflow-x-auto">
          {loadingPricing ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-4 w-4 animate-spin text-accent" />
              <span className="ml-2 text-sm text-muted-foreground">Loading pricing...</span>
            </div>
          ) : pricingPreview.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-left">
                  <th className="px-3 py-2 font-medium text-navy">Product</th>
                  <th className="px-3 py-2 font-medium text-navy">Container</th>
                  <th className="px-3 py-2 text-right font-medium text-navy">Price</th>
                </tr>
              </thead>
              <tbody>
                {pricingPreview.map((p, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="px-3 py-2">{p.product_name}</td>
                    <td className="px-3 py-2">{p.container}</td>
                    <td className="px-3 py-2 text-right font-medium">${p.price_per_unit.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="px-3 py-3 text-sm text-muted-foreground">No pricing available.</p>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Step 3: Visit Notes ────────────────────────────────────────────────────

function Step3Notes({
  findings,
  recommendations,
  onFindingsChange,
  onRecommendationsChange,
}: {
  findings: string
  recommendations: string
  onFindingsChange: (v: string) => void
  onRecommendationsChange: (v: string) => void
}) {
  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-base font-bold text-navy">What did you find and recommend?</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Write in plain language — our AI will turn your notes into a professional report.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-navy">
            What did you observe on this visit? <span className="text-red-500">*</span>
          </label>
          <textarea
            value={findings}
            onChange={(e) => onFindingsChange(e.target.value)}
            rows={10}
            placeholder="e.g., Milking parlor is well-maintained. Noticed some teat end roughness on the fresh pen cows. SCC trending up slightly over past 2 months..."
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-base leading-relaxed outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
            data-testid="findings-textarea"
          />
          <p className="mt-1 text-right text-xs text-muted-foreground" data-testid="findings-count">
            {findings.length} characters
          </p>
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-navy">
            What are you recommending? <span className="text-red-500">*</span>
          </label>
          <textarea
            value={recommendations}
            onChange={(e) => onRecommendationsChange(e.target.value)}
            rows={10}
            placeholder="e.g., Switch to a higher-emollient post-dip to improve teat conditioning. Continue current pre-dip — it's working well..."
            className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-base leading-relaxed outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
            data-testid="recs-textarea"
          />
          <p className="mt-1 text-right text-xs text-muted-foreground" data-testid="recs-count">
            {recommendations.length} characters
          </p>
        </div>
      </div>
    </div>
  )
}

// ─── Step 4: Preview & Generate ─────────────────────────────────────────────

function Step4Generate({
  customer,
  selectedProducts,
  includePricing,
  findings,
  recommendations,
  status,
  result,
  error,
  isGovernanceError,
  onGenerate,
  onGoBack,
  onRetry,
  onClose,
}: {
  customer: CustomerInfo
  selectedProducts: ProductSummary[]
  includePricing: boolean
  findings: string
  recommendations: string
  status: GenerateStatus
  result: ReportGenerateResponse | null
  error: string | null
  isGovernanceError: boolean
  onGenerate: () => void
  onGoBack: () => void
  onRetry: () => void
  onClose: () => void
}) {
  const locationName = LOCATIONS[customer.locationCode] || customer.locationCode

  // Success state
  if (status === 'success' && result) {
    return (
      <div className="flex flex-col items-center py-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
          <Check className="h-8 w-8 text-green-600" />
        </div>
        <h3 className="mt-4 text-lg font-bold text-navy">
          Your report for {result.operation_name} is ready!
        </h3>
        <p className="mt-2 text-sm text-muted-foreground">
          {result.products_included} product{result.products_included !== 1 ? 's' : ''} included
          {result.pricing_included ? ' with pricing' : ''}
        </p>

        <div className="mt-6 w-full space-y-3">
          {result.download_url && (
            <a
              href={result.download_url}
              target="_blank"
              rel="noopener noreferrer"
              className="tap-target flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
              data-testid="download-report-btn"
            >
              Download Report
            </a>
          )}
          <button
            onClick={onClose}
            className="tap-target w-full rounded-lg border border-gray-200 px-4 py-3 text-sm font-medium text-navy transition-colors hover:bg-gray-50"
          >
            Back to Reports
          </button>
        </div>
      </div>
    )
  }

  // Error state
  if (status === 'error' && error) {
    return (
      <div className="flex flex-col items-center py-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
          <AlertCircle className="h-8 w-8 text-red-600" />
        </div>
        <h3 className="mt-4 text-lg font-bold text-navy">
          {isGovernanceError ? 'Product Not Available' : 'Report Generation Failed'}
        </h3>
        <p className="mt-2 text-sm text-muted-foreground" data-testid="generate-error">
          {error}
        </p>
        <div className="mt-6 w-full space-y-3">
          {isGovernanceError ? (
            <button
              onClick={onGoBack}
              className="tap-target w-full rounded-lg bg-accent px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
            >
              Go Back to Product Selection
            </button>
          ) : (
            <button
              onClick={onRetry}
              className="tap-target w-full rounded-lg bg-accent px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
            >
              Try Again
            </button>
          )}
        </div>
      </div>
    )
  }

  // Generating state (progress steps)
  if (status !== 'idle') {
    return (
      <div className="flex flex-col items-center py-12 text-center">
        <Loader2 className="h-10 w-10 animate-spin text-accent" />
        <p className="mt-4 text-base font-medium text-navy" data-testid="progress-message">
          {PROGRESS_MESSAGES[status] || 'Working...'}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          This usually takes 15-30 seconds.
        </p>
      </div>
    )
  }

  // Default: Review & Generate
  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-base font-bold text-navy">Review & Generate</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Review your inputs below. Once you generate, the report will be ready to download.
        </p>
      </div>

      {/* Summary cards */}
      <div className="space-y-3">
        <SummaryRow label="Customer" value={customer.customerName} />
        <SummaryRow label="Operation" value={customer.operationName} />
        <SummaryRow label="Location" value={locationName} />
        <SummaryRow label="Rep" value={`${customer.repName}, ${customer.repTitle}`} />
        <SummaryRow
          label="Products"
          value={selectedProducts.map((p) => p.product_name).join(', ')}
        />
        <SummaryRow label="Pricing included" value={includePricing ? 'Yes' : 'No'} />
        <SummaryRow label="Findings" value={findings.slice(0, 100) + (findings.length > 100 ? '...' : '')} />
        <SummaryRow
          label="Recommendations"
          value={recommendations.slice(0, 100) + (recommendations.length > 100 ? '...' : '')}
        />
      </div>

      {/* Generate button */}
      <button
        onClick={onGenerate}
        className="tap-target flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
        data-testid="generate-btn"
      >
        Generate Report
      </button>
    </div>
  )
}

// ─── Shared Field Components ────────────────────────────────────────────────

function FieldInput({
  label,
  value,
  onChange,
  placeholder,
  required,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  required?: boolean
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-navy">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-base outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
      />
    </div>
  )
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2.5">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-sm text-navy">{value || '—'}</p>
    </div>
  )
}
