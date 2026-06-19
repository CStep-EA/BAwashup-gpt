/**
 * Bower Ag CowCare Tool — Chat Store (Zustand)
 * Sprint 7: Conversation state in memory only (security requirement).
 *
 * NO browser persistence — history stays in React state only.
 * Session IDs generated per conversation for location locking.
 */

import { create } from 'zustand'
import type { ConversationResponse } from '@/lib/api'

// ─── Types ──────────────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  // Assistant-only metadata
  domain?: string
  governanceApplied?: boolean
  locationLocked?: string | null
  needsLocation?: boolean
  llmCalled?: boolean
  inputTokens?: number | null
  outputTokens?: number | null
  // Feedback state
  feedbackRating?: -1 | 1
  feedbackComment?: string
}

interface ChatState {
  messages: ChatMessage[]
  sessionId: string
  locationCode: string | null
  locationName: string | null
  isStreaming: boolean
  error: string | null

  // Actions
  addUserMessage: (content: string) => string
  addAssistantMessage: (content: string, meta: Partial<ConversationResponse>) => string
  addLoadingMessage: () => string
  removeLoadingMessage: () => void
  setFeedback: (messageId: string, rating: -1 | 1, comment?: string) => void
  setLocation: (code: string, name: string) => void
  clearLocation: () => void
  setStreaming: (streaming: boolean) => void
  setError: (error: string | null) => void
  newConversation: () => void
  getHistory: () => { role: 'user' | 'assistant'; content: string }[]
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function generateId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
}

// ─── Location map ───────────────────────────────────────────────────────────

export const LOCATIONS: Record<string, string> = {
  EVANS: 'Evans CO',
  ULYSSES: 'Ulysses KS',
  JEROME: 'Jerome ID',
  TURLOCK: 'Turlock CA',
  TULARE: 'Tulare CA',
}

// ─── Store ──────────────────────────────────────────────────────────────────

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  sessionId: generateSessionId(),
  locationCode: null,
  locationName: null,
  isStreaming: false,
  error: null,

  addUserMessage: (content) => {
    const id = generateId()
    set((s) => ({
      messages: [
        ...s.messages,
        {
          id,
          role: 'user',
          content,
          timestamp: Date.now(),
        },
      ],
      error: null,
    }))
    return id
  },

  addAssistantMessage: (content, meta) => {
    const id = generateId()
    set((s) => ({
      messages: [
        ...s.messages,
        {
          id,
          role: 'assistant',
          content,
          timestamp: Date.now(),
          domain: meta.domain,
          governanceApplied: meta.governance_applied,
          locationLocked: meta.location_locked,
          needsLocation: meta.needs_location,
          llmCalled: meta.llm_called,
          inputTokens: meta.input_tokens,
          outputTokens: meta.output_tokens,
        },
      ],
    }))
    return id
  },

  addLoadingMessage: () => {
    const id = 'loading'
    set((s) => ({
      messages: [
        ...s.messages,
        {
          id,
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
        },
      ],
    }))
    return id
  },

  removeLoadingMessage: () => {
    set((s) => ({
      messages: s.messages.filter((m) => m.id !== 'loading'),
    }))
  },

  setFeedback: (messageId, rating, comment) => {
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === messageId
          ? { ...m, feedbackRating: rating, feedbackComment: comment }
          : m
      ),
    }))
  },

  setLocation: (code, name) => {
    set({ locationCode: code, locationName: name })
  },

  clearLocation: () => {
    set({ locationCode: null, locationName: null })
  },

  setStreaming: (streaming) => set({ isStreaming: streaming }),

  setError: (error) => set({ error }),

  newConversation: () => {
    set({
      messages: [],
      sessionId: generateSessionId(),
      locationCode: null,
      locationName: null,
      isStreaming: false,
      error: null,
    })
  },

  getHistory: () => {
    return get()
      .messages.filter((m) => m.id !== 'loading')
      .map((m) => ({ role: m.role, content: m.content }))
  },
}))
