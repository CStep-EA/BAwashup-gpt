/**
 * Bower Ag CowCare Tool — Auth Store (Zustand)
 * Sprint 6: Full auth lifecycle — login, logout, initialize from session.
 *
 * State: {user, profile, role, locationCode, isLoading}
 * Actions: login(email, pass), logout(), initialize()
 */

import { create } from 'zustand'
import { supabase } from '@/lib/supabase'

interface UserProfile {
  id: string
  full_name: string | null
  role: string
  location_id: string | null
  customer_operation: string | null
  active: boolean
  must_change_password?: boolean
}

interface AuthState {
  user: { id: string; email: string } | null
  profile: UserProfile | null
  role: string | null
  locationCode: string | null
  isLoading: boolean
  isAuthenticated: boolean
  error: string | null

  // Actions
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  initialize: () => Promise<void>
  setLocationCode: (code: string | null) => void
  clearError: () => void
}

/**
 * Detect if the current URL contains a Supabase recovery token.
 * Supabase embeds tokens in the hash fragment: #access_token=xxx&type=recovery
 * OR in query params after PKCE flow: ?type=recovery&code=xxx
 */
function isRecoveryUrl(): boolean {
  const hash = window.location.hash
  const search = window.location.search
  // Hash-based: #access_token=xxx&type=recovery
  if (hash && hash.includes('type=recovery')) {
    return true
  }
  // Query-based (PKCE): ?type=recovery or ?type=recovery&code=xxx
  if (search && search.includes('type=recovery')) {
    return true
  }
  return false
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  profile: null,
  role: null,
  locationCode: null,
  isLoading: true,
  isAuthenticated: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (error) {
        set({ isLoading: false, error: error.message })
        return
      }

      if (data.user) {
        const user = { id: data.user.id, email: data.user.email || '' }
        set({ user, isAuthenticated: true })

        // Fetch profile
        const { data: profileData } = await supabase
          .from('profiles')
          .select('id, full_name, role, location_id, customer_operation, active, must_change_password')
          .eq('id', data.user.id)
          .single()

        if (profileData) {
          set({
            profile: profileData as UserProfile,
            role: profileData.role,
            isLoading: false,
          })

          // Force password change if admin-set temporary password
          if (profileData.must_change_password) {
            window.location.href = '/reset-password?forced=true'
            return
          }
        } else {
          // Default to consultant if no profile
          set({
            role: 'consultant',
            isLoading: false,
          })
        }
      }
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Login failed',
      })
    }
  },

  logout: async () => {
    await supabase.auth.signOut()
    set({
      user: null,
      profile: null,
      role: null,
      locationCode: null,
      isAuthenticated: false,
      error: null,
    })
  },

  initialize: async () => {
    set({ isLoading: true })

    // ─── EARLY DETECTION: Recovery token in URL ───────────────────────
    // If the URL contains a recovery token (from email reset link),
    // we must redirect to /reset-password BEFORE processing the session.
    // This handles the case where Supabase redirects to "/" instead of "/reset-password"
    // (e.g., if redirect_to isn't whitelisted in Supabase Dashboard).
    const currentPath = window.location.pathname
    const onResetPage = currentPath === '/reset-password'

    if (isRecoveryUrl() && !onResetPage) {
      // Preserve the hash/search params so ResetPasswordPage can process the token
      window.location.href = '/reset-password' + window.location.hash
      return
    }

    // If we're on the reset page with a recovery URL, don't process as normal auth
    if (isRecoveryUrl() && onResetPage) {
      set({ isLoading: false })
      return
    }

    // ─── Register auth state change listener FIRST ────────────────────
    // This must be before getSession() so we don't miss the PASSWORD_RECOVERY event
    // that Supabase fires when processing the hash fragment.
    let recoveryDetected = false

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'PASSWORD_RECOVERY') {
        recoveryDetected = true
        // Redirect to reset password page if not already there
        if (window.location.pathname !== '/reset-password') {
          window.location.href = '/reset-password'
        }
        return
      }

      if (!session && event === 'SIGNED_OUT') {
        get().logout()
      }
    })

    try {
      const { data: { session } } = await supabase.auth.getSession()

      // If PASSWORD_RECOVERY was detected during getSession(), bail out
      // (the redirect is already happening)
      if (recoveryDetected) {
        set({ isLoading: false })
        return
      }

      if (!session?.user) {
        set({ isLoading: false })
        return
      }

      const user = {
        id: session.user.id,
        email: session.user.email || '',
      }
      set({ user, isAuthenticated: true })

      // Fetch profile
      const { data: profileData } = await supabase
        .from('profiles')
        .select('id, full_name, role, location_id, customer_operation, active, must_change_password')
        .eq('id', session.user.id)
        .single()

      if (profileData) {
        set({
          profile: profileData as UserProfile,
          role: profileData.role,
          isLoading: false,
        })

        // Force password change if flagged
        if (profileData.must_change_password && currentPath !== '/reset-password') {
          window.location.href = '/reset-password?forced=true'
          return
        }
      } else {
        set({ role: 'consultant', isLoading: false })
      }
    } catch {
      set({ isLoading: false })
    }

    // Clean up subscription on page unload (though in practice
    // this store lives for the app lifetime)
    void subscription
  },

  setLocationCode: (code) => set({ locationCode: code }),
  clearError: () => set({ error: null }),
}))
