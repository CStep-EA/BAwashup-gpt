/**
 * DashboardPage — Landing page for non-customer roles
 * 3 stat cards + recent activity list with skeleton loaders.
 */

import { useState, useEffect } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { MessageSquare, FileText, TrendingUp } from 'lucide-react'
import { useAuthStore } from '@/store/auth'

function DashboardSkeleton() {
  return (
    <div className="space-y-4 p-4">
      {/* Stat cards skeleton */}
      <div className="grid grid-cols-2 gap-3">
        <Skeleton className="h-28 rounded-xl" />
        <Skeleton className="h-28 rounded-xl" />
      </div>
      <Skeleton className="h-28 rounded-xl" />

      {/* Recent activity skeleton */}
      <Skeleton className="mt-6 h-5 w-40" />
      <div className="space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-16 rounded-xl" />
        ))}
      </div>
    </div>
  )
}

export function DashboardPage() {
  const { profile } = useAuthStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Simulate data fetch — replace with real API call in Sprint 8+
    const timer = setTimeout(() => setLoading(false), 800)
    return () => clearTimeout(timer)
  }, [])

  if (loading) return <DashboardSkeleton />

  return (
    <div className="space-y-4 p-4">
      {/* Welcome */}
      <div>
        <h2 className="text-xl font-bold text-charcoal">
          Welcome back, {profile?.full_name?.split(' ')[0] || 'there'}
        </h2>
        <p className="text-sm text-muted-foreground">
          Here's your CowCare overview for today.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-3">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm text-muted-foreground">
                Conversations
              </CardTitle>
              <MessageSquare className="h-4 w-4 text-accent" />
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-charcoal">—</p>
            <p className="text-xs text-muted-foreground">This week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm text-muted-foreground">
                Reports
              </CardTitle>
              <FileText className="h-4 w-4 text-success" />
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-charcoal">—</p>
            <p className="text-xs text-muted-foreground">Generated</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm text-muted-foreground">
              Governance Lookups
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-warning" />
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold text-navy">—</p>
          <p className="text-xs text-muted-foreground">
            Product + pricing queries this month
          </p>
        </CardContent>
      </Card>

      {/* Recent activity placeholder */}
      <div className="mt-2">
        <h3 className="mb-3 text-sm font-semibold text-navy">
          Recent Activity
        </h3>
        <div className="rounded-xl border bg-white p-6 text-center text-sm text-muted-foreground">
          <MessageSquare className="mx-auto mb-2 h-8 w-8 text-gray-300" />
          <p>No recent activity yet.</p>
          <p className="mt-1 text-xs">
            Start a conversation to see your history here.
          </p>
        </div>
      </div>
    </div>
  )
}
