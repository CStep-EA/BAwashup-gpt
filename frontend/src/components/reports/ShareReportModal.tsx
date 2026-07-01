/**
 * ShareReportModal — Share a report with any user (internal or customer).
 * Sprint 21: Updated to allow sharing with internal team members as well.
 *
 * Searches all users (internal + customer) via /users endpoint.
 * Displays role badge so the user knows who they're sharing with.
 */

import { useState } from 'react'
import { X, Search, Loader2, Check, Users, AlertCircle, Mail } from 'lucide-react'
import { shareReport, apiFetchRaw } from '@/lib/api'

// ─── Types ───────────────────────────────────────────────────────────────────

interface UserAccount {
  id: string
  email: string | null
  full_name: string | null
  role: string
  customer_operation: string | null
}

type ShareStep = 'search' | 'confirm' | 'success' | 'error'

// ─── Role Display Helper ─────────────────────────────────────────────────────

function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, string> = {
    customer: 'bg-blue-100 text-blue-700',
    consultant: 'bg-green-100 text-green-700',
    technician: 'bg-purple-100 text-purple-700',
    account_manager: 'bg-amber-100 text-amber-700',
    admin_manager: 'bg-red-100 text-red-700',
    org_admin: 'bg-red-100 text-red-700',
  }
  const displayName: Record<string, string> = {
    customer: 'Customer',
    consultant: 'Consultant',
    technician: 'Technician',
    account_manager: 'Acct Manager',
    admin_manager: 'Admin',
    org_admin: 'Org Admin',
  }
  return (
    <span className={`inline-block rounded-full px-1.5 py-0.5 text-[10px] font-medium ${colors[role] || 'bg-gray-100 text-gray-600'}`}>
      {displayName[role] || role}
    </span>
  )
}

// ─── Props ───────────────────────────────────────────────────────────────────

interface ShareReportModalProps {
  reportId: string
  reportTitle: string
  onClose: () => void
  onShared: () => void
}

// ─── Component ───────────────────────────────────────────────────────────────

export function ShareReportModal({ reportId, reportTitle, onClose, onShared }: ShareReportModalProps) {
  const [step, setStep] = useState<ShareStep>('search')
  const [searchQuery, setSearchQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState<UserAccount[]>([])
  const [selectedUsers, setSelectedUsers] = useState<UserAccount[]>([])
  const [sharing, setSharing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Debounce timer ref
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null)

  // ── Search for users (debounced) ──
  const handleSearch = (query: string) => {
    setSearchQuery(query)
    
    if (debounceTimer) clearTimeout(debounceTimer)
    
    if (query.length < 2) {
      setResults([])
      return
    }

    const timer = setTimeout(async () => {
      setSearching(true)
      try {
        // Search all users (internal + customer)
        const res = await apiFetchRaw<UserAccount[]>(
          `/users?search=${encodeURIComponent(query)}`,
        )
        if (res.data) {
          setResults(res.data)
        } else {
          setResults([])
        }
      } catch {
        setResults([])
      } finally {
        setSearching(false)
      }
    }, 300) // 300ms debounce

    setDebounceTimer(timer)
  }

  // ── Toggle user selection ──
  const handleToggleUser = (user: UserAccount) => {
    setSelectedUsers((prev) => {
      const exists = prev.find((u) => u.id === user.id)
      if (exists) {
        return prev.filter((u) => u.id !== user.id)
      }
      return [...prev, user]
    })
  }

  // ── Go to confirmation ──
  const handleNext = () => {
    if (selectedUsers.length === 0) return
    setStep('confirm')
  }

  // ── Execute share ──
  const handleShare = async () => {
    if (selectedUsers.length === 0) return
    setSharing(true)
    setError(null)

    try {
      await shareReport(reportId, {
        customer_user_ids: selectedUsers.map((u) => u.id),
      })
      setStep('success')
      onShared()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to share report')
      setStep('error')
    } finally {
      setSharing(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h3 className="text-base font-bold text-navy">Share Report</h3>
          <button
            onClick={onClose}
            className="tap-target rounded-lg p-1.5 hover:bg-gray-100"
            aria-label="Close"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4">
          {/* Step 1: Search */}
          {step === 'search' && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Search for team members or customers to share this report with.
              </p>

              {/* Search input */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Search by email or name..."
                  className="w-full rounded-lg border border-gray-300 py-2.5 pl-10 pr-3 text-base outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
                  autoFocus
                  data-testid="share-search-input"
                />
                {searching && (
                  <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-gray-400" />
                )}
              </div>

              {/* Selected users chips */}
              {selectedUsers.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {selectedUsers.map((u) => (
                    <button
                      key={u.id}
                      onClick={() => handleToggleUser(u)}
                      className="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2.5 py-1 text-xs font-medium text-accent hover:bg-accent/20 transition-colors"
                    >
                      {u.full_name || u.email || 'User'}
                      <X className="h-3 w-3" />
                    </button>
                  ))}
                </div>
              )}

              {/* Results */}
              <div className="max-h-48 space-y-1 overflow-y-auto">
                {results.map((user) => {
                  const isSelected = selectedUsers.some((u) => u.id === user.id)
                  return (
                    <button
                      key={user.id}
                      onClick={() => handleToggleUser(user)}
                      className={`tap-target flex w-full items-center gap-3 rounded-lg p-3 text-left transition-colors ${
                        isSelected ? 'bg-accent/5 border border-accent/20' : 'hover:bg-gray-50'
                      }`}
                      data-testid="user-result"
                    >
                      <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                        isSelected ? 'bg-accent/20' : 'bg-blue-100'
                      }`}>
                        {isSelected ? (
                          <Check className="h-4 w-4 text-accent" />
                        ) : (
                          <Users className="h-4 w-4 text-blue-600" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium text-navy truncate">
                            {user.full_name || user.email || 'Unknown'}
                          </p>
                          <RoleBadge role={user.role} />
                        </div>
                        {user.email && (
                          <p className="text-xs text-muted-foreground truncate">
                            <Mail className="mr-0.5 inline h-3 w-3" />
                            {user.email}
                          </p>
                        )}
                      </div>
                    </button>
                  )
                })}

                {searchQuery.length >= 2 && !searching && results.length === 0 && (
                  <div className="py-4 text-center">
                    <p className="text-sm text-muted-foreground">
                      No users found matching &ldquo;{searchQuery}&rdquo;.
                    </p>
                  </div>
                )}
              </div>

              {/* Share button */}
              {selectedUsers.length > 0 && (
                <button
                  onClick={handleNext}
                  className="tap-target w-full rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
                >
                  Share with {selectedUsers.length} {selectedUsers.length === 1 ? 'person' : 'people'}
                </button>
              )}
            </div>
          )}

          {/* Step 2: Confirmation */}
          {step === 'confirm' && (
            <div className="space-y-4" data-testid="share-confirm">
              <p className="text-sm font-medium text-navy">
                Share &ldquo;{reportTitle}&rdquo; with:
              </p>
              
              <div className="space-y-2 rounded-lg bg-gray-50 p-3">
                {selectedUsers.map((u) => (
                  <div key={u.id} className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-green-600" />
                    <span className="text-sm text-navy">
                      {u.full_name || u.email}
                    </span>
                    <RoleBadge role={u.role} />
                  </div>
                ))}
              </div>

              <p className="text-xs text-muted-foreground">
                Selected users will be able to view and download this report. 
                Customer accounts will only see the report — no internal information.
              </p>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setStep('search')}
                  className="tap-target flex-1 rounded-lg border border-gray-200 px-4 py-2.5 text-sm font-medium text-navy transition-colors hover:bg-gray-50"
                  disabled={sharing}
                >
                  Back
                </button>
                <button
                  onClick={handleShare}
                  disabled={sharing}
                  className="tap-target flex flex-1 items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
                  data-testid="share-confirm-btn"
                >
                  {sharing ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Sharing...
                    </>
                  ) : (
                    'Confirm Share'
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Success */}
          {step === 'success' && (
            <div className="flex flex-col items-center py-4 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <Check className="h-6 w-6 text-green-600" />
              </div>
              <p className="mt-3 text-sm font-medium text-navy">
                Report shared with {selectedUsers.length} {selectedUsers.length === 1 ? 'person' : 'people'}.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                They can now view and download this report.
              </p>
              <button
                onClick={onClose}
                className="tap-target mt-4 w-full rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
              >
                Done
              </button>
            </div>
          )}

          {/* Error */}
          {step === 'error' && (
            <div className="flex flex-col items-center py-4 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
              <p className="mt-3 text-sm font-medium text-navy">Failed to share report</p>
              <p className="mt-1 text-xs text-muted-foreground">{error}</p>
              <button
                onClick={() => setStep('confirm')}
                className="tap-target mt-4 w-full rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
