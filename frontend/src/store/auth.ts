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
          .select('id, full_name, role, location_id, customer_operation, active')
          .eq('id', data.user.id)
          .single()

        if (profileData) {
          set({
            profile: profileData as UserProfile,
            role: profileData.role,
            isLoading: false,
          })
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
    try {
      const { data: { session } } = await supabase.auth.getSession()

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
        .select('id, full_name, role, location_id, customer_operation, active')
        .eq('id', session.user.id)
        .single()

      if (profileData) {
        set({
          profile: profileData as UserProfile,
          role: profileData.role,
          isLoading: false,
        })
      } else {
        set({ role: 'consultant', isLoading: false })
      }
    } catch {
      set({ isLoading: false })
    }

    // Listen for auth state changes (session refresh, logout from other tab)
    supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        get().logout()
      }
    })
  },

  setLocationCode: (code) => set({ locationCode: code }),
  clearError: () => set({ error: null }),
}))
