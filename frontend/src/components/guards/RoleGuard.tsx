/**
 * RoleGuard — shows 403 page (not redirect) if wrong role.
 */

import { Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { ForbiddenPage } from '@/pages/ForbiddenPage'

interface Props {
  allowedRoles: string[]
}

export function RoleGuard({ allowedRoles }: Props) {
  const { role } = useAuthStore()

  if (!role || !allowedRoles.includes(role)) {
    return <ForbiddenPage />
  }

  return <Outlet />
}
