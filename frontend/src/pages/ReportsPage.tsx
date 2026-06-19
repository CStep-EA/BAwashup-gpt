/**
 * ReportsPage — Report list with cards, empty state, polling, and new report form.
 * Sprint 10: Full reports UI — list, generate, share, download, preview.
 *
 * Polling: When any report has status='generating', polls GET /reports every 5s.
 * Toast: Shows notification when a generating report completes.
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, FileText, Loader2 } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { useReportsStore } from '@/store/reports'
import { fetchReportDetail } from '@/lib/api'
import type { ReportGenerateResponse } from '@/lib/api'
import { ReportCard } from '@/components/reports/ReportCard'
import { NewReportForm } from '@/components/reports/NewReportForm'
import { ShareReportModal } from '@/components/reports/ShareReportModal'

// ─── Skeletons ───────────────────────────────────────────────────────────────

function ReportsSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-7 w-32" />
        <Skeleton className="h-10 w-28 rounded-lg" />
      </div>
      <div className="space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    </div>
  )
}

// ─── Page ────────────────────────────────────────────────────────────────────

export function ReportsPage() {
  const navigate = useNavigate()
  const { reports, isLoading, error, completedToast, loadReports, stopPolling, clearToast } =
    useReportsStore()

  const [showNewForm, setShowNewForm] = useState(false)
  const [shareReportId, setShareReportId] = useState<string | null>(null)
  const [shareReportTitle, setShareReportTitle] = useState('')

  // Initial load
  useEffect(() => {
    loadReports()
    return () => stopPolling()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auto-dismiss toast
  useEffect(() => {
    if (completedToast) {
      const t = setTimeout(() => clearToast(), 5000)
      return () => clearTimeout(t)
    }
  }, [completedToast, clearToast])

  // ── Handlers ──
  const handleDownload = async (reportId: string) => {
    try {
      const detail = await fetchReportDetail(reportId)
      if (detail.download_url) {
        window.open(detail.download_url, '_blank')
      }
    } catch {
      // If fetching fails, the report may have expired presigned URL
      alert('Unable to download. Please try again.')
    }
  }

  const handleShare = (reportId: string) => {
    const report = reports.find((r) => r.report_id === reportId)
    if (report) {
      setShareReportId(reportId)
      setShareReportTitle(`${report.customer_name} - ${report.operation_name}`)
    }
  }

  const handleView = (reportId: string) => {
    navigate(`/reports/${reportId}/preview`)
  }

  const handleNewReportSuccess = (_result: ReportGenerateResponse) => {
    // Refresh reports list after successful generation
    loadReports()
  }

  const handleCloseNewForm = () => {
    setShowNewForm(false)
    loadReports() // Refresh in case something was generated
  }

  // ── Loading ──
  if (isLoading && reports.length === 0) {
    return <ReportsSkeleton />
  }

  // ── Empty state ──
  const activeReports = reports.filter((r) => r.status !== 'deleted')

  return (
    <div className="space-y-4 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-navy">My Reports</h2>
          <p className="text-sm text-muted-foreground">
            Customer visit reports & assessments
          </p>
        </div>
        <button
          onClick={() => setShowNewForm(true)}
          className="tap-target flex items-center gap-2 rounded-lg bg-accent px-3 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover sm:px-4"
        >
          <Plus className="h-4 w-4" />
          <span className="hidden sm:inline">New Report</span>
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Reports list */}
      {activeReports.length === 0 ? (
        <div className="rounded-xl border bg-white p-8 text-center" data-testid="empty-state">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-accent/10">
            <FileText className="h-7 w-7 text-accent" />
          </div>
          <p className="font-medium text-navy">No reports yet.</p>
          <p className="mt-2 max-w-xs mx-auto text-sm text-muted-foreground">
            After your next farm visit, create a report to share with your customer.
          </p>
          <button
            onClick={() => setShowNewForm(true)}
            className="tap-target mt-4 rounded-lg bg-accent px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
            data-testid="create-first-report-btn"
          >
            Create Your First Report
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {activeReports.map((report) => (
            <ReportCard
              key={report.report_id}
              report={report}
              onDownload={handleDownload}
              onShare={handleShare}
              onView={handleView}
            />
          ))}
        </div>
      )}

      {/* Polling indicator */}
      {reports.some((r) => r.status === 'generating') && (
        <div className="flex items-center justify-center gap-2 py-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Checking for updates...
        </div>
      )}

      {/* Toast for completed reports */}
      {completedToast && (
        <div className="fixed left-1/2 top-20 z-[70] -translate-x-1/2 rounded-lg bg-green-600 px-4 py-2.5 text-sm font-medium text-white shadow-lg">
          &#10003; {completedToast}
        </div>
      )}

      {/* New Report Form */}
      {showNewForm && (
        <NewReportForm
          onClose={handleCloseNewForm}
          onSuccess={handleNewReportSuccess}
        />
      )}

      {/* Share Modal */}
      {shareReportId && (
        <ShareReportModal
          reportId={shareReportId}
          reportTitle={shareReportTitle}
          onClose={() => setShareReportId(null)}
          onShared={() => {
            setShareReportId(null)
            loadReports()
          }}
        />
      )}
    </div>
  )
}
