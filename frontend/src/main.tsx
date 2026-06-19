/**
 * Bower Ag CowCare Tool — Entry Point
 * Sprint 16: Sentry error monitoring + production-ready initialization.
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import * as Sentry from '@sentry/react'
import { useAuthStore } from '@/store/auth'
import './index.css'
import App from './App.tsx'

// ─── Sentry Initialization (optional — only if DSN configured) ──────────────
const sentryDsn = import.meta.env.VITE_SENTRY_DSN
if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    environment: import.meta.env.MODE,
    release: import.meta.env.VITE_APP_VERSION || '0.0.1',
    tracesSampleRate: 0.1,
    // Don't send in development unless explicitly configured
    enabled: import.meta.env.PROD || !!sentryDsn,
  })
}

// ─── React Query Client ─────────────────────────────────────────────────────
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
})

// Initialize auth session on app load
useAuthStore.getState().initialize()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
