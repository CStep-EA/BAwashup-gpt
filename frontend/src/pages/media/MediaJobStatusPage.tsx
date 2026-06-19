/**
 * MediaJobStatusPage — Video analysis job progress tracker
 * Sprint 14: Polls /media/jobs/{jobId} every 10 seconds.
 *
 * States:
 *   pending    → Queued, waiting for worker
 *   processing → Extracting frames, analyzing with Vision
 *   complete   → Report ready, link to /reports/:reportId/preview
 *   failed     → Error with friendly message + retry hint
 *
 * Mobile-first: warm, practical messaging. 48px tap targets.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  Video,
  Clock,
  Loader2,
  CheckCircle,
  XCircle,
  ArrowLeft,
  FileText,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { fetchMediaJob, type MediaJobResponse } from '@/lib/api'

const POLL_INTERVAL = 10_000 // 10 seconds

type JobStatus = 'pending' | 'processing' | 'complete' | 'failed'

const STATUS_CONFIG: Record<JobStatus, {
  icon: typeof Clock
  label: string
  color: string
  bgColor: string
  description: string
}> = {
  pending: {
    icon: Clock,
    label: 'Queued',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    description: 'Your video is in the queue. Processing will start shortly.',
  },
  processing: {
    icon: Loader2,
    label: 'Analyzing',
    color: 'text-accent',
    bgColor: 'bg-accent/5',
    description: 'We are extracting frames and running our AI analysis. This usually takes 3-5 minutes.',
  },
  complete: {
    icon: CheckCircle,
    label: 'Complete',
    color: 'text-success',
    bgColor: 'bg-success/5',
    description: 'Your video analysis is ready! A report has been generated with our findings.',
  },
  failed: {
    icon: XCircle,
    label: 'Failed',
    color: 'text-danger',
    bgColor: 'bg-danger/5',
    description: 'Something went wrong during analysis. Please try uploading again or contact support.',
  },
}

export function MediaJobStatusPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()

  const [job, setJob] = useState<MediaJobResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchJob = useCallback(async () => {
    if (!jobId) return
    try {
      const data = await fetchMediaJob(jobId)
      setJob(data)
      setError(null)

      // Stop polling when terminal state
      if (data.status === 'complete' || data.status === 'failed') {
        if (pollRef.current) {
          clearInterval(pollRef.current)
          pollRef.current = null
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch job status')
    } finally {
      setLoading(false)
    }
  }, [jobId])

  // Initial fetch + polling
  useEffect(() => {
    fetchJob()
    pollRef.current = setInterval(fetchJob, POLL_INTERVAL)
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
      }
    }
  }, [fetchJob])

  // ── Loading state ──
  if (loading && !job) {
    return (
      <div className="flex h-[calc(100vh-8rem)] flex-col items-center justify-center p-4 lg:h-[calc(100vh-3.5rem)]">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
        <p className="mt-3 text-sm text-muted-foreground">Loading job status…</p>
      </div>
    )
  }

  // ── Error with no data ──
  if (error && !job) {
    return (
      <div className="flex h-[calc(100vh-8rem)] flex-col items-center justify-center p-4 lg:h-[calc(100vh-3.5rem)]">
        <div className="rounded-2xl border bg-white p-6 text-center shadow-sm">
          <XCircle className="mx-auto h-10 w-10 text-danger" />
          <h2 className="mt-3 text-lg font-bold text-navy">Unable to Load Job</h2>
          <p className="mt-2 text-sm text-muted-foreground">{error}</p>
          <button
            onClick={() => navigate('/chat')}
            className="tap-target mt-4 inline-flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Chat
          </button>
        </div>
      </div>
    )
  }

  if (!job) return null

  const status = (job.status as JobStatus) || 'pending'
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending
  const StatusIcon = config.icon

  const createdDate = job.created_at ? new Date(job.created_at) : null
  const completedDate = job.completed_at ? new Date(job.completed_at) : null

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 lg:py-10">
      {/* Back link */}
      <Link
        to="/chat"
        className="tap-target mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-navy"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Chat
      </Link>

      {/* Header */}
      <div className="mb-6 flex items-start gap-3">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent/10">
          <Video className="h-6 w-6 text-accent" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-navy">Video Analysis</h1>
          <p className="text-sm text-muted-foreground">
            Job ID: {jobId?.slice(0, 8)}…
          </p>
        </div>
      </div>

      {/* Status card */}
      <div className={cn('rounded-2xl border p-6 shadow-sm', config.bgColor)}>
        <div className="flex items-center gap-3">
          <StatusIcon
            className={cn(
              'h-6 w-6',
              config.color,
              status === 'processing' && 'animate-spin',
            )}
          />
          <div>
            <h2 className={cn('text-base font-bold', config.color)}>
              {config.label}
            </h2>
          </div>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-foreground">
          {config.description}
        </p>

        {/* Progress info */}
        {(job.frames_extracted || job.frames_analyzed) && (
          <div className="mt-4 grid grid-cols-2 gap-3">
            {job.frames_extracted != null && (
              <div className="rounded-lg bg-white/60 px-3 py-2">
                <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Frames Extracted
                </p>
                <p className="text-lg font-bold text-navy">{job.frames_extracted}</p>
              </div>
            )}
            {job.frames_analyzed != null && (
              <div className="rounded-lg bg-white/60 px-3 py-2">
                <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Frames Analyzed
                </p>
                <p className="text-lg font-bold text-navy">{job.frames_analyzed}</p>
              </div>
            )}
          </div>
        )}

        {/* Error message */}
        {status === 'failed' && job.error_message && (
          <div className="mt-4 rounded-lg bg-white/60 px-3 py-2">
            <p className="text-xs text-danger">{job.error_message}</p>
          </div>
        )}
      </div>

      {/* Timestamps */}
      <div className="mt-4 space-y-1 px-1">
        {createdDate && (
          <p className="text-xs text-muted-foreground">
            Submitted: {createdDate.toLocaleString()}
          </p>
        )}
        {completedDate && (
          <p className="text-xs text-muted-foreground">
            Completed: {completedDate.toLocaleString()}
          </p>
        )}
      </div>

      {/* Action buttons */}
      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        {/* View Report — only when complete */}
        {status === 'complete' && job.result_report_id && (
          <Link
            to={`/reports/${job.result_report_id}/preview`}
            className="tap-target inline-flex items-center justify-center gap-2 rounded-lg bg-accent px-5 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-accent-hover"
          >
            <FileText className="h-4 w-4" />
            View Report
          </Link>
        )}

        {/* Back to Chat */}
        <button
          onClick={() => navigate('/chat')}
          className="tap-target inline-flex items-center justify-center gap-2 rounded-lg border bg-white px-5 py-3 text-sm font-medium text-navy shadow-sm transition-colors hover:bg-gray-50"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Chat
        </button>
      </div>

      {/* Polling indicator */}
      {(status === 'pending' || status === 'processing') && (
        <p className="mt-6 text-center text-[11px] text-muted-foreground">
          Auto-refreshing every 10 seconds…
        </p>
      )}
    </div>
  )
}
