/**
 * ForbiddenPage — 403 Access Denied
 * Shown by RoleGuard when user lacks required role.
 * Uses a clear, helpful message — not a redirect.
 */

import { ShieldX } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { Button } from '@/components/ui/button'
import { useNavigate } from 'react-router-dom'

export function ForbiddenPage() {
  const { role } = useAuthStore()
  const navigate = useNavigate()

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-50">
          <ShieldX className="h-8 w-8 text-danger" />
        </div>
        <h1 className="text-2xl font-bold text-navy">Access Denied</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Your role ({role || 'unknown'}) doesn't have permission to view this page.
          If you think this is an error, contact your administrator.
        </p>
        <div className="mt-6 flex flex-col gap-3">
          <Button
            className="tap-target h-12 w-full bg-navy text-white hover:bg-navy-light"
            onClick={() => navigate(-1)}
          >
            Go Back
          </Button>
          <Button
            variant="outline"
            className="tap-target h-12 w-full"
            onClick={() => navigate('/')}
          >
            Return to Home
          </Button>
        </div>
      </div>
    </div>
  )
}
