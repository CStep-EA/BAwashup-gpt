/**
 * BugReportSheet — Slide-up sheet (mobile) / modal (desktop)
 * Sprint 7: Title, what happened, expected, severity buttons.
 * Auto-attaches: role, location, app_version, conversation_id.
 */

import { useState } from 'react'
import { X, Bug, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { submitBugReport } from '@/lib/api'
import { useChatStore } from '@/store/chat'
import { useAuthStore } from '@/store/auth'

const SEVERITIES = ['critical', 'high', 'medium', 'low'] as const
type Severity = (typeof SEVERITIES)[number]

const SEVERITY_COLORS: Record<Severity, string> = {
  critical: 'bg-danger/10 text-danger border-danger/30',
  high: 'bg-warning/10 text-warning border-warning/30',
  medium: 'bg-accent/10 text-accent border-accent/30',
  low: 'bg-gray-100 text-gray-600 border-gray-200',
}

interface BugReportSheetProps {
  messageId?: string
  onClose: () => void
}

export function BugReportSheet({ messageId, onClose }: BugReportSheetProps) {
  const { sessionId, locationCode } = useChatStore()
  const { role } = useAuthStore()

  const [title, setTitle] = useState('')
  const [whatHappened, setWhatHappened] = useState('')
  const [expected, setExpected] = useState('')
  const [severity, setSeverity] = useState<Severity>('medium')
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = title.trim().length >= 3 && whatHappened.trim().length >= 10

  const handleSubmit = async () => {
    if (!canSubmit) return
    setSubmitting(true)
    setError(null)

    try {
      await submitBugReport(
        {
          title: title.trim(),
          what_happened: whatHappened.trim(),
          expected_behavior: expected.trim() || undefined,
          severity,
          conversation_id: messageId,
          session_id: sessionId,
        },
        sessionId,
      )
      setSuccess(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit bug report')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-50 bg-black/40" onClick={onClose} />

      {/* Sheet / Modal */}
      <div className="fixed inset-x-0 bottom-0 z-50 max-h-[90vh] overflow-y-auto rounded-t-2xl bg-white p-5 pb-8 shadow-xl lg:inset-auto lg:left-1/2 lg:top-1/2 lg:w-full lg:max-w-lg lg:-translate-x-1/2 lg:-translate-y-1/2 lg:rounded-2xl lg:pb-5">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bug className="h-5 w-5 text-warning" />
            <h3 className="text-base font-bold text-navy">Report an Issue</h3>
          </div>
          <button
            onClick={onClose}
            className="tap-target flex h-8 w-8 items-center justify-center rounded-full hover:bg-gray-100"
          >
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        {success ? (
          <div className="py-8 text-center">
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-success/10">
              <span className="text-2xl">✓</span>
            </div>
            <p className="font-medium text-navy">Thanks for the report!</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Got it — we'll look into this. Thanks for helping make CowCare better.
            </p>
            <button
              onClick={onClose}
              className="tap-target mt-4 rounded-lg bg-navy px-6 py-2.5 text-sm font-medium text-white"
            >
              Close
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Title */}
            <div>
              <label className="mb-1 block text-sm font-medium text-navy">
                Title <span className="text-danger">*</span>
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Brief description of the issue"
                className="w-full rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
                style={{ fontSize: '16px' }}
                maxLength={200}
              />
            </div>

            {/* What happened */}
            <div>
              <label className="mb-1 block text-sm font-medium text-navy">
                What happened? <span className="text-danger">*</span>
              </label>
              <textarea
                value={whatHappened}
                onChange={(e) => setWhatHappened(e.target.value)}
                placeholder="Describe what you were doing and what went wrong…"
                rows={3}
                className="w-full resize-none rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
                style={{ fontSize: '16px' }}
                maxLength={2000}
              />
            </div>

            {/* Expected behavior */}
            <div>
              <label className="mb-1 block text-sm font-medium text-navy">
                What did you expect? <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                value={expected}
                onChange={(e) => setExpected(e.target.value)}
                placeholder="What should have happened instead…"
                rows={2}
                className="w-full resize-none rounded-lg border px-3 py-2.5 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
                style={{ fontSize: '16px' }}
                maxLength={2000}
              />
            </div>

            {/* Severity */}
            <div>
              <label className="mb-2 block text-sm font-medium text-navy">Severity</label>
              <div className="flex gap-2">
                {SEVERITIES.map((s) => (
                  <button
                    key={s}
                    onClick={() => setSeverity(s)}
                    className={cn(
                      'tap-target flex-1 rounded-lg border px-2 py-2 text-xs font-semibold capitalize transition-all',
                      severity === s
                        ? SEVERITY_COLORS[s]
                        : 'border-gray-200 text-gray-400 hover:border-gray-300'
                    )}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* Auto-attached context note */}
            <p className="text-[10px] text-gray-400">
              Auto-attached: role={role}, location={locationCode || 'none'}, version=v1.0-beta
            </p>

            {/* Error */}
            {error && (
              <p className="rounded-lg bg-danger/5 px-3 py-2 text-xs text-danger">{error}</p>
            )}

            {/* Submit */}
            <button
              onClick={handleSubmit}
              disabled={!canSubmit || submitting}
              className="tap-target w-full rounded-lg bg-navy py-3 text-sm font-semibold text-white transition-colors hover:bg-navy-light disabled:opacity-50"
            >
              {submitting ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Submitting…
                </span>
              ) : (
                'Submit Report'
              )}
            </button>
          </div>
        )}
      </div>
    </>
  )
}
