/**
 * ShareReportModal — Share a report with customer accounts.
 * Sprint 10: Customer search, confirmation, share execution.
 *
 * Only shows customer-role users in search results.
 * Clear confirmation before sharing with customer details.
 */

import { useState } from 'react'
import { X, Search, Loader2, Check, Users, AlertCircle } from 'lucide-react'
import { shareReport, apiFetchRaw } from '@/lib/api'

// ─── Types ───────────────────────────────────────────────────────────────────

interface CustomerAccount {
  id: string
  email: string
  full_name: string | null
  customer_operation: string | null
}

type ShareStep = 'search' | 'confirm' | 'success' | 'error'

// ─── Props ───────────────────────────────────────────────────────────────────

interface ShareReportModalProps {
  reportId: string
  reportTitle: string
  onClose: () => void
  onShared: () => void
}

// ─── Component ───────────────────────────────────────────────────────────────

export function ShareReportModal({ reportId, reportTitle, onClose, onShared }: ShareReportModalProps) {
  const [step, setStep] = useState<ShareStep>('search')
  const [searchQuery, setSearchQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState<CustomerAccount[]>([])
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerAccount | null>(null)
  const [sharing, setSharing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // ── Search for customers ──
  const handleSearch = async (query: string) => {
    setSearchQuery(query)
    if (query.length < 2) {
      setResults([])
      return
    }

    setSearching(true)
    try {
      // Call backend endpoint that searches users by role=customer
      const res = await apiFetchRaw<CustomerAccount[]>(
        `/users?role=customer&search=${encodeURIComponent(query)}`,
      )
      if (res.data) {
        setResults(res.data)
      } else {
        setResults([])
      }
    } catch {
      setResults([])
    } finally {
      setSearching(false)
    }
  }

  // ── Select customer → go to confirmation ──
  const handleSelect = (customer: CustomerAccount) => {
    setSelectedCustomer(customer)
    setStep('confirm')
  }

  // ── Execute share ──
  const handleShare = async () => {
    if (!selectedCustomer) return
    setSharing(true)
    setError(null)

    try {
      await shareReport(reportId, {
        customer_user_ids: [selectedCustomer.id],
      })
      setStep('success')
      onShared()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to share report')
      setStep('error')
    } finally {
      setSharing(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h3 className="text-base font-bold text-navy">Share Report</h3>
          <button
            onClick={onClose}
            className="tap-target rounded-lg p-1.5 hover:bg-gray-100"
            aria-label="Close"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4">
          {/* Step 1: Search */}
          {step === 'search' && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Who would you like to share this with?
              </p>

              {/* Search input */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Search by email or name..."
                  className="w-full rounded-lg border border-gray-300 py-2.5 pl-10 pr-3 text-base outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
                  autoFocus
                  data-testid="share-search-input"
                />
                {searching && (
                  <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-gray-400" />
                )}
              </div>

              {/* Results */}
              <div className="max-h-48 space-y-1 overflow-y-auto">
                {results.map((customer) => (
                  <button
                    key={customer.id}
                    onClick={() => handleSelect(customer)}
                    className="tap-target flex w-full items-center gap-3 rounded-lg p-3 text-left transition-colors hover:bg-gray-50"
                    data-testid="customer-result"
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100">
                      <Users className="h-4 w-4 text-blue-600" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-navy truncate">
                        {customer.full_name || customer.email}
                      </p>
                      {customer.customer_operation && (
                        <p className="text-xs text-muted-foreground truncate">
                          {customer.customer_operation}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground truncate">{customer.email}</p>
                    </div>
                  </button>
                ))}

                {searchQuery.length >= 2 && !searching && results.length === 0 && (
                  <div className="py-4 text-center">
                    <p className="text-sm text-muted-foreground">
                      No customer account found.
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Ask your manager to create one.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 2: Confirmation */}
          {step === 'confirm' && selectedCustomer && (
            <div className="space-y-4" data-testid="share-confirm">
              <p className="text-sm font-medium text-navy">
                Share &ldquo;{reportTitle}&rdquo; with{' '}
                {selectedCustomer.customer_operation || selectedCustomer.full_name || selectedCustomer.email}?
              </p>
              <p className="text-sm text-muted-foreground">
                {selectedCustomer.full_name || 'This customer'} will be able to log in to view and
                download this report.
              </p>
              <p className="text-sm text-muted-foreground">
                They will <strong>NOT</strong> see any Bower Ag internal information — only the report
                contents.
              </p>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setStep('search')}
                  className="tap-target flex-1 rounded-lg border border-gray-200 px-4 py-2.5 text-sm font-medium text-navy transition-colors hover:bg-gray-50"
                  disabled={sharing}
                >
                  Back
                </button>
                <button
                  onClick={handleShare}
                  disabled={sharing}
                  className="tap-target flex flex-1 items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
                  data-testid="share-confirm-btn"
                >
                  {sharing ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Sharing...
                    </>
                  ) : (
                    'Share'
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Success */}
          {step === 'success' && selectedCustomer && (
            <div className="flex flex-col items-center py-4 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <Check className="h-6 w-6 text-green-600" />
              </div>
              <p className="mt-3 text-sm font-medium text-navy">
                Report shared with{' '}
                {selectedCustomer.customer_operation || selectedCustomer.full_name || 'customer'}.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                They can log in to view it.
              </p>
              <button
                onClick={onClose}
                className="tap-target mt-4 w-full rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
              >
                Done
              </button>
            </div>
          )}

          {/* Error */}
          {step === 'error' && (
            <div className="flex flex-col items-center py-4 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
              <p className="mt-3 text-sm font-medium text-navy">Failed to share report</p>
              <p className="mt-1 text-xs text-muted-foreground">{error}</p>
              <button
                onClick={() => setStep('confirm')}
                className="tap-target mt-4 w-full rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
