/**
 * MyReportsPage — Customer-only report view
 * Shows reports shared with the logged-in customer.
 * Sprint 6: Shell with skeleton. Full data wiring later.
 */

import { useState, useEffect } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { FileText, Download } from 'lucide-react'
import { useAuthStore } from '@/store/auth'

function MyReportsSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <Skeleton className="h-7 w-40" />
      <Skeleton className="h-4 w-56" />
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    </div>
  )
}

export function MyReportsPage() {
  const { profile } = useAuthStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 600)
    return () => clearTimeout(timer)
  }, [])

  if (loading) return <MyReportsSkeleton />

  return (
    <div className="space-y-4 p-4">
      <div>
        <h2 className="text-xl font-bold text-navy">My Reports</h2>
        <p className="text-sm text-muted-foreground">
          Reports shared with {profile?.customer_operation || 'your operation'}
        </p>
      </div>

      {/* Empty state */}
      <div className="rounded-xl border bg-white p-8 text-center">
        <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-accent/10">
          <FileText className="h-7 w-7 text-accent" />
        </div>
        <p className="font-medium text-navy">No reports shared yet</p>
        <p className="mt-2 max-w-xs mx-auto text-sm text-muted-foreground">
          Your Bower Ag representative will share visit reports and
          recommendations here after each assessment.
        </p>
        <div className="mt-4 flex items-center justify-center gap-1 text-xs text-muted-foreground">
          <Download className="h-3 w-3" />
          <span>Reports will be downloadable as PDF</span>
        </div>
      </div>
    </div>
  )
}
