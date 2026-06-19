/**
 * NotFoundPage — 404 catch-all
 */

import { MapPin } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useNavigate } from 'react-router-dom'

export function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
          <MapPin className="h-8 w-8 text-muted-foreground" />
        </div>
        <h1 className="text-5xl font-bold text-navy">404</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          This page doesn't exist. Maybe you took a wrong turn on the way to the barn.
        </p>
        <Button
          className="tap-target mt-6 h-12 w-full bg-navy text-white hover:bg-navy-light"
          onClick={() => navigate('/')}
        >
          Back to Dashboard
        </Button>
      </div>
    </div>
  )
}
