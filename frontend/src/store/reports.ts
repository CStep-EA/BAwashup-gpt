/**
 * Bower Ag CowCare Tool — Reports Store (Zustand)
 * Sprint 10: Report list state with polling for generating status.
 *
 * Polling: When any report has status='generating', polls GET /reports every 5s.
 * Stops automatically when all reports are complete or failed.
 */

import { create } from 'zustand'
import type { ReportSummary } from '@/lib/api'
import { fetchReports } from '@/lib/api'

interface ReportsState {
  reports: ReportSummary[]
  isLoading: boolean
  error: string | null
  pollingInterval: ReturnType<typeof setInterval> | null

  // Toast state for status changes
  completedToast: string | null

  // Actions
  loadReports: () => Promise<void>
  startPolling: () => void
  stopPolling: () => void
  clearToast: () => void
}

export const useReportsStore = create<ReportsState>((set, get) => ({
  reports: [],
  isLoading: false,
  error: null,
  pollingInterval: null,
  completedToast: null,

  loadReports: async () => {
    const state = get()
    // Only show full loading on first load (not polling refreshes)
    if (state.reports.length === 0) {
      set({ isLoading: true })
    }
    set({ error: null })

    try {
      const reports = await fetchReports()

      // Detect newly completed reports for toast
      const prev = state.reports
      const newlyComplete = reports.filter(
        (r) =>
          r.status === 'complete' &&
          prev.find((p) => p.report_id === r.report_id && p.status === 'generating'),
      )
      const toast =
        newlyComplete.length > 0
          ? `${newlyComplete[0].customer_name} report is ready!`
          : null

      set({ reports, isLoading: false, completedToast: toast || state.completedToast })

      // Auto-manage polling based on generating reports
      const hasGenerating = reports.some((r) => r.status === 'generating')
      if (hasGenerating && !state.pollingInterval) {
        get().startPolling()
      } else if (!hasGenerating && state.pollingInterval) {
        get().stopPolling()
      }
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to load reports',
        isLoading: false,
      })
    }
  },

  startPolling: () => {
    const state = get()
    if (state.pollingInterval) return

    const interval = setInterval(() => {
      get().loadReports()
    }, 5000)

    set({ pollingInterval: interval })
  },

  stopPolling: () => {
    const state = get()
    if (state.pollingInterval) {
      clearInterval(state.pollingInterval)
      set({ pollingInterval: null })
    }
  },

  clearToast: () => set({ completedToast: null }),
}))
