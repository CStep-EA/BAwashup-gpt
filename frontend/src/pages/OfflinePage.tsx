/**
 * OfflinePage — PWA offline fallback
 * Shown when the app is offline and no cached page is available.
 */

import { WifiOff, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function OfflinePage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-warning/10">
          <WifiOff className="h-8 w-8 text-warning" />
        </div>
        <h1 className="text-2xl font-bold text-navy">You're Offline</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          CowCare Tool needs an internet connection to access product data
          and governance information. Please check your connection and try again.
        </p>
        <Button
          className="tap-target mt-6 h-12 w-full gap-2 bg-navy text-white hover:bg-navy-light"
          onClick={() => window.location.reload()}
        >
          <RefreshCw className="h-4 w-4" />
          Try Again
        </Button>
        <p className="mt-6 text-xs text-muted-foreground">
          Tip: Make sure you're connected to WiFi or have cellular data.
        </p>
      </div>
    </div>
  )
}
