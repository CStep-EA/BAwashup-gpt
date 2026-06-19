/**
 * AuditLogPage — Raw audit log viewer (org_admin ONLY)
 * Sprint 12: Filterable data table, date range, CSV export.
 *
 * Fetches from /admin/audit (org_admin only on backend).
 * Filters: user_id, domain, action, start_date, end_date, limit.
 */

import { useState, useEffect } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  FileText,
  Download,
  AlertTriangle,
  Search,
  RefreshCw,
  Filter,
  X,
} from 'lucide-react'
import type { AuditLogEntry } from '@/lib/api'
import { fetchAuditLog, getAuditExportUrl } from '@/lib/api'

// ─── Skeleton ──────────────────────────────────────────────────────────────────

function AuditSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <Skeleton className="h-7 w-28" />
      <div className="flex gap-2">
        <Skeleton className="h-10 flex-1 rounded-lg" />
        <Skeleton className="h-10 w-32 rounded-lg" />
      </div>
      <Skeleton className="h-80 rounded-xl" />
    </div>
  )
}

// ─── Component ─────────────────────────────────────────────────────────────────

export function AuditLogPage() {
  const [loading, setLoading] = useState(true)
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [showFilters, setShowFilters] = useState(false)
  const [domain, setDomain] = useState('')
  const [action, setAction] = useState('')
  const [userId, setUserId] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [limit, setLimit] = useState(100)

  const loadAuditLog = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAuditLog({
        domain: domain || undefined,
        action: action || undefined,
        user_id: userId || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        limit,
      })
      setEntries(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit log')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAuditLog()
  }, [])

  const handleExport = () => {
    const url = getAuditExportUrl({
      domain: domain || undefined,
      action: action || undefined,
      user_id: userId || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    })
    window.open(url, '_blank')
  }

  const clearFilters = () => {
    setDomain('')
    setAction('')
    setUserId('')
    setStartDate('')
    setEndDate('')
    setLimit(100)
  }

  const hasFilters = domain || action || userId || startDate || endDate

  if (loading) return <AuditSkeleton />

  if (error) {
    return (
      <div className="space-y-4 p-4">
        <h2 className="text-xl font-bold text-navy">Audit Log</h2>
        <Card>
          <CardContent className="py-8 text-center">
            <AlertTriangle className="mx-auto mb-3 h-10 w-10 text-amber-500" />
            <p className="font-medium text-navy">Failed to load audit log</p>
            <p className="mt-1 text-sm text-muted-foreground">{error}</p>
            <Button className="mt-4 bg-accent text-white hover:bg-accent/90" onClick={loadAuditLog}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4 p-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-bold text-navy">Audit Log</h2>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className="gap-1.5"
          >
            <Filter className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Filters</span>
            {hasFilters && (
              <span className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full bg-accent text-[10px] text-white">
                !
              </span>
            )}
          </Button>
          <Button variant="outline" size="sm" onClick={loadAuditLog} className="gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport} className="gap-1.5">
            <Download className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Export CSV</span>
          </Button>
        </div>
      </div>

      {/* Filters panel */}
      {showFilters && (
        <Card>
          <CardContent className="py-4">
            <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
              <div>
                <label className="text-xs text-muted-foreground">Domain</label>
                <Input
                  placeholder="e.g. admin, conversation"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Action</label>
                <Input
                  placeholder="e.g. query, config_updated"
                  value={action}
                  onChange={(e) => setAction(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">User ID</label>
                <Input
                  placeholder="UUID"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Start Date</label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">End Date</label>
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Limit</label>
                <Input
                  type="number"
                  value={String(limit)}
                  onChange={(e) => setLimit(Number(e.target.value) || 100)}
                  className="mt-1"
                  min={1}
                  max={500}
                />
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <Button
                size="sm"
                className="gap-1.5 bg-accent text-white hover:bg-accent/90"
                onClick={loadAuditLog}
              >
                <Search className="h-3.5 w-3.5" />
                Apply
              </Button>
              {hasFilters && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    clearFilters()
                    // Trigger load after clearing
                    setTimeout(loadAuditLog, 0)
                  }}
                  className="gap-1.5"
                >
                  <X className="h-3.5 w-3.5" />
                  Clear
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <p className="text-xs text-muted-foreground">
        {entries.length} entr{entries.length !== 1 ? 'ies' : 'y'}
        {limit && entries.length >= limit && ` (limit: ${limit})`}
      </p>

      {/* Audit log table */}
      {entries.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50 text-left text-xs text-muted-foreground">
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3">User</th>
                    <th className="px-4 py-3">Action</th>
                    <th className="px-4 py-3 hidden md:table-cell">Domain</th>
                    <th className="px-4 py-3 hidden lg:table-cell">Location</th>
                    <th className="px-4 py-3 hidden lg:table-cell">Duration</th>
                    <th className="px-4 py-3 hidden xl:table-cell">Query</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry) => (
                    <tr key={entry.id} className="border-b last:border-0 hover:bg-gray-50/50">
                      <td className="px-4 py-2.5 text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(entry.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-2.5">
                        <p className="text-xs font-medium text-navy">{entry.user_name || '—'}</p>
                        <p className="text-[10px] text-muted-foreground capitalize">
                          {entry.user_role?.replace('_', ' ') || '—'}
                        </p>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className="inline-block rounded bg-gray-100 px-2 py-0.5 text-xs font-mono">
                          {entry.action || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 hidden md:table-cell text-xs text-muted-foreground">
                        {entry.domain || '—'}
                      </td>
                      <td className="px-4 py-2.5 hidden lg:table-cell text-xs text-muted-foreground">
                        {entry.location_locked || '—'}
                      </td>
                      <td className="px-4 py-2.5 hidden lg:table-cell text-xs text-muted-foreground tabular-nums">
                        {entry.duration_ms != null ? `${entry.duration_ms}ms` : '—'}
                      </td>
                      <td className="px-4 py-2.5 hidden xl:table-cell max-w-[200px]">
                        <p className="text-xs text-muted-foreground truncate">
                          {entry.query_text || '—'}
                        </p>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-8 text-center">
            <FileText className="mx-auto mb-3 h-10 w-10 text-gray-300" />
            <p className="font-medium text-navy">No audit entries</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {hasFilters
                ? 'Try adjusting your filters.'
                : 'Audit entries will appear here as users interact with the system.'}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
