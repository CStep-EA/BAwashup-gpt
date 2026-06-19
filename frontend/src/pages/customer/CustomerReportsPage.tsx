/**
 * CustomerReportsPage — Main landing page for customers.
 * Sprint 13: Warm welcome, list of shared reports, helpful empty state.
 *
 * UX:
 *   - Warm greeting with customer name + operation
 *   - Report cards with view/download actions
 *   - Friendly empty state if no reports shared yet
 *   - Loading skeleton
 *   - Error state with retry
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { fetchCustomerReports, type CustomerReportSummary } from '@/lib/api'
import { CustomerReportCard } from '@/components/customer/CustomerReportCard'
import { RefreshCw, FileText } from 'lucide-react'

export function CustomerReportsPage() {
  const { profile } = useAuthStore()
  const navigate = useNavigate()

  const [reports, setReports] = useState<CustomerReportSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const customerName = profile?.full_name?.split(' ')[0] || 'there'
  const operationName = profile?.customer_operation || ''

  async function loadReports() {
    setIsLoading(true)
    setError(null)
    try {
      const data = await fetchCustomerReports()
      setReports(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reports')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadReports()
  }, [])

  function handleView(reportId: string) {
    navigate(`/my-reports/${reportId}`)
  }

  return (
    <div data-testid="customer-reports-page">
      {/* ── Welcome section ──────────────────────────────────────────── */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-navy" data-testid="customer-welcome">
          Welcome back, {customerName}!
        </h1>
        {operationName && (
          <p className="mt-1 text-sm text-muted-foreground" data-testid="customer-operation-subtitle">
            {operationName}
          </p>
        )}
        <p className="mt-2 text-sm text-muted-foreground">
          Here are the reports your Bower Ag team has prepared for you. Each one includes our
          observations and recommendations tailored specifically for your operation.
        </p>
      </div>

      {/* ── Loading skeleton ─────────────────────────────────────────── */}
      {isLoading && (
        <div className="space-y-3" data-testid="customer-reports-loading">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="animate-pulse rounded-xl border bg-white p-4"
            >
              <div className="flex gap-3">
                <div className="h-10 w-10 rounded-lg bg-gray-200" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-3/4 rounded bg-gray-200" />
                  <div className="h-3 w-1/2 rounded bg-gray-200" />
                </div>
              </div>
              <div className="mt-3 h-9 rounded-lg bg-gray-200" />
            </div>
          ))}
        </div>
      )}

      {/* ── Error state ──────────────────────────────────────────────── */}
      {!isLoading && error && (
        <div
          className="rounded-xl border border-danger/20 bg-danger/5 p-6 text-center"
          data-testid="customer-reports-error"
        >
          <p className="text-sm font-medium text-danger">Something went wrong</p>
          <p className="mt-1 text-xs text-muted-foreground">{error}</p>
          <button
            onClick={loadReports}
            className="tap-target mt-3 inline-flex items-center gap-2 rounded-lg bg-navy px-4 py-2 text-sm font-medium text-white hover:bg-navy/90"
            data-testid="customer-reports-retry"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </button>
        </div>
      )}

      {/* ── Empty state ──────────────────────────────────────────────── */}
      {!isLoading && !error && reports.length === 0 && (
        <div
          className="rounded-xl border bg-white p-8 text-center"
          data-testid="customer-reports-empty"
        >
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-accent/10">
            <FileText className="h-8 w-8 text-accent" />
          </div>
          <h2 className="mt-4 text-base font-semibold text-navy">
            No reports yet
          </h2>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">
            Your Bower Ag team hasn&apos;t shared any reports with you yet. Once they do,
            you&apos;ll find them right here.
          </p>
          <p className="mt-3 text-xs text-muted-foreground/70">
            If you&apos;re expecting a report, reach out to your Bower Ag representative.
          </p>
        </div>
      )}

      {/* ── Report list ──────────────────────────────────────────────── */}
      {!isLoading && !error && reports.length > 0 && (
        <div className="space-y-3" data-testid="customer-reports-list">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground">
              {reports.length} {reports.length === 1 ? 'report' : 'reports'} available
            </p>
            <button
              onClick={loadReports}
              className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-muted-foreground hover:bg-gray-100"
              aria-label="Refresh reports"
              data-testid="customer-reports-refresh"
            >
              <RefreshCw className="h-3 w-3" />
              Refresh
            </button>
          </div>
          {reports.map((report) => (
            <CustomerReportCard
              key={report.report_id}
              report={report}
              onView={handleView}
            />
          ))}
        </div>
      )}
    </div>
  )
}
