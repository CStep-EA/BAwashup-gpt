/**
 * AuthGuard — redirects to /login if not authenticated.
 * Shows loading skeleton while checking session.
 */

import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { AppSkeleton } from '@/components/layout/AppSkeleton'

export function AuthGuard() {
  const { isAuthenticated, isLoading } = useAuthStore()

  if (isLoading) return <AppSkeleton />
  if (!isAuthenticated) return <Navigate to="/login" replace />

  return <Outlet />
}
