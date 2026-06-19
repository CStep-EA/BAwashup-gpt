/**
 * AppSkeleton — Full-page loading skeleton
 * Shown by AuthGuard while session is being validated.
 * Mimics the AppLayout structure for zero-shift loading.
 */

import { Skeleton } from '@/components/ui/skeleton'

export function AppSkeleton() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      {/* Header skeleton */}
      <div className="flex h-14 items-center gap-3 bg-navy px-4">
        <Skeleton className="h-8 w-8 rounded-full bg-white/10" />
        <div className="space-y-1">
          <Skeleton className="h-4 w-24 bg-white/10" />
          <Skeleton className="h-3 w-16 bg-white/10" />
        </div>
      </div>

      {/* Main content skeleton */}
      <div className="flex-1 p-4">
        <div className="mx-auto max-w-lg space-y-4">
          {/* Stat cards skeleton */}
          <div className="grid grid-cols-2 gap-3">
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
          </div>
          <Skeleton className="h-24 rounded-xl" />

          {/* List skeleton */}
          <div className="space-y-3">
            <Skeleton className="h-5 w-32" />
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 rounded-xl" />
            ))}
          </div>
        </div>
      </div>

      {/* Bottom nav skeleton — visible on mobile only */}
      <div className="flex h-16 items-center justify-around border-t bg-white px-4 lg:hidden">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex flex-col items-center gap-1">
            <Skeleton className="h-5 w-5 rounded" />
            <Skeleton className="h-3 w-8" />
          </div>
        ))}
      </div>
    </div>
  )
}
