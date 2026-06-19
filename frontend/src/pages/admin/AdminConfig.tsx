/**
 * AdminConfig — System configuration page (Admin only)
 * Sprint 12: Toggle cards for system_config, editable_by guard graying,
 * maintenance mode confirmation dialog.
 *
 * Fetches from /admin/config. ADMIN_ROLES guard on backend.
 * Config items with editable_by='org_admin' are grayed for admin_manager users.
 */

import { useState, useEffect } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  AlertTriangle,
  Shield,
  Save,
  ToggleLeft,
  ToggleRight,
  X,
  RefreshCw,
  Lock,
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import type { ConfigItem } from '@/lib/api'
import { fetchAdminConfig, updateConfig } from '@/lib/api'

// ─── Helpers ───────────────────────────────────────────────────────────────────

function isBoolean(val: unknown): val is boolean {
  return typeof val === 'boolean'
}

function isNumeric(val: unknown): boolean {
  return typeof val === 'number'
}

function isString(val: unknown): val is string {
  return typeof val === 'string'
}

// ─── Skeleton ──────────────────────────────────────────────────────────────────

function ConfigSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <Skeleton className="h-7 w-36" />
      {[1, 2, 3, 4, 5].map((i) => (
        <Skeleton key={i} className="h-24 rounded-xl" />
      ))}
    </div>
  )
}

// ─── Component ─────────────────────────────────────────────────────────────────

export function AdminConfig() {
  const { role } = useAuthStore()
  const isOrgAdmin = role === 'org_admin'

  const [loading, setLoading] = useState(true)
  const [configs, setConfigs] = useState<ConfigItem[]>([])
  const [error, setError] = useState<string | null>(null)

  // Track per-key editing state
  const [editValues, setEditValues] = useState<Record<string, unknown>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [saveErrors, setSaveErrors] = useState<Record<string, string>>({})

  // Maintenance mode confirmation
  const [maintenanceConfirm, setMaintenanceConfirm] = useState(false)
  const [pendingMaintenanceValue, setPendingMaintenanceValue] = useState<boolean>(false)

  const loadConfig = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAdminConfig()
      setConfigs(data)
      // Initialize edit values
      const vals: Record<string, unknown> = {}
      data.forEach((c) => {
        vals[c.key] = c.value
      })
      setEditValues(vals)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load config')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConfig()
  }, [])

  const handleSave = async (key: string, value: unknown) => {
    // Maintenance mode confirmation
    if (key === 'maintenance_mode' && isBoolean(value) && value === true) {
      setPendingMaintenanceValue(true)
      setMaintenanceConfirm(true)
      return
    }

    setSaving((prev) => ({ ...prev, [key]: true }))
    setSaveErrors((prev) => ({ ...prev, [key]: '' }))
    try {
      const updated = await updateConfig(key, value)
      setConfigs((prev) =>
        prev.map((c) => (c.key === key ? updated : c))
      )
      setEditValues((prev) => ({ ...prev, [key]: updated.value }))
    } catch (err) {
      setSaveErrors((prev) => ({
        ...prev,
        [key]: err instanceof Error ? err.message : 'Save failed',
      }))
    } finally {
      setSaving((prev) => ({ ...prev, [key]: false }))
    }
  }

  const confirmMaintenanceMode = async () => {
    setMaintenanceConfirm(false)
    await handleSaveForce('maintenance_mode', pendingMaintenanceValue)
  }

  const handleSaveForce = async (key: string, value: unknown) => {
    setSaving((prev) => ({ ...prev, [key]: true }))
    setSaveErrors((prev) => ({ ...prev, [key]: '' }))
    try {
      const updated = await updateConfig(key, value)
      setConfigs((prev) =>
        prev.map((c) => (c.key === key ? updated : c))
      )
      setEditValues((prev) => ({ ...prev, [key]: updated.value }))
    } catch (err) {
      setSaveErrors((prev) => ({
        ...prev,
        [key]: err instanceof Error ? err.message : 'Save failed',
      }))
    } finally {
      setSaving((prev) => ({ ...prev, [key]: false }))
    }
  }

  const canEdit = (config: ConfigItem): boolean => {
    if (config.editable_by === 'org_admin' && !isOrgAdmin) return false
    return true
  }

  if (loading) return <ConfigSkeleton />

  if (error) {
    return (
      <div className="space-y-4 p-4">
        <h2 className="text-xl font-bold text-navy">Configuration</h2>
        <Card>
          <CardContent className="py-8 text-center">
            <AlertTriangle className="mx-auto mb-3 h-10 w-10 text-amber-500" />
            <p className="font-medium text-navy">Failed to load configuration</p>
            <p className="mt-1 text-sm text-muted-foreground">{error}</p>
            <Button className="mt-4 bg-accent text-white hover:bg-accent/90" onClick={loadConfig}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-navy">Configuration</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={loadConfig}
          className="gap-1.5"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Refresh</span>
        </Button>
      </div>

      <p className="text-xs text-muted-foreground">
        {configs.length} configuration{configs.length !== 1 ? 's' : ''} •{' '}
        {!isOrgAdmin && (
          <span className="inline-flex items-center gap-1">
            <Lock className="inline h-3 w-3" /> Some settings require org_admin access
          </span>
        )}
      </p>

      {/* Config cards */}
      <div className="space-y-3">
        {configs.map((config) => {
          const editable = canEdit(config)
          const val = editValues[config.key] ?? config.value
          const isSaving = saving[config.key]
          const saveError = saveErrors[config.key]
          const hasChanged = JSON.stringify(val) !== JSON.stringify(config.value)

          return (
            <Card
              key={config.key}
              className={`transition-opacity ${!editable ? 'opacity-60' : ''}`}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-sm font-semibold text-navy">
                      {config.key.replace(/_/g, ' ')}
                    </CardTitle>
                    {config.editable_by === 'org_admin' && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-600">
                        <Shield className="h-2.5 w-2.5" /> org_admin only
                      </span>
                    )}
                  </div>
                  {!editable && <Lock className="h-4 w-4 text-muted-foreground" />}
                </div>
                {config.description && (
                  <p className="text-xs text-muted-foreground">{config.description}</p>
                )}
              </CardHeader>
              <CardContent>
                {saveError && (
                  <div className="mb-2 rounded bg-red-50 px-3 py-1.5 text-xs text-red-700">
                    {saveError}
                  </div>
                )}
                <div className="flex items-center gap-3">
                  {/* Boolean toggle */}
                  {isBoolean(val) && (
                    <button
                      disabled={!editable || isSaving}
                      onClick={() => {
                        const newVal = !val
                        setEditValues((prev) => ({ ...prev, [config.key]: newVal }))
                        handleSave(config.key, newVal)
                      }}
                      className="flex items-center gap-2 disabled:cursor-not-allowed"
                    >
                      {val ? (
                        <ToggleRight className="h-8 w-8 text-accent" />
                      ) : (
                        <ToggleLeft className="h-8 w-8 text-gray-400" />
                      )}
                      <span className="text-sm font-medium text-navy">
                        {val ? 'Enabled' : 'Disabled'}
                      </span>
                    </button>
                  )}

                  {/* Numeric input */}
                  {isNumeric(val) && (
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        value={String(val)}
                        onChange={(e) =>
                          setEditValues((prev) => ({
                            ...prev,
                            [config.key]: Number(e.target.value),
                          }))
                        }
                        disabled={!editable || isSaving}
                        className="w-32"
                      />
                      {hasChanged && editable && (
                        <Button
                          size="sm"
                          className="gap-1 bg-accent text-white hover:bg-accent/90"
                          onClick={() => handleSave(config.key, val)}
                          disabled={isSaving}
                        >
                          <Save className="h-3.5 w-3.5" />
                          {isSaving ? 'Saving…' : 'Save'}
                        </Button>
                      )}
                    </div>
                  )}

                  {/* String input */}
                  {isString(val) && (
                    <div className="flex flex-1 items-center gap-2">
                      <Input
                        value={val}
                        onChange={(e) =>
                          setEditValues((prev) => ({
                            ...prev,
                            [config.key]: e.target.value,
                          }))
                        }
                        disabled={!editable || isSaving}
                        className="flex-1"
                      />
                      {hasChanged && editable && (
                        <Button
                          size="sm"
                          className="gap-1 bg-accent text-white hover:bg-accent/90"
                          onClick={() => handleSave(config.key, val)}
                          disabled={isSaving}
                        >
                          <Save className="h-3.5 w-3.5" />
                          {isSaving ? 'Saving…' : 'Save'}
                        </Button>
                      )}
                    </div>
                  )}

                  {/* JSON / object / array — show as formatted text */}
                  {!isBoolean(val) && !isNumeric(val) && !isString(val) && val !== null && (
                    <div className="flex-1">
                      <pre className="rounded bg-gray-50 p-2 text-xs text-muted-foreground overflow-x-auto max-h-24">
                        {JSON.stringify(val, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>

                {config.updated_at && (
                  <p className="mt-2 text-[10px] text-muted-foreground">
                    Last updated: {new Date(config.updated_at).toLocaleString()}
                  </p>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* ─── Maintenance Mode Confirmation ──────────────────────────────────── */}
      {maintenanceConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-bold text-red-600">Enable Maintenance Mode?</h3>
              <button
                onClick={() => setMaintenanceConfirm(false)}
                className="rounded-lg p-1 hover:bg-gray-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="mb-4 rounded-lg bg-amber-50 p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-600" />
                <div>
                  <p className="text-sm font-medium text-amber-800">
                    This will block all non-admin users
                  </p>
                  <p className="mt-1 text-xs text-amber-700">
                    Enabling maintenance mode will prevent consultants, technicians, and
                    customers from accessing the system. Only org_admin and admin_manager
                    users will be able to use the tool.
                  </p>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setMaintenanceConfirm(false)}>
                Cancel
              </Button>
              <Button
                className="bg-red-600 text-white hover:bg-red-700"
                onClick={confirmMaintenanceMode}
              >
                Enable Maintenance Mode
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
