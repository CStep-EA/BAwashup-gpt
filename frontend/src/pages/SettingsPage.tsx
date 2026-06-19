/**
 * SettingsPage — User settings and preferences
 * Sprint 6: Shell. Full implementation later.
 */

import { useState, useEffect } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuthStore } from '@/store/auth'
import { User, MapPin, Bell, Shield } from 'lucide-react'

function SettingsSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <Skeleton className="h-7 w-24" />
      <Skeleton className="h-32 rounded-xl" />
      <Skeleton className="h-24 rounded-xl" />
      <Skeleton className="h-24 rounded-xl" />
    </div>
  )
}

export function SettingsPage() {
  const { profile, role, locationCode } = useAuthStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 500)
    return () => clearTimeout(timer)
  }, [])

  if (loading) return <SettingsSkeleton />

  return (
    <div className="space-y-4 p-4">
      <h2 className="text-xl font-bold text-navy">Settings</h2>

      {/* Profile card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-navy text-white">
              <User className="h-5 w-5" />
            </div>
            <div>
              <CardTitle>{profile?.full_name || 'Bower Ag User'}</CardTitle>
              <p className="text-xs capitalize text-muted-foreground">
                {role?.replace('_', ' ') || 'Unknown role'}
              </p>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Account ID</span>
              <span className="font-mono text-xs">{profile?.id?.slice(0, 8) || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Status</span>
              <span className={profile?.active ? 'text-success' : 'text-danger'}>
                {profile?.active ? '● Active' : '○ Inactive'}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Location */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-accent" />
            <CardTitle className="text-sm">Location Lock</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {locationCode ? (
              <>
                Locked to:{' '}
                <span className="font-semibold text-navy">{locationCode}</span>
              </>
            ) : (
              'No location locked for this session. Location will be locked on first query.'
            )}
          </p>
        </CardContent>
      </Card>

      {/* Preferences placeholder */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-warning" />
            <CardTitle className="text-sm">Notifications</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Notification preferences will be available in a future update.
          </p>
        </CardContent>
      </Card>

      {/* Security placeholder */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-success" />
            <CardTitle className="text-sm">Security</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Password change and two-factor authentication settings will be available soon.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
