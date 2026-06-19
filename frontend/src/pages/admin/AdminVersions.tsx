/**
 * AdminVersions — Version history / changelog (Admin only)
 * Sprint 12: Accordion entries, create release (org_admin only), CSV export.
 *
 * Fetches from /admin/versions. ADMIN_ROLES guard on backend.
 * POST /admin/versions requires org_admin.
 */

import { useState, useEffect } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  GitBranch,
  Plus,
  Download,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Tag,
  Clock,
  X,
  AlertCircle,
  Check,
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import type { VersionLogItem, CreateVersionRequest } from '@/lib/api'
import { fetchAdminVersions, createVersion, getVersionsExportUrl } from '@/lib/api'

// ─── Skeleton ──────────────────────────────────────────────────────────────────

function VersionsSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <Skeleton className="h-7 w-28" />
      <Skeleton className="h-20 rounded-xl" />
      <Skeleton className="h-20 rounded-xl" />
      <Skeleton className="h-20 rounded-xl" />
    </div>
  )
}

// ─── Accordion Item ────────────────────────────────────────────────────────────

function VersionAccordionItem({ version }: { version: VersionLogItem }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <Card>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left"
      >
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Tag className="h-4 w-4 text-accent" />
              <div>
                <CardTitle className="text-sm font-bold text-navy">
                  {version.version_tag}
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  <Clock className="mr-1 inline h-3 w-3" />
                  {new Date(version.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
            {expanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        </CardHeader>
      </button>

      {expanded && (
        <CardContent className="pt-0">
          <div className="space-y-3 border-t pt-3">
            {/* Release Notes */}
            {version.release_notes && (
              <div>
                <p className="mb-1 text-xs font-semibold text-muted-foreground">Release Notes</p>
                <p className="text-sm text-navy whitespace-pre-wrap">{version.release_notes}</p>
              </div>
            )}

            {/* Breaking Changes */}
            {version.breaking_changes && (
              <div>
                <p className="mb-1 text-xs font-semibold text-red-600">
                  <AlertCircle className="mr-1 inline h-3 w-3" />
                  Breaking Changes
                </p>
                <p className="text-sm text-red-700 whitespace-pre-wrap">{version.breaking_changes}</p>
              </div>
            )}

            {/* Bugs Resolved */}
            {version.bugs_resolved && version.bugs_resolved.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-semibold text-green-600">
                  <Check className="mr-1 inline h-3 w-3" />
                  Bugs Resolved
                </p>
                <ul className="list-disc pl-5 text-sm text-navy">
                  {version.bugs_resolved.map((bugId, idx) => (
                    <li key={idx} className="text-xs">{bugId}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Metadata */}
            <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
              {version.release_date && (
                <span>Released: {new Date(version.release_date).toLocaleDateString()}</span>
              )}
              {version.deployed_by && (
                <span>Deployed by: {version.deployed_by.slice(0, 8)}…</span>
              )}
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  )
}

// ─── Component ─────────────────────────────────────────────────────────────────

export function AdminVersions() {
  const { role } = useAuthStore()
  const isOrgAdmin = role === 'org_admin'

  const [loading, setLoading] = useState(true)
  const [versions, setVersions] = useState<VersionLogItem[]>([])
  const [error, setError] = useState<string | null>(null)

  // Create release modal
  const [createOpen, setCreateOpen] = useState(false)
  const [formTag, setFormTag] = useState('')
  const [formNotes, setFormNotes] = useState('')
  const [formBreaking, setFormBreaking] = useState('')
  const [formBugs, setFormBugs] = useState('')
  const [formLoading, setFormLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const loadVersions = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAdminVersions()
      setVersions(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load versions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadVersions()
  }, [])

  const handleCreate = async () => {
    if (!formTag) return
    setFormLoading(true)
    setFormError(null)
    try {
      const req: CreateVersionRequest = {
        version_tag: formTag,
      }
      if (formNotes) req.release_notes = formNotes
      if (formBreaking) req.breaking_changes = formBreaking
      if (formBugs.trim()) {
        req.bugs_resolved = formBugs.split(',').map((s) => s.trim()).filter(Boolean)
      }
      await createVersion(req)
      setCreateOpen(false)
      setFormTag('')
      setFormNotes('')
      setFormBreaking('')
      setFormBugs('')
      await loadVersions()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to create version')
    } finally {
      setFormLoading(false)
    }
  }

  const handleExport = () => {
    window.open(getVersionsExportUrl(), '_blank')
  }

  if (loading) return <VersionsSkeleton />

  if (error) {
    return (
      <div className="space-y-4 p-4">
        <h2 className="text-xl font-bold text-navy">Versions</h2>
        <Card>
          <CardContent className="py-8 text-center">
            <AlertTriangle className="mx-auto mb-3 h-10 w-10 text-amber-500" />
            <p className="font-medium text-navy">Failed to load versions</p>
            <p className="mt-1 text-sm text-muted-foreground">{error}</p>
            <Button className="mt-4 bg-accent text-white hover:bg-accent/90" onClick={loadVersions}>
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
        <h2 className="text-xl font-bold text-navy">Version History</h2>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExport} className="gap-1.5">
            <Download className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Export CSV</span>
          </Button>
          {isOrgAdmin && (
            <Button
              className="tap-target gap-2 bg-accent text-white hover:bg-accent/90"
              onClick={() => {
                setFormError(null)
                setCreateOpen(true)
              }}
            >
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline">New Release</span>
            </Button>
          )}
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        {versions.length} version{versions.length !== 1 ? 's' : ''} recorded
      </p>

      {/* Version list */}
      {versions.length > 0 ? (
        <div className="space-y-3">
          {versions.map((v) => (
            <VersionAccordionItem key={v.id} version={v} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-8 text-center">
            <GitBranch className="mx-auto mb-3 h-10 w-10 text-gray-300" />
            <p className="font-medium text-navy">No versions yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {isOrgAdmin
                ? 'Create the first release to start tracking.'
                : 'Versions will appear here once created by an org_admin.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* ─── Create Release Modal ──────────────────────────────────────────── */}
      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-bold text-navy">Create Release</h3>
              <button onClick={() => setCreateOpen(false)} className="rounded-lg p-1 hover:bg-gray-100">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              {formError && (
                <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{formError}</div>
              )}

              <div>
                <Label htmlFor="version-tag">Version Tag</Label>
                <Input
                  id="version-tag"
                  placeholder="v1.2.3 or v1.2.3-beta"
                  value={formTag}
                  onChange={(e) => setFormTag(e.target.value)}
                  className="mt-1"
                />
                <p className="mt-1 text-[10px] text-muted-foreground">
                  Format: vX.Y.Z or vX.Y.Z-beta
                </p>
              </div>

              <div>
                <Label htmlFor="release-notes">Release Notes</Label>
                <textarea
                  id="release-notes"
                  value={formNotes}
                  onChange={(e) => setFormNotes(e.target.value)}
                  className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm min-h-[80px] resize-y"
                  placeholder="What's new in this release…"
                />
              </div>

              <div>
                <Label htmlFor="breaking-changes">Breaking Changes (optional)</Label>
                <textarea
                  id="breaking-changes"
                  value={formBreaking}
                  onChange={(e) => setFormBreaking(e.target.value)}
                  className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm min-h-[60px] resize-y"
                  placeholder="Any breaking changes…"
                />
              </div>

              <div>
                <Label htmlFor="bugs-resolved">Bugs Resolved (comma-separated IDs)</Label>
                <Input
                  id="bugs-resolved"
                  placeholder="BUG-001, BUG-002"
                  value={formBugs}
                  onChange={(e) => setFormBugs(e.target.value)}
                  className="mt-1"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={() => setCreateOpen(false)}>
                  Cancel
                </Button>
                <Button
                  className="bg-accent text-white hover:bg-accent/90"
                  onClick={handleCreate}
                  disabled={formLoading || !formTag}
                >
                  {formLoading ? 'Creating…' : 'Create Release'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
