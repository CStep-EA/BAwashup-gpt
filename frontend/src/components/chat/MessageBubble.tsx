/**
 * MessageBubble — Chat message display
 * Sprint 7: User/assistant bubbles, domain badges, governance citation,
 * feedback buttons, loading dots.
 */

import { useState } from 'react'
import { ThumbsUp, ThumbsDown, Flag } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChatMessage } from '@/store/chat'

// ─── Domain badge config ────────────────────────────────────────────────────

const DOMAIN_BADGES: Record<string, { label: string; className: string }> = {
  PRICING: { label: 'Pricing', className: 'bg-domain-pricing/15 text-domain-pricing' },
  TEAT_DIP: { label: 'Teat Dip', className: 'bg-domain-teat-dip/15 text-domain-teat-dip' },
  CHEMICAL_CIP: { label: 'CIP Chemical', className: 'bg-domain-chemical/15 text-domain-chemical' },
  TROUBLESHOOTING: { label: 'Troubleshooting', className: 'bg-domain-troubleshooting/15 text-domain-troubleshooting' },
  COW_HEALTH: { label: 'Cow Health', className: 'bg-domain-cow-health/15 text-domain-cow-health' },
  UNKNOWN: { label: 'General', className: 'bg-domain-unknown/15 text-domain-unknown' },
}

// ─── Loading dots ───────────────────────────────────────────────────────────

function LoadingDots() {
  return (
    <div className="flex items-center gap-1.5 px-1 py-2">
      <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
    </div>
  )
}

// ─── Props ──────────────────────────────────────────────────────────────────

interface MessageBubbleProps {
  message: ChatMessage
  onFeedback?: (messageId: string, rating: -1 | 1) => void
  onFlagReport?: (messageId: string) => void
  showFeedbackInput?: string | null
  onFeedbackComment?: (messageId: string, comment: string) => void
}

export function MessageBubble({
  message,
  onFeedback,
  onFlagReport,
  showFeedbackInput,
  onFeedbackComment,
}: MessageBubbleProps) {
  const [feedbackText, setFeedbackText] = useState('')
  const isUser = message.role === 'user'
  const isLoading = message.id === 'loading'

  // ── User message ──
  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[85%] rounded-[18px_18px_4px_18px] bg-navy px-4 py-3 text-sm leading-relaxed text-white"
        >
          {message.content}
        </div>
      </div>
    )
  }

  // ── Assistant message ──
  const badge = message.domain ? DOMAIN_BADGES[message.domain] || DOMAIN_BADGES.UNKNOWN : null

  return (
    <div className="flex gap-2.5">
      {/* Avatar */}
      <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent/10 text-sm">
        🐄
      </div>

      <div className="min-w-0 max-w-[85%] space-y-1.5">
        {/* Bubble */}
        <div className="rounded-2xl rounded-tl-md bg-white px-4 py-3 text-sm leading-relaxed text-foreground shadow-sm ring-1 ring-black/5">
          {isLoading ? (
            <LoadingDots />
          ) : (
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
          )}
        </div>

        {/* Metadata row — only for real messages */}
        {!isLoading && (
          <div className="flex flex-wrap items-center gap-1.5 px-1">
            {/* Domain badge */}
            {badge && (
              <span
                className={cn(
                  'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold',
                  badge.className
                )}
              >
                {badge.label}
              </span>
            )}

            {/* Location badge */}
            {message.locationLocked && (
              <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600">
                📍 {message.locationLocked}
              </span>
            )}

            {/* Spacer */}
            <div className="flex-1" />

            {/* Feedback buttons */}
            {onFeedback && (
              <>
                <button
                  onClick={() => onFeedback(message.id, 1)}
                  className={cn(
                    'tap-target flex h-7 w-7 items-center justify-center rounded-md transition-colors',
                    message.feedbackRating === 1
                      ? 'bg-success/10 text-success'
                      : 'text-gray-300 hover:bg-gray-100 hover:text-gray-500'
                  )}
                  aria-label="Thumbs up"
                >
                  <ThumbsUp className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => onFeedback(message.id, -1)}
                  className={cn(
                    'tap-target flex h-7 w-7 items-center justify-center rounded-md transition-colors',
                    message.feedbackRating === -1
                      ? 'bg-danger/10 text-danger'
                      : 'text-gray-300 hover:bg-gray-100 hover:text-gray-500'
                  )}
                  aria-label="Thumbs down"
                >
                  <ThumbsDown className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => onFlagReport?.(message.id)}
                  className="tap-target flex h-7 w-7 items-center justify-center rounded-md text-gray-300 transition-colors hover:bg-gray-100 hover:text-warning"
                  aria-label="Report issue"
                >
                  <Flag className="h-3.5 w-3.5" />
                </button>
              </>
            )}
          </div>
        )}

        {/* Governance citation */}
        {message.governanceApplied && message.locationLocked && (
          <p className="px-1 text-[11px] italic text-gray-400">
            Pricing confirmed: {message.locationLocked} Price Sheet
          </p>
        )}

        {/* Thumbs-down follow-up field */}
        {showFeedbackInput === message.id && message.feedbackRating === -1 && (
          <div className="px-1">
            <div className="flex gap-2 rounded-lg border bg-gray-50 p-2">
              <input
                type="text"
                placeholder="What was wrong? (optional)"
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                className="flex-1 bg-transparent text-xs outline-none placeholder:text-gray-400"
                style={{ fontSize: '16px' }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && feedbackText.trim()) {
                    onFeedbackComment?.(message.id, feedbackText.trim())
                    setFeedbackText('')
                  }
                }}
              />
              <button
                onClick={() => {
                  if (feedbackText.trim()) {
                    onFeedbackComment?.(message.id, feedbackText.trim())
                    setFeedbackText('')
                  }
                }}
                className="shrink-0 rounded-md bg-navy px-2.5 py-1 text-[10px] font-medium text-white"
              >
                Send
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
