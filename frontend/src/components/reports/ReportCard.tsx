/**
 * ReportCard — Individual report card in the reports list.
 * Sprint 10: Status badge, shared badge, action buttons, mobile-first.
 *
 * Status badges: Complete (green), Generating (amber+spinner), Failed (red)
 * All action buttons 44px minimum height for barn-friendly tap targets.
 */

import { Download, Share2, Eye, Loader2 } from 'lucide-react'
import type { ReportSummary } from '@/lib/api'
import { LOCATIONS } from '@/store/chat'

// ─── Status badge ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; className: string; showSpinner?: boolean }> = {
  complete: { label: 'Complete', className: 'bg-green-100 text-green-700' },
  generating: { label: 'Generating...', className: 'bg-amber-100 text-amber-700', showSpinner: true },
  failed: { label: 'Failed', className: 'bg-red-100 text-red-700' },
  deleted: { label: 'Deleted', className: 'bg-gray-100 text-gray-500' },
}

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.failed
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className}`}
      data-testid={`status-badge-${status}`}
    >
      {config.showSpinner && <Loader2 className="h-3 w-3 animate-spin" />}
      {config.label}
    </span>
  )
}

// ─── Component ───────────────────────────────────────────────────────────────

interface ReportCardProps {
  report: ReportSummary
  onDownload: (reportId: string) => void
  onShare: (reportId: string) => void
  onView: (reportId: string) => void
}

export function ReportCard({ report, onDownload, onShare, onView }: ReportCardProps) {
  const locationName = LOCATIONS[report.location_code] || report.location_code
  const dateStr = new Date(report.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

  const isComplete = report.status === 'complete'

  return (
    <div
      className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
      data-testid="report-card"
    >
      {/* Top row: names + status */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-bold text-navy leading-snug truncate">
            {report.customer_name}
          </h3>
          <p className="text-sm text-navy/80 truncate">{report.operation_name}</p>
        </div>
        <StatusBadge status={report.status} />
      </div>

      {/* Meta row */}
      <div className="mt-1.5 flex items-center gap-2 text-[13px] text-muted-foreground">
        <span>{locationName}</span>
        <span aria-hidden="true">·</span>
        <span>{dateStr}</span>
      </div>

      {/* Shared badge */}
      {report.shared_with_customer && (
        <div className="mt-2">
          <span
            className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700"
            data-testid="shared-badge"
          >
            <Share2 className="h-3 w-3" />
            Shared with customer
          </span>
        </div>
      )}

      {/* Action buttons */}
      {isComplete && (
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => onDownload(report.report_id)}
            className="tap-target flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2.5 text-sm font-medium text-navy transition-colors hover:bg-gray-50"
            aria-label={`Download report for ${report.customer_name}`}
          >
            <Download className="h-4 w-4" />
            Download
          </button>
          <button
            onClick={() => onShare(report.report_id)}
            className="tap-target flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2.5 text-sm font-medium text-navy transition-colors hover:bg-gray-50"
            aria-label={`Share report for ${report.customer_name}`}
          >
            <Share2 className="h-4 w-4" />
            Share
          </button>
          <button
            onClick={() => onView(report.report_id)}
            className="tap-target flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2.5 text-sm font-medium text-navy transition-colors hover:bg-gray-50"
            aria-label={`View report for ${report.customer_name}`}
          >
            <Eye className="h-4 w-4" />
            View
          </button>
        </div>
      )}
    </div>
  )
}
