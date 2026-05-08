/**
 * Bower Ag CowCare Tool — Auth Store (Zustand)
 * Manages user session, profile, role, and location state.
 */

import { create } from 'zustand'

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

  // Actions
  setUser: (user: AuthState['user']) => void
  setProfile: (profile: UserProfile | null) => void
  setLoading: (loading: boolean) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  profile: null,
  role: null,
  locationCode: null,
  isLoading: true,
  isAuthenticated: false,

  setUser: (user) =>
    set({
      user,
      isAuthenticated: !!user,
    }),

  setProfile: (profile) =>
    set({
      profile,
      role: profile?.role ?? null,
    }),

  setLoading: (isLoading) => set({ isLoading }),

  logout: () =>
    set({
      user: null,
      profile: null,
      role: null,
      locationCode: null,
      isAuthenticated: false,
    }),
}))
