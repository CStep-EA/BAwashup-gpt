/**
 * ChatPage — Full conversation interface
 * Sprint 7: Location bar + message thread + input bar + feedback + bug reports.
 * Sprint 14: Image/video attachment via paperclip, feature-flag gated.
 *
 * Layout: flex column, full-height.
 *   Top: LocationSelector (fixed)
 *   Middle: message thread (flex-grow, overflow-y auto, auto-scroll)
 *   Bottom: ChatInput (fixed, above bottom nav)
 *
 * Desktop: max-width 800px centered.
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { RotateCcw, MessageSquare } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { useChatStore, LOCATIONS } from '@/store/chat'
import { useAuthStore } from '@/store/auth'
import {
  sendMessage,
  submitFeedback,
  analyzeImage,
  uploadVideo,
  checkFeatureEnabled,
} from '@/lib/api'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { LocationSelector } from '@/components/chat/LocationSelector'
import { ChatInput } from '@/components/chat/ChatInput'
import { BugReportSheet } from '@/components/chat/BugReportSheet'
import { clearLocation as apiClearLocation } from '@/lib/api'

// Roles that can use media pipeline (mirrors backend MEDIA_ROLES)
const MEDIA_ROLES = new Set(['consultant', 'technician', 'admin_manager', 'org_admin'])

const IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/heic', 'image/webp'])

// ─── Skeleton ───────────────────────────────────────────────────────────────

function ChatSkeleton() {
  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col lg:h-[calc(100vh-3.5rem)]">
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        <div className="flex gap-3">
          <Skeleton className="h-8 w-8 shrink-0 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-4 w-64" />
          </div>
        </div>
        <div className="flex justify-end">
          <Skeleton className="h-10 w-48 rounded-2xl" />
        </div>
      </div>
      <div className="border-t bg-white p-3">
        <div className="flex gap-2">
          <Skeleton className="h-12 flex-1 rounded-xl" />
          <Skeleton className="h-12 w-12 rounded-full" />
        </div>
      </div>
    </div>
  )
}

// ─── Empty state ────────────────────────────────────────────────────────────

function EmptyState({ onQuickSend }: { onQuickSend: (q: string) => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center p-4 text-center">
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent/10">
        <MessageSquare className="h-8 w-8 text-accent" />
      </div>
      <h2 className="text-lg font-bold text-navy">Start a Conversation</h2>
      <p className="mt-2 max-w-xs text-sm text-muted-foreground">
        Ask about teat dip products, CIP chemicals, troubleshooting, or
        pricing for a specific location.
      </p>
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {[
          'What teat dips are available?',
          'Show me CIP chemicals for Turlock',
          'High bacteria troubleshooting',
        ].map((q) => (
          <button
            key={q}
            onClick={() => onQuickSend(q)}
            className="tap-target rounded-full border bg-white px-3 py-2 text-xs text-muted-foreground transition-colors hover:border-accent hover:text-accent"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── ChatPage ───────────────────────────────────────────────────────────────

export function ChatPage() {
  const {
    messages,
    sessionId,
    isStreaming,
    error,
    addUserMessage,
    addAssistantMessage,
    addLoadingMessage,
    removeLoadingMessage,
    setFeedback,
    setStreaming,
    setError,
    newConversation,
    getHistory,
    clearLocation,
  } = useChatStore()

  const role = useAuthStore((s) => s.role)
  const navigate = useNavigate()

  const [inputValue, setInputValue] = useState('')
  const [showFeedbackInput, setShowFeedbackInput] = useState<string | null>(null)
  const [bugReportMessageId, setBugReportMessageId] = useState<string | null>(null)
  const [initLoading, setInitLoading] = useState(true)
  const threadRef = useRef<HTMLDivElement>(null)

  // Sprint 14: Media state
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [mediaEnabled, setMediaEnabled] = useState(false)
  const [mediaUploading, setMediaUploading] = useState(false)

  // Initial skeleton
  useEffect(() => {
    const t = setTimeout(() => setInitLoading(false), 400)
    return () => clearTimeout(t)
  }, [])

  // Sprint 14: Check feature flag on mount (only for eligible roles)
  useEffect(() => {
    if (!role || !MEDIA_ROLES.has(role)) {
      setMediaEnabled(false)
      return
    }
    let cancelled = false
    checkFeatureEnabled('feature.video_upload')
      .then((enabled) => {
        if (!cancelled) setMediaEnabled(enabled)
      })
      .catch(() => {
        if (!cancelled) setMediaEnabled(false)
      })
    return () => { cancelled = true }
  }, [role])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight
    }
  }, [messages])

  // ── Send message ──────────────────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    const text = inputValue.trim()
    const file = selectedFile

    // Must have text or file
    if (!text && !file) return
    if (isStreaming || mediaUploading) return

    setInputValue('')
    setSelectedFile(null)

    // If file is attached, handle media upload
    if (file) {
      const isImage = IMAGE_TYPES.has(file.type)

      // Add user message showing what they're sending
      const userText = text || (isImage ? '📷 Analyzing image…' : '🎥 Uploading video for analysis…')
      addUserMessage(userText)

      if (isImage) {
        // ── Sync image analysis ──
        addLoadingMessage()
        setMediaUploading(true)
        setStreaming(true)
        setError(null)

        try {
          const result = await analyzeImage(file, 'general')
          removeLoadingMessage()

          let reply = result.analysis
          if (result.teat_scores && result.teat_scores.length > 0) {
            reply += `\n\nTeat Scores: ${result.teat_scores.join(', ')}`
          }
          if (result.governance_applied) {
            reply += '\n\n_Some product references were adjusted per Bower Ag governance._'
          }

          addAssistantMessage(reply, {
            domain: result.domain.toUpperCase(),
            governance_applied: result.governance_applied,
          })
        } catch (err) {
          removeLoadingMessage()
          addAssistantMessage(
            "I wasn't able to analyze that image right now. Please check your connection and try again.",
            { domain: 'UNKNOWN' },
          )
          setError(err instanceof Error ? err.message : 'Image analysis failed')
        } finally {
          setMediaUploading(false)
          setStreaming(false)
        }
      } else {
        // ── Async video upload ──
        setMediaUploading(true)
        setError(null)

        try {
          const result = await uploadVideo(file)
          addAssistantMessage(
            result.message +
            '\n\nYou can check progress on the job status page.',
            { domain: 'MEDIA' },
          )

          // Navigate to the job status page
          navigate(`/media/jobs/${result.job_id}`)
        } catch (err) {
          addAssistantMessage(
            "I wasn't able to upload that video right now. Please try again or use a smaller file.",
            { domain: 'UNKNOWN' },
          )
          setError(err instanceof Error ? err.message : 'Video upload failed')
        } finally {
          setMediaUploading(false)
        }
      }

      return
    }

    // ── Text-only send ──
    addUserMessage(text)
    addLoadingMessage()
    setStreaming(true)
    setError(null)

    try {
      const history = getHistory().slice(0, -1) // Exclude the loading placeholder
      const res = await sendMessage(
        {
          message: text,
          session_id: sessionId,
          conversation_history: history.filter((m) => m.content),
        },
        sessionId,
      )

      removeLoadingMessage()
      addAssistantMessage(res.reply, res)

      // If location was locked by backend, update chat store
      if (res.location_locked) {
        const name = LOCATIONS[res.location_locked] || res.location_locked
        useChatStore.getState().setLocation(res.location_locked, name)
      }
    } catch (err) {
      removeLoadingMessage()
      addAssistantMessage(
        "I'm running into a technical issue connecting to the server. Please check your connection and try again.",
        { domain: 'UNKNOWN' },
      )
      setError(err instanceof Error ? err.message : 'Connection error')
    } finally {
      setStreaming(false)
    }
  }, [
    inputValue,
    selectedFile,
    isStreaming,
    mediaUploading,
    sessionId,
    navigate,
    addUserMessage,
    addAssistantMessage,
    addLoadingMessage,
    removeLoadingMessage,
    setStreaming,
    setError,
    getHistory,
  ])

  // Quick send from empty state
  const handleQuickSend = useCallback(
    (q: string) => {
      setInputValue(q)
      // Need to defer so state updates before sending
      setTimeout(() => {
        useChatStore.getState().setError(null)
        const addUser = useChatStore.getState().addUserMessage
        const addLoading = useChatStore.getState().addLoadingMessage
        const setStream = useChatStore.getState().setStreaming
        const getHist = useChatStore.getState().getHistory
        const sid = useChatStore.getState().sessionId

        addUser(q)
        addLoading()
        setStream(true)

        sendMessage(
          { message: q, session_id: sid, conversation_history: getHist().slice(0, -1).filter((m) => m.content) },
          sid,
        )
          .then((res) => {
            useChatStore.getState().removeLoadingMessage()
            useChatStore.getState().addAssistantMessage(res.reply, res)
            if (res.location_locked) {
              useChatStore.getState().setLocation(res.location_locked, LOCATIONS[res.location_locked] || res.location_locked)
            }
          })
          .catch(() => {
            useChatStore.getState().removeLoadingMessage()
            useChatStore.getState().addAssistantMessage(
              "I'm running into a technical issue. Please try again.",
              { domain: 'UNKNOWN' },
            )
          })
          .finally(() => {
            useChatStore.getState().setStreaming(false)
          })

        setInputValue('')
      }, 0)
    },
    [],
  )

  // ── Feedback ──────────────────────────────────────────────────────────────
  const handleFeedback = useCallback(
    async (messageId: string, rating: -1 | 1) => {
      setFeedback(messageId, rating)

      if (rating === -1) {
        setShowFeedbackInput(messageId)
      } else {
        setShowFeedbackInput(null)
      }

      try {
        await submitFeedback({
          rating,
          session_id: sessionId,
          conversation_id: messageId,
        })
      } catch {
        // Feedback is best-effort — don't block UX
      }
    },
    [sessionId, setFeedback],
  )

  const handleFeedbackComment = useCallback(
    async (messageId: string, comment: string) => {
      setFeedback(messageId, -1, comment)
      setShowFeedbackInput(null)

      try {
        await submitFeedback({
          rating: -1,
          comment,
          session_id: sessionId,
          conversation_id: messageId,
        })
      } catch {
        // Best-effort
      }
    },
    [sessionId, setFeedback],
  )

  // ── New conversation ──────────────────────────────────────────────────────
  const handleNewConversation = useCallback(async () => {
    try {
      await apiClearLocation(sessionId)
    } catch {
      // Best-effort
    }
    clearLocation()
    newConversation()
    setInputValue('')
    setSelectedFile(null)
    setShowFeedbackInput(null)
    setBugReportMessageId(null)
  }, [sessionId, clearLocation, newConversation])

  // ── File handlers ─────────────────────────────────────────────────────────
  const handleFileSelect = useCallback((file: File) => {
    setSelectedFile(file)
  }, [])

  const handleFileClear = useCallback(() => {
    setSelectedFile(null)
  }, [])

  // ── Render ────────────────────────────────────────────────────────────────

  if (initLoading) return <ChatSkeleton />

  const hasMessages = messages.length > 0

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col lg:h-[calc(100vh-3.5rem)]">
      {/* Location selector + New Conversation */}
      <div className="relative shrink-0">
        <LocationSelector />
        {hasMessages && (
          <button
            onClick={handleNewConversation}
            className="tap-target absolute right-3 top-1/2 z-10 -translate-y-1/2 flex items-center gap-1.5 rounded-lg border bg-white px-2.5 py-1.5 text-xs font-medium text-muted-foreground shadow-sm transition-colors hover:bg-gray-50 hover:text-navy"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">New Chat</span>
          </button>
        )}
      </div>

      {/* Message thread */}
      <div
        ref={threadRef}
        className="flex-1 overflow-y-auto"
      >
        {hasMessages ? (
          <div className="mx-auto max-w-3xl space-y-4 p-4">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onFeedback={msg.role === 'assistant' ? handleFeedback : undefined}
                onFlagReport={(id) => setBugReportMessageId(id)}
                showFeedbackInput={showFeedbackInput}
                onFeedbackComment={handleFeedbackComment}
              />
            ))}
          </div>
        ) : (
          <EmptyState onQuickSend={handleQuickSend} />
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="border-t bg-danger/5 px-4 py-2 text-center text-xs text-danger">
          {error}
        </div>
      )}

      {/* Input bar */}
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSend={handleSend}
        loading={isStreaming || mediaUploading}
        disabled={false}
        mediaEnabled={mediaEnabled}
        onFileSelect={handleFileSelect}
        selectedFile={selectedFile}
        onFileClear={handleFileClear}
      />

      {/* Bug report sheet */}
      {bugReportMessageId !== null && (
        <BugReportSheet
          messageId={bugReportMessageId}
          onClose={() => setBugReportMessageId(null)}
        />
      )}
    </div>
  )
}
