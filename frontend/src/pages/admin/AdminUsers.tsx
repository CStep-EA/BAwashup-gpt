/**
 * AdminUsers — User management page (Admin only)
 * Sprint 12: Full table, invite/edit modals, deactivate dialog, role filter.
 *
 * Fetches from /admin/users. ADMIN_ROLES guard on backend.
 * Guards: cannot create org_admin, admin_manager can't assign admin_manager,
 * can't deactivate yourself, org_admin immutable.
 */

import { useState, useEffect, useMemo } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Users,
  Plus,
  Search,
  Edit2,
  UserX,
  AlertTriangle,
  X,
  Check,
  Mail,
  Shield,
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import type { AdminUserItem, InviteUserRequest, UpdateUserRequest } from '@/lib/api'
import {
  fetchAdminUsers,
  inviteUser,
  updateUser,
  deactivateUser,
} from '@/lib/api'

// ─── Constants ─────────────────────────────────────────────────────────────────

const ASSIGNABLE_ROLES = [
  'admin_manager',
  'consultant',
  'technician',
  'account_manager',
  'customer',
] as const

const ROLE_COLORS: Record<string, string> = {
  org_admin: 'bg-red-100 text-red-700',
  admin_manager: 'bg-purple-100 text-purple-700',
  consultant: 'bg-blue-100 text-blue-700',
  technician: 'bg-green-100 text-green-700',
  account_manager: 'bg-amber-100 text-amber-700',
  customer: 'bg-gray-100 text-gray-700',
}

// ─── Skeleton ──────────────────────────────────────────────────────────────────

function UsersSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-7 w-36" />
        <Skeleton className="h-10 w-28 rounded-lg" />
      </div>
      <Skeleton className="h-12 rounded-lg" />
      <Skeleton className="h-80 rounded-xl" />
    </div>
  )
}

// ─── Role Badge ────────────────────────────────────────────────────────────────

function RoleBadge({ role }: { role: string }) {
  const color = ROLE_COLORS[role] || 'bg-gray-100 text-gray-700'
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}>
      {role.replace('_', ' ')}
    </span>
  )
}

// ─── Modal Overlay ─────────────────────────────────────────────────────────────

function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-bold text-navy">{title}</h3>
          <button onClick={onClose} className="rounded-lg p-1 hover:bg-gray-100">
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

// ─── Component ─────────────────────────────────────────────────────────────────

export function AdminUsers() {
  const { role: currentRole, user: currentUser } = useAuthStore()
  const isOrgAdmin = currentRole === 'org_admin'

  const [loading, setLoading] = useState(true)
  const [users, setUsers] = useState<AdminUserItem[]>([])
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')

  // Modals
  const [inviteOpen, setInviteOpen] = useState(false)
  const [editUser, setEditUser] = useState<AdminUserItem | null>(null)
  const [deactivateTarget, setDeactivateTarget] = useState<AdminUserItem | null>(null)

  // Form state
  const [formLoading, setFormLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Invite form
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteName, setInviteName] = useState('')
  const [inviteRole, setInviteRole] = useState<string>('consultant')

  // Edit form
  const [editRole, setEditRole] = useState('')
  const [editName, setEditName] = useState('')

  const loadUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAdminUsers()
      setUsers(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  // Filtered users
  const filteredUsers = useMemo(() => {
    let result = users
    if (search) {
      const s = search.toLowerCase()
      result = result.filter(
        (u) =>
          (u.full_name || '').toLowerCase().includes(s) ||
          (u.email || '').toLowerCase().includes(s)
      )
    }
    if (roleFilter) {
      result = result.filter((u) => u.role === roleFilter)
    }
    return result
  }, [users, search, roleFilter])

  // ─── Invite handler ──────────────────────────────────────────────────────────

  const handleInvite = async () => {
    if (!inviteEmail || !inviteName || !inviteRole) return
    setFormLoading(true)
    setFormError(null)
    try {
      const req: InviteUserRequest = {
        email: inviteEmail,
        role: inviteRole,
        full_name: inviteName,
      }
      await inviteUser(req)
      setInviteOpen(false)
      setInviteEmail('')
      setInviteName('')
      setInviteRole('consultant')
      await loadUsers()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Invite failed')
    } finally {
      setFormLoading(false)
    }
  }

  // ─── Edit handler ────────────────────────────────────────────────────────────

  const openEdit = (u: AdminUserItem) => {
    setEditUser(u)
    setEditRole(u.role)
    setEditName(u.full_name || '')
    setFormError(null)
  }

  const handleEdit = async () => {
    if (!editUser) return
    setFormLoading(true)
    setFormError(null)
    try {
      const req: UpdateUserRequest = {}
      if (editRole !== editUser.role) req.role = editRole
      if (editName !== (editUser.full_name || '')) req.full_name = editName
      if (!req.role && !req.full_name) {
        setEditUser(null)
        return
      }
      await updateUser(editUser.id, req)
      setEditUser(null)
      await loadUsers()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Update failed')
    } finally {
      setFormLoading(false)
    }
  }

  // ─── Deactivate handler ──────────────────────────────────────────────────────

  const handleDeactivate = async () => {
    if (!deactivateTarget) return
    setFormLoading(true)
    setFormError(null)
    try {
      await deactivateUser(deactivateTarget.id)
      setDeactivateTarget(null)
      await loadUsers()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Deactivate failed')
    } finally {
      setFormLoading(false)
    }
  }

  // Roles available for assignment (admin_manager can't assign admin_manager)
  const availableRoles = isOrgAdmin
    ? ASSIGNABLE_ROLES
    : ASSIGNABLE_ROLES.filter((r) => r !== 'admin_manager')

  if (loading) return <UsersSkeleton />

  if (error) {
    return (
      <div className="space-y-4 p-4">
        <h2 className="text-xl font-bold text-navy">User Management</h2>
        <Card>
          <CardContent className="py-8 text-center">
            <AlertTriangle className="mx-auto mb-3 h-10 w-10 text-amber-500" />
            <p className="font-medium text-navy">Failed to load users</p>
            <p className="mt-1 text-sm text-muted-foreground">{error}</p>
            <Button className="mt-4 bg-accent text-white hover:bg-accent/90" onClick={loadUsers}>
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
        <h2 className="text-xl font-bold text-navy">User Management</h2>
        <Button
          className="tap-target gap-2 bg-accent text-white hover:bg-accent/90"
          onClick={() => {
            setFormError(null)
            setInviteOpen(true)
          }}
        >
          <Plus className="h-4 w-4" />
          <span className="hidden sm:inline">Invite User</span>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name or email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="rounded-lg border bg-white px-3 py-2 text-sm"
        >
          <option value="">All Roles</option>
          {['org_admin', ...ASSIGNABLE_ROLES].map((r) => (
            <option key={r} value={r}>{r.replace('_', ' ')}</option>
          ))}
        </select>
      </div>

      {/* User count */}
      <p className="text-xs text-muted-foreground">
        {filteredUsers.length} of {users.length} users
      </p>

      {/* Users table */}
      {filteredUsers.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50 text-left text-xs text-muted-foreground">
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3 hidden sm:table-cell">Email</th>
                    <th className="px-4 py-3">Role</th>
                    <th className="px-4 py-3 hidden md:table-cell">Location</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((u) => {
                    const isCurrentUser = u.id === currentUser?.id
                    const isImmutable = u.role === 'org_admin'
                    return (
                      <tr key={u.id} className="border-b last:border-0 hover:bg-gray-50/50">
                        <td className="px-4 py-3">
                          <p className="font-medium text-navy">{u.full_name || '—'}</p>
                          <p className="text-xs text-muted-foreground sm:hidden">{u.email || '—'}</p>
                        </td>
                        <td className="px-4 py-3 hidden sm:table-cell text-muted-foreground">
                          {u.email || '—'}
                        </td>
                        <td className="px-4 py-3">
                          <RoleBadge role={u.role} />
                        </td>
                        <td className="px-4 py-3 hidden md:table-cell text-muted-foreground">
                          {u.location_name || '—'}
                        </td>
                        <td className="px-4 py-3">
                          {u.active ? (
                            <span className="inline-flex items-center gap-1 text-xs text-green-600">
                              <Check className="h-3 w-3" /> Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs text-red-500">
                              <X className="h-3 w-3" /> Inactive
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            {!isImmutable && (
                              <button
                                onClick={() => openEdit(u)}
                                className="rounded-lg p-1.5 text-muted-foreground hover:bg-gray-100 hover:text-navy"
                                title="Edit user"
                              >
                                <Edit2 className="h-4 w-4" />
                              </button>
                            )}
                            {!isImmutable && !isCurrentUser && u.active && (
                              <button
                                onClick={() => {
                                  setFormError(null)
                                  setDeactivateTarget(u)
                                }}
                                className="rounded-lg p-1.5 text-muted-foreground hover:bg-red-50 hover:text-red-600"
                                title="Deactivate user"
                              >
                                <UserX className="h-4 w-4" />
                              </button>
                            )}
                            {isImmutable && (
                              <span className="text-xs text-muted-foreground">
                                <Shield className="inline h-3.5 w-3.5" /> Protected
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-8 text-center">
            <Users className="mx-auto mb-3 h-10 w-10 text-gray-300" />
            <p className="font-medium text-navy">No users found</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {search || roleFilter ? 'Try adjusting your filters.' : 'Invite your first team member.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* ─── Invite Modal ─────────────────────────────────────────────────────── */}
      <Modal open={inviteOpen} onClose={() => setInviteOpen(false)} title="Invite User">
        <div className="space-y-4">
          {formError && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{formError}</div>
          )}
          <div>
            <Label htmlFor="invite-email">Email</Label>
            <div className="relative mt-1">
              <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="invite-email"
                type="email"
                placeholder="user@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
          <div>
            <Label htmlFor="invite-name">Full Name</Label>
            <Input
              id="invite-name"
              placeholder="Jane Doe"
              value={inviteName}
              onChange={(e) => setInviteName(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="invite-role">Role</Label>
            <select
              id="invite-role"
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm"
            >
              {availableRoles.map((r) => (
                <option key={r} value={r}>{r.replace('_', ' ')}</option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setInviteOpen(false)}>
              Cancel
            </Button>
            <Button
              className="bg-accent text-white hover:bg-accent/90"
              onClick={handleInvite}
              disabled={formLoading || !inviteEmail || !inviteName}
            >
              {formLoading ? 'Sending…' : 'Send Invite'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ─── Edit Modal ───────────────────────────────────────────────────────── */}
      <Modal
        open={!!editUser}
        onClose={() => setEditUser(null)}
        title={`Edit ${editUser?.full_name || 'User'}`}
      >
        <div className="space-y-4">
          {formError && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{formError}</div>
          )}
          <div>
            <Label htmlFor="edit-name">Full Name</Label>
            <Input
              id="edit-name"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="edit-role">Role</Label>
            <select
              id="edit-role"
              value={editRole}
              onChange={(e) => setEditRole(e.target.value)}
              className="mt-1 w-full rounded-lg border bg-white px-3 py-2 text-sm"
            >
              {availableRoles.map((r) => (
                <option key={r} value={r}>{r.replace('_', ' ')}</option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setEditUser(null)}>
              Cancel
            </Button>
            <Button
              className="bg-accent text-white hover:bg-accent/90"
              onClick={handleEdit}
              disabled={formLoading}
            >
              {formLoading ? 'Saving…' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ─── Deactivate Dialog ────────────────────────────────────────────────── */}
      <Modal
        open={!!deactivateTarget}
        onClose={() => setDeactivateTarget(null)}
        title="Deactivate User"
      >
        <div className="space-y-4">
          {formError && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{formError}</div>
          )}
          <p className="text-sm text-muted-foreground">
            Are you sure you want to deactivate{' '}
            <strong className="text-navy">{deactivateTarget?.full_name || deactivateTarget?.email}</strong>?
            They will be banned and unable to log in.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setDeactivateTarget(null)}>
              Cancel
            </Button>
            <Button
              className="bg-red-600 text-white hover:bg-red-700"
              onClick={handleDeactivate}
              disabled={formLoading}
            >
              {formLoading ? 'Deactivating…' : 'Deactivate'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
