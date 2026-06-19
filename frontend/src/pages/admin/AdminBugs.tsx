/**
 * AdminBugs — Bug report viewer (Admin only)
 * Sprint 12: Table with severity/status badges, detail panel,
 * status update, CSV export, filters.
 *
 * Fetches from /admin/bugs. ADMIN_ROLES guard on backend.
 */

import { useState, useEffect } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Bug,
  Search,
  Download,
  X,
  AlertTriangle,
  ChevronRight,
  Clock,
  Check,
  RefreshCw,
  Save,
} from 'lucide-react'
import type { AdminBugReport, BugUpdateRequest } from '@/lib/api'
import { fetchAdminBugs, updateAdminBug, getAdminBugsExportUrl } from '@/lib/api'

// ─── Constants ─────────────────────────────────────────────────────────────────

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-700',
  high: 'bg-orange-100 text-orange-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-green-100 text-green-700',
}

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-blue-100 text-blue-700',
  investigating: 'bg-purple-100 text-purple-700',
  in_progress: 'bg-amber-100 text-amber-700',
  resolved: 'bg-green-100 text-green-700',
  fixed: 'bg-green-100 text-green-700',
  closed: 'bg-gray-100 text-gray-700',
  wont_fix: 'bg-gray-100 text-gray-500',
}

const STATUS_OPTIONS = [
  'open',
  'investigating',
  'in_progress',
  'resolved',
  'fixed',
  'closed',
  'wont_fix',
]

const SEVERITY_OPTIONS = ['critical', 'high', 'medium', 'low']

// ─── Skeleton ──────────────────────────────────────────────────────────────────

function BugsSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <Skeleton className="h-7 w-32" />
      <Skeleton className="h-12 rounded-lg" />
      <Skeleton className="h-64 rounded-xl" />
    </div>
  )
}

// ─── Badge ─────────────────────────────────────────────────────────────────────

function Badge({ label, colorMap }: { label: string; colorMap: Record<string, string> }) {
  const color = colorMap[label] || 'bg-gray-100 text-gray-700'
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}>
      {label.replace('_', ' ')}
    </span>
  )
}

// ─── Component ─────────────────────────────────────────────────────────────────

export function AdminBugs() {
  const [loading, setLoading] = useState(true)
  const [bugs, setBugs] = useState<AdminBugReport[]>([])
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [search, setSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  // Detail panel
  const [selectedBug, setSelectedBug] = useState<AdminBugReport | null>(null)
  const [editStatus, setEditStatus] = useState('')
  const [editNotes, setEditNotes] = useState('')
  const [editSeverity, setEditSeverity] = useState('')
  const [updateLoading, setUpdateLoading] = useState(false)
  const [updateError, setUpdateError] = useState<string | null>(null)

  const loadBugs = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAdminBugs({
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        search: search || undefined,
      })
      setBugs(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load bugs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadBugs()
  }, [severityFilter, statusFilter])

  const handleSearch = () => loadBugs()

  const openDetail = (bug: AdminBugReport) => {
    setSelectedBug(bug)
    setEditStatus(bug.status)
    setEditNotes(bug.fix_notes || '')
    setEditSeverity(bug.severity)
    setUpdateError(null)
  }

  const handleUpdate = async () => {
    if (!selectedBug) return
    setUpdateLoading(true)
    setUpdateError(null)
    try {
      const req: BugUpdateRequest = {}
      if (editStatus !== selectedBug.status) req.status = editStatus
      if (editNotes !== (selectedBug.fix_notes || '')) req.fix_notes = editNotes
      if (editSeverity !== selectedBug.severity) req.severity = editSeverity
      if (!req.status && !req.fix_notes && !req.severity) {
        setSelectedBug(null)
        return
      }
      const updated = await updateAdminBug(selectedBug.id, req)
      setBugs((prev) => prev.map((b) => (b.id === updated.id ? updated : b)))
      setSelectedBug(updated)
    } catch (err) {
      setUpdateError(err instanceof Error ? err.message : 'Update failed')
    } finally {
      setUpdateLoading(false)
    }
  }

  const handleExport = () => {
    const url = getAdminBugsExportUrl({
      severity: severityFilter || undefined,
      status: statusFilter || undefined,
      search: search || undefined,
    })
    window.open(url, '_blank')
  }

  if (loading) return <BugsSkeleton />

  if (error) {
    return (
      <div className="space-y-4 p-4">
        <h2 className="text-xl font-bold text-navy">Bug Reports</h2>
        <Card>
          <CardContent className="py-8 text-center">
            <AlertTriangle className="mx-auto mb-3 h-10 w-10 text-amber-500" />
            <p className="font-medium text-navy">Failed to load bug reports</p>
            <p className="mt-1 text-sm text-muted-foreground">{error}</p>
            <Button className="mt-4 bg-accent text-white hover:bg-accent/90" onClick={loadBugs}>
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
        <h2 className="text-xl font-bold text-navy">Bug Reports</h2>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadBugs} className="gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            className="gap-1.5"
          >
            <Download className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Export CSV</span>
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-[180px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search bugs…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            className="pl-9"
          />
        </div>
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="rounded-lg border bg-white px-3 py-2 text-sm"
        >
          <option value="">All Severities</option>
          {SEVERITY_OPTIONS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border bg-white px-3 py-2 text-sm"
        >
          <option value="">All Statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s.replace('_', ' ')}</option>
          ))}
        </select>
      </div>

      <p className="text-xs text-muted-foreground">{bugs.length} bug report{bugs.length !== 1 ? 's' : ''}</p>

      {/* Bug list */}
      {bugs.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50 text-left text-xs text-muted-foreground">
                    <th className="px-4 py-3">Title</th>
                    <th className="px-4 py-3">Severity</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 hidden md:table-cell">Reporter</th>
                    <th className="px-4 py-3 hidden sm:table-cell">Created</th>
                    <th className="px-4 py-3 w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  {bugs.map((bug) => (
                    <tr
                      key={bug.id}
                      onClick={() => openDetail(bug)}
                      className="cursor-pointer border-b last:border-0 hover:bg-gray-50/50"
                    >
                      <td className="px-4 py-3">
                        <p className="font-medium text-navy line-clamp-1">{bug.title}</p>
                        <p className="text-xs text-muted-foreground line-clamp-1">
                          {bug.description || '—'}
                        </p>
                      </td>
                      <td className="px-4 py-3">
                        <Badge label={bug.severity} colorMap={SEVERITY_COLORS} />
                      </td>
                      <td className="px-4 py-3">
                        <Badge label={bug.status} colorMap={STATUS_COLORS} />
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell text-muted-foreground">
                        {bug.reporter_name || '—'}
                      </td>
                      <td className="px-4 py-3 hidden sm:table-cell text-xs text-muted-foreground">
                        {new Date(bug.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
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
            <Bug className="mx-auto mb-3 h-10 w-10 text-gray-300" />
            <p className="font-medium text-navy">No bug reports</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {severityFilter || statusFilter || search
                ? 'Try adjusting your filters.'
                : 'No bugs have been reported yet.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* ─── Detail Panel ──────────────────────────────────────────────────── */}
      {selectedBug && (
        <div className="fixed inset-0 z-50 flex items-start justify-end bg-black/50">
          <div className="h-full w-full max-w-lg overflow-y-auto bg-white p-6 shadow-xl md:w-[480px]">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-bold text-navy">Bug Detail</h3>
              <button
                onClick={() => setSelectedBug(null)}
                className="rounded-lg p-1 hover:bg-gray-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              {/* Title & ID */}
              <div>
                <h4 className="text-base font-semibold text-navy">{selectedBug.title}</h4>
                <p className="text-xs text-muted-foreground">ID: {selectedBug.id}</p>
              </div>

              {/* Badges */}
              <div className="flex items-center gap-2">
                <Badge label={selectedBug.severity} colorMap={SEVERITY_COLORS} />
                <Badge label={selectedBug.status} colorMap={STATUS_COLORS} />
                {selectedBug.version_tag && (
                  <span className="text-xs text-muted-foreground">{selectedBug.version_tag}</span>
                )}
              </div>

              {/* Metadata */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Reporter</p>
                  <p className="font-medium text-navy">{selectedBug.reporter_name || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Created</p>
                  <p className="flex items-center gap-1 font-medium text-navy">
                    <Clock className="h-3 w-3" />
                    {new Date(selectedBug.created_at).toLocaleDateString()}
                  </p>
                </div>
                {selectedBug.resolved_at && (
                  <div>
                    <p className="text-xs text-muted-foreground">Resolved</p>
                    <p className="flex items-center gap-1 font-medium text-green-600">
                      <Check className="h-3 w-3" />
                      {new Date(selectedBug.resolved_at).toLocaleDateString()}
                    </p>
                  </div>
                )}
              </div>

              {/* Description */}
              {selectedBug.description && (
                <div>
                  <p className="mb-1 text-xs font-semibold text-muted-foreground">Description</p>
                  <p className="text-sm text-navy whitespace-pre-wrap">{selectedBug.description}</p>
                </div>
              )}

              {/* Steps to Reproduce */}
              {selectedBug.steps_to_reproduce && (
                <div>
                  <p className="mb-1 text-xs font-semibold text-muted-foreground">Steps to Reproduce</p>
                  <p className="text-sm text-navy whitespace-pre-wrap">{selectedBug.steps_to_reproduce}</p>
                </div>
              )}

              {/* Expected / Actual */}
              {selectedBug.expected_behavior && (
                <div>
                  <p className="mb-1 text-xs font-semibold text-muted-foreground">Expected Behavior</p>
                  <p className="text-sm text-navy whitespace-pre-wrap">{selectedBug.expected_behavior}</p>
                </div>
              )}
              {selectedBug.actual_behavior && (
                <div>
                  <p className="mb-1 text-xs font-semibold text-muted-foreground">Actual Behavior</p>
                  <p className="text-sm text-navy whitespace-pre-wrap">{selectedBug.actual_behavior}</p>
                </div>
              )}

              {/* ── Admin update form ────────────────────────────────────────── */}
              <div className="border-t pt-4">
                <p className="mb-3 text-sm font-semibold text-navy">Update Bug</p>

                {updateError && (
                  <div className="mb-2 rounded bg-red-50 px-3 py-1.5 text-xs text-red-700">
                    {updateError}
                  </div>
                )}

                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-muted-foreground">Status</label>
                    <select
                      value={editStatus}
                      onChange={(e) => setEditStatus(e.target.value)}
                      className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm"
                    >
                      {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>{s.replace('_', ' ')}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">Severity</label>
                    <select
                      value={editSeverity}
                      onChange={(e) => setEditSeverity(e.target.value)}
                      className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm"
                    >
                      {SEVERITY_OPTIONS.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">Fix Notes</label>
                    <textarea
                      value={editNotes}
                      onChange={(e) => setEditNotes(e.target.value)}
                      className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm min-h-[80px] resize-y"
                      placeholder="Describe the fix or workaround…"
                    />
                  </div>
                  <Button
                    className="w-full gap-2 bg-accent text-white hover:bg-accent/90"
                    onClick={handleUpdate}
                    disabled={updateLoading}
                  >
                    <Save className="h-4 w-4" />
                    {updateLoading ? 'Saving…' : 'Save Changes'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
