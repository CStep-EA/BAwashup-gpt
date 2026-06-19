/**
 * ReportPreviewPage — In-app branded report preview.
 * Sprint 10: Renders report content in a clean, branded layout.
 *
 * Route: /reports/:reportId/preview
 * Used by reps before sharing, and by customers in the customer portal.
 * Download DOCX button is sticky on mobile.
 */

import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, Loader2, AlertCircle } from 'lucide-react'
import { fetchReportDetail } from '@/lib/api'
import type { ReportDetailResponse } from '@/lib/api'
import { LOCATIONS } from '@/store/chat'

// ─── Content Renderer ────────────────────────────────────────────────────────

// Exported for future use when report_content is added to the API response
export function ReportContent({ content }: { content: string }) {
  // Parse markdown-style sections: ## Header, **bold**, numbered lists
  const lines = content.split('\n')
  const elements: React.ReactElement[] = []

  lines.forEach((line, i) => {
    const trimmed = line.trim()
    if (!trimmed) {
      elements.push(<div key={i} className="h-3" />)
    } else if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={i} className="mt-6 mb-2 text-lg font-bold text-navy">
          {trimmed.slice(3)}
        </h2>,
      )
    } else if (/^\d+\.\s/.test(trimmed)) {
      elements.push(
        <p key={i} className="ml-4 mb-1 text-sm leading-relaxed text-gray-700">
          {trimmed}
        </p>,
      )
    } else if (trimmed.startsWith('- ')) {
      elements.push(
        <p key={i} className="ml-4 mb-1 text-sm leading-relaxed text-gray-700">
          {'\u2022 '}{trimmed.slice(2)}
        </p>,
      )
    } else {
      elements.push(
        <p key={i} className="mb-2 text-sm leading-relaxed text-gray-700">
          {trimmed}
        </p>,
      )
    }
  })

  return <div>{elements}</div>
}

// ─── Page ────────────────────────────────────────────────────────────────────

export function ReportPreviewPage() {
  const { reportId } = useParams<{ reportId: string }>()
  const navigate = useNavigate()
  const [report, setReport] = useState<ReportDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!reportId) return
    setLoading(true)
    fetchReportDetail(reportId)
      .then((data) => setReport(data))
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load report'))
      .finally(() => setLoading(false))
  }, [reportId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="flex flex-col items-center py-20 text-center px-4">
        <AlertCircle className="h-10 w-10 text-red-400" />
        <p className="mt-3 text-base font-medium text-navy">Unable to load report</p>
        <p className="mt-1 text-sm text-muted-foreground">{error || 'Report not found.'}</p>
        <button
          onClick={() => navigate(-1)}
          className="tap-target mt-4 rounded-lg border border-gray-200 px-4 py-2.5 text-sm font-medium text-navy hover:bg-gray-50"
        >
          Go Back
        </button>
      </div>
    )
  }

  const locationName = LOCATIONS[report.location_code] || report.location_code
  const dateStr = new Date(report.created_at).toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })

  return (
    <div className="flex flex-col min-h-full">
      {/* Header bar */}
      <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-4 py-3">
        <button
          onClick={() => navigate(-1)}
          className="tap-target flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-medium text-navy hover:bg-gray-50"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Reports
        </button>
      </div>

      {/* Report content */}
      <div className="flex-1 px-4 pb-24">
        {/* Branded header */}
        <div className="mt-6 rounded-t-xl bg-navy px-5 py-4">
          <p className="text-lg font-bold tracking-wide text-white">BOWER AG</p>
          <p className="text-sm text-white/70">Cow Care Assessment Report</p>
        </div>

        {/* Report meta */}
        <div className="rounded-b-xl border border-t-0 border-gray-200 bg-white px-5 py-4">
          <h1 className="text-xl font-bold text-navy">{report.operation_name}</h1>
          <p className="mt-1 text-base text-navy/80">{report.customer_name}</p>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <span>{locationName}</span>
            <span>{dateStr}</span>
          </div>
          {report.rep_name && (
            <p className="mt-2 text-sm text-muted-foreground">
              Prepared by: {report.rep_name}
              {report.rep_title && `, ${report.rep_title}`}
            </p>
          )}
        </div>

        {/* Body content — the report_content isn't in detail response yet, show placeholder */}
        <div className="mt-6 space-y-1">
          {report.status === 'complete' ? (
            <div className="rounded-xl border border-gray-200 bg-white px-5 py-4">
              <p className="text-sm text-muted-foreground italic">
                Full report content is available in the downloaded DOCX file.
                The preview will be enhanced in a future sprint when report_content
                is included in the API response.
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4">
              <p className="text-sm text-amber-800">
                This report is still {report.status}. Please check back shortly.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Sticky download footer */}
      {report.download_url && report.status === 'complete' && (
        <div className="fixed bottom-0 left-0 right-0 border-t bg-white p-4 shadow-lg lg:sticky">
          <a
            href={report.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="tap-target flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
          >
            <Download className="h-4 w-4" />
            Download Report (DOCX)
          </a>
        </div>
      )}
    </div>
  )
}
