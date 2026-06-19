/**
 * CustomerReportCard — Single report card for the customer portal.
 * Sprint 13: Clean, warm card showing operation name, rep name, date, and actions.
 *
 * Governance: No internal fields exposed (no location_code, no pricing flags).
 */

import { FileText, Download, Eye } from 'lucide-react'
import type { CustomerReportSummary } from '@/lib/api'

interface CustomerReportCardProps {
  report: CustomerReportSummary
  onView: (reportId: string) => void
}

export function CustomerReportCard({ report, onView }: CustomerReportCardProps) {
  const formattedDate = formatDate(report.created_at)

  return (
    <div
      className="rounded-xl border bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
      data-testid={`customer-report-card-${report.report_id}`}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/10">
          <FileText className="h-5 w-5 text-accent" />
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-navy" data-testid="report-operation-name">
            {report.operation_name}
          </h3>
          {report.rep_name && (
            <p className="mt-0.5 text-xs text-muted-foreground" data-testid="report-rep-name">
              Prepared by {report.rep_name}
            </p>
          )}
          <p className="mt-1 text-[11px] text-muted-foreground/70" data-testid="report-date">
            {formattedDate}
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="mt-3 flex gap-2">
        <button
          onClick={() => onView(report.report_id)}
          className="tap-target flex flex-1 items-center justify-center gap-2 rounded-lg bg-accent px-3 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent/90"
          data-testid={`view-report-${report.report_id}`}
        >
          <Eye className="h-4 w-4" />
          View Report
        </button>
        {report.has_download && (
          <button
            onClick={() => onView(report.report_id)}
            className="tap-target flex items-center justify-center rounded-lg border px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-gray-50"
            data-testid={`download-hint-${report.report_id}`}
            aria-label="Download report"
          >
            <Download className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}
