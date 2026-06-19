/**
 * CustomerGuard — /my-reports only for customers.
 * Redirects customers away from /chat and /products.
 */

import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'

export function CustomerGuard() {
  const { role } = useAuthStore()

  if (role === 'customer') {
    return <Navigate to="/my-reports" replace />
  }

  return <Outlet />
}
