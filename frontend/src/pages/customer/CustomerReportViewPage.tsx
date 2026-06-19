/**
 * CustomerReportViewPage — Branded report viewer for customers.
 * Sprint 13: Displays report_content with section parsing, download bar.
 *
 * UX:
 *   - Back button to return to report list
 *   - Report header with operation name, rep info, date
 *   - Parsed report content (sections split by ## or **Section**)
 *   - Sticky download bar at bottom for DOCX
 *   - Loading and error states
 */

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchCustomerReportDetail, type CustomerReportDetail } from '@/lib/api'
import { ArrowLeft, Download, FileText, RefreshCw } from 'lucide-react'

export function CustomerReportViewPage() {
  const { reportId } = useParams<{ reportId: string }>()
  const navigate = useNavigate()

  const [report, setReport] = useState<CustomerReportDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadReport() {
    if (!reportId) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await fetchCustomerReportDetail(reportId)
      setReport(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load report')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadReport()
  }, [reportId])

  function handleDownload() {
    if (report?.download_url) {
      window.open(report.download_url, '_blank', 'noopener')
    }
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

  // ── Loading state ──────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div data-testid="report-view-loading">
        <button
          onClick={() => navigate('/my-reports')}
          className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-navy"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Reports
        </button>
        <div className="animate-pulse space-y-4 rounded-xl border bg-white p-6">
          <div className="h-6 w-2/3 rounded bg-gray-200" />
          <div className="h-4 w-1/3 rounded bg-gray-200" />
          <div className="mt-6 space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-3 rounded bg-gray-200" style={{ width: `${90 - i * 10}%` }} />
            ))}
          </div>
        </div>
      </div>
    )
  }

  // ── Error state ────────────────────────────────────────────────────
  if (error) {
    return (
      <div data-testid="report-view-error">
        <button
          onClick={() => navigate('/my-reports')}
          className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-navy"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Reports
        </button>
        <div className="rounded-xl border border-danger/20 bg-danger/5 p-6 text-center">
          <p className="text-sm font-medium text-danger">Unable to load report</p>
          <p className="mt-1 text-xs text-muted-foreground">{error}</p>
          <button
            onClick={loadReport}
            className="tap-target mt-3 inline-flex items-center gap-2 rounded-lg bg-navy px-4 py-2 text-sm font-medium text-white hover:bg-navy/90"
            data-testid="report-view-retry"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </button>
        </div>
      </div>
    )
  }

  // ── No report found ────────────────────────────────────────────────
  if (!report) {
    return (
      <div data-testid="report-view-not-found">
        <button
          onClick={() => navigate('/my-reports')}
          className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-navy"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Reports
        </button>
        <div className="rounded-xl border bg-white p-8 text-center">
          <p className="text-sm text-muted-foreground">Report not found.</p>
        </div>
      </div>
    )
  }

  // ── Report sections ────────────────────────────────────────────────
  const sections = parseReportSections(report.report_content || '')

  return (
    <div className="pb-20" data-testid="report-view-page">
      {/* Back button */}
      <button
        onClick={() => navigate('/my-reports')}
        className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-navy"
        data-testid="report-view-back"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Reports
      </button>

      {/* Report card */}
      <div className="rounded-xl border bg-white shadow-sm">
        {/* Header */}
        <div className="border-b p-4 sm:p-6">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/10">
              <FileText className="h-5 w-5 text-accent" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-navy" data-testid="report-view-title">
                {report.operation_name}
              </h1>
              {report.rep_name && (
                <p className="mt-0.5 text-sm text-muted-foreground" data-testid="report-view-rep">
                  Prepared by {report.rep_name}
                  {report.rep_title ? `, ${report.rep_title}` : ''}
                </p>
              )}
              <p className="mt-1 text-xs text-muted-foreground/70" data-testid="report-view-date">
                {formatDate(report.created_at)}
              </p>
            </div>
          </div>
        </div>

        {/* Report content */}
        <div className="p-4 sm:p-6" data-testid="report-view-content">
          {sections.length > 0 ? (
            <div className="space-y-5">
              {sections.map((section, idx) => (
                <div key={idx}>
                  {section.heading && (
                    <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-navy">
                      {section.heading}
                    </h2>
                  )}
                  <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-700">
                    {section.body}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground italic">
              Report content is being prepared. Please check back shortly.
            </p>
          )}
        </div>
      </div>

      {/* ── Sticky download bar ─────────────────────────────────────── */}
      {report.download_url && (
        <div
          className="fixed inset-x-0 bottom-0 z-40 border-t bg-white p-3 shadow-lg"
          data-testid="report-download-bar"
        >
          <div className="mx-auto max-w-3xl">
            <button
              onClick={handleDownload}
              className="tap-target flex w-full items-center justify-center gap-2 rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent/90"
              data-testid="report-download-btn"
            >
              <Download className="h-4 w-4" />
              Download Full Report (DOCX)
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Section parser ────────────────────────────────────────────────────────

interface ReportSection {
  heading: string | null
  body: string
}

function parseReportSections(content: string): ReportSection[] {
  if (!content.trim()) return []

  // Split by ## headings or **Bold Heading** at start of line
  const lines = content.split('\n')
  const sections: ReportSection[] = []
  let currentHeading: string | null = null
  let currentBody: string[] = []

  for (const line of lines) {
    // Check for ## Heading
    const h2Match = line.match(/^##\s+(.+)$/)
    // Check for **Bold Heading** on its own line
    const boldMatch = line.match(/^\*\*([^*]+)\*\*\s*$/)

    if (h2Match || boldMatch) {
      // Push previous section
      if (currentBody.length > 0 || currentHeading) {
        sections.push({
          heading: currentHeading,
          body: currentBody.join('\n').trim(),
        })
      }
      currentHeading = (h2Match?.[1] || boldMatch?.[1] || '').trim()
      currentBody = []
    } else {
      // Strip markdown bold inline
      currentBody.push(line.replace(/\*\*([^*]+)\*\*/g, '$1'))
    }
  }

  // Push last section
  if (currentBody.length > 0 || currentHeading) {
    sections.push({
      heading: currentHeading,
      body: currentBody.join('\n').trim(),
    })
  }

  return sections
}
