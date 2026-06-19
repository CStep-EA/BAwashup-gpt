/**
 * AdminDashboard — Admin-only overview page
 * Sprint 12: Live metrics, Recharts bar/line charts, top products table, date range.
 *
 * Fetches from /admin/analytics/summary, /top_products, /usage_by_day.
 * Desktop-primary layout (768px+ grid), stacked cards on mobile.
 */

import { useState, useEffect, useCallback } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Users,
  MessageSquare,
  ShieldAlert,
  Bug,
  ThumbsUp,
  ThumbsDown,
  Zap,
  Clock,
  AlertTriangle,
  BarChart3,
  TrendingUp,
  RefreshCw,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type {
  AnalyticsSummary,
  TopProduct,
  DailyUsage,
} from '@/lib/api'
import {
  fetchAnalyticsSummary,
  fetchTopProducts,
  fetchUsageByDay,
} from '@/lib/api'

// ─── Date Range Options ────────────────────────────────────────────────────────

const DATE_RANGES = [
  { label: '7d', value: 7 },
  { label: '14d', value: 14 },
  { label: '30d', value: 30 },
  { label: '90d', value: 90 },
] as const

// ─── Skeleton ──────────────────────────────────────────────────────────────────

function AdminDashboardSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-9 w-48" />
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[5, 6, 7, 8].map((i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-72 rounded-xl" />
        <Skeleton className="h-72 rounded-xl" />
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  )
}

// ─── Metric Card ───────────────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  icon: Icon,
  color,
  subtitle,
}: {
  label: string
  value: string | number
  icon: React.ComponentType<{ className?: string }>
  color: string
  subtitle?: string
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xs text-muted-foreground">
            {label}
          </CardTitle>
          <Icon className={`h-4 w-4 ${color}`} />
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold text-navy">{value}</p>
        {subtitle && (
          <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Component ─────────────────────────────────────────────────────────────────

export function AdminDashboard() {
  const [days, setDays] = useState(7)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [topProducts, setTopProducts] = useState<TopProduct[]>([])
  const [usageByDay, setUsageByDay] = useState<DailyUsage[]>([])

  const loadData = useCallback(async (selectedDays: number, isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    else setLoading(true)
    setError(null)

    try {
      const [summaryData, topData, usageData] = await Promise.all([
        fetchAnalyticsSummary(selectedDays),
        fetchTopProducts(selectedDays, 10),
        fetchUsageByDay(selectedDays),
      ])
      setSummary(summaryData)
      setTopProducts(topData)
      setUsageByDay(usageData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadData(days)
  }, [days, loadData])

  if (loading) return <AdminDashboardSkeleton />

  if (error) {
    return (
      <div className="space-y-4 p-4">
        <h2 className="text-xl font-bold text-navy">Admin Dashboard</h2>
        <Card>
          <CardContent className="py-8 text-center">
            <AlertTriangle className="mx-auto mb-3 h-10 w-10 text-amber-500" />
            <p className="font-medium text-navy">Failed to load analytics</p>
            <p className="mt-1 text-sm text-muted-foreground">{error}</p>
            <Button
              className="mt-4 bg-accent text-white hover:bg-accent/90"
              onClick={() => loadData(days)}
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!summary) return null

  // Format domain data for bar chart
  const domainChartData = summary.queries_by_domain.map((d) => ({
    name: d.domain.length > 12 ? d.domain.slice(0, 12) + '…' : d.domain,
    queries: d.count,
  }))

  return (
    <div className="space-y-4 p-4">
      {/* Header with date range + refresh */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-bold text-navy">Admin Dashboard</h2>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border bg-white p-0.5">
            {DATE_RANGES.map((range) => (
              <button
                key={range.value}
                onClick={() => setDays(range.value)}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  days === range.value
                    ? 'bg-accent text-white'
                    : 'text-muted-foreground hover:text-navy'
                }`}
              >
                {range.label}
              </button>
            ))}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadData(days, true)}
            disabled={refreshing}
            className="gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
        </div>
      </div>

      {/* Row 1: Primary metrics */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricCard
          label="Total Queries"
          value={summary.total_queries.toLocaleString()}
          icon={MessageSquare}
          color="text-blue-500"
          subtitle={`${summary.queries_today} today`}
        />
        <MetricCard
          label="Active Users"
          value={summary.active_users}
          icon={Users}
          color="text-green-500"
          subtitle={`Last ${days} days`}
        />
        <MetricCard
          label="Claude API Calls"
          value={summary.claude_api_calls.toLocaleString()}
          icon={Zap}
          color="text-purple-500"
        />
        <MetricCard
          label="Avg Response"
          value={`${summary.avg_response_ms}ms`}
          icon={Clock}
          color="text-orange-500"
        />
      </div>

      {/* Row 2: Secondary metrics */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricCard
          label="Governance Blocks"
          value={summary.governance_blocks}
          icon={ShieldAlert}
          color="text-red-500"
        />
        <MetricCard
          label="Open Bugs"
          value={summary.open_bugs}
          icon={Bug}
          color="text-amber-500"
          subtitle={`${summary.open_critical_bugs} critical`}
        />
        <MetricCard
          label="Thumbs Up"
          value={summary.thumbs_up}
          icon={ThumbsUp}
          color="text-green-500"
        />
        <MetricCard
          label="Thumbs Down"
          value={summary.thumbs_down}
          icon={ThumbsDown}
          color="text-red-400"
        />
      </div>

      {/* Charts row */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Usage by Day — Line Chart */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-accent" />
              <CardTitle className="text-sm font-semibold text-navy">
                Daily Usage
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {usageByDay.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={usageByDay}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v) => String(v).slice(5)}
                  />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    labelFormatter={(label) => `Date: ${String(label)}`}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line
                    type="monotone"
                    dataKey="query_count"
                    stroke="#2563eb"
                    strokeWidth={2}
                    name="Queries"
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="active_users"
                    stroke="#16a34a"
                    strokeWidth={2}
                    name="Active Users"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="py-12 text-center text-sm text-muted-foreground">
                No usage data for this period.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Queries by Domain — Bar Chart */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-accent" />
              <CardTitle className="text-sm font-semibold text-navy">
                Queries by Domain
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {domainChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={domainChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Bar
                    dataKey="queries"
                    fill="#2563eb"
                    radius={[4, 4, 0, 0]}
                    name="Queries"
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="py-12 text-center text-sm text-muted-foreground">
                No domain data for this period.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Top Products table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold text-navy">
            Top Products Mentioned ({days}d)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {topProducts.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="pb-2 pr-4">#</th>
                    <th className="pb-2 pr-4">Product</th>
                    <th className="pb-2 text-right">Mentions</th>
                  </tr>
                </thead>
                <tbody>
                  {topProducts.map((p, idx) => (
                    <tr key={p.product_name} className="border-b last:border-0">
                      <td className="py-2.5 pr-4 text-muted-foreground">{idx + 1}</td>
                      <td className="py-2.5 pr-4 font-medium text-navy">
                        {p.product_name}
                      </td>
                      <td className="py-2.5 text-right tabular-nums">
                        {p.mention_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No product mentions found for this period.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Location breakdown */}
      {summary.queries_by_location.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-navy">
              Queries by Location
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-5">
              {summary.queries_by_location.map((loc) => (
                <div
                  key={loc.location_locked}
                  className="rounded-lg border bg-gray-50 p-3 text-center"
                >
                  <p className="text-lg font-bold text-navy">{loc.count}</p>
                  <p className="text-xs text-muted-foreground">
                    {loc.location_locked === 'none' ? 'No Location' : loc.location_locked}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
