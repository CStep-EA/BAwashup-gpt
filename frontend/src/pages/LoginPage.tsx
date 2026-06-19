/**
 * LoginPage — Mobile-first login at 390px
 * Sprint 6: Full-width inputs, 16px font, 52px navy button,
 * error banner, loading spinner. Redirects by role after login.
 */

import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Loader2, AlertCircle } from 'lucide-react'

/** Determine landing page based on role */
function getLandingRoute(role: string | null): string {
  if (role === 'customer') return '/my-reports'
  return '/'
}

export function LoginPage() {
  const { login, isAuthenticated, isLoading, error, role, clearError } = useAuthStore()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Already authenticated — redirect by role
  if (isAuthenticated && !isLoading) {
    return <Navigate to={getLandingRoute(role)} replace />
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    clearError()
    setSubmitting(true)
    await login(email, password)
    setSubmitting(false)

    // After login, auth store updates role — navigate based on it
    const currentRole = useAuthStore.getState().role
    const isAuth = useAuthStore.getState().isAuthenticated
    if (isAuth) {
      navigate(getLandingRoute(currentRole), { replace: true })
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        {/* Logo / Branding */}
        <div className="mb-8 text-center">
          <img
            src="/bower-ag-logo.jpg"
            alt="Bower Ag"
            className="mx-auto mb-4 h-14 w-auto"
          />
          <h1 className="text-2xl font-bold text-charcoal">CowCare Tool</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Expert System for Dairy Cow Care
          </p>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-danger">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label
              htmlFor="email"
              className="text-sm font-medium text-foreground"
            >
              Email
            </label>
            <Input
              id="email"
              type="email"
              placeholder="you@bowerag.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="h-12 rounded-lg text-base"
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="password"
              className="text-sm font-medium text-foreground"
            >
              Password
            </label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="h-12 rounded-lg text-base"
            />
          </div>

          <Button
            type="submit"
            disabled={submitting || !email || !password}
            className="tap-target h-[52px] w-full rounded-lg bg-barn-red text-base font-semibold text-white hover:bg-barn-red-light disabled:opacity-50"
          >
            {submitting ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Signing in…
              </>
            ) : (
              'Sign In'
            )}
          </Button>
        </form>

        {/* Footer */}
        <p className="mt-8 text-center text-xs text-muted-foreground">
          v1.0 Beta · Bower Ag · Cow comfort is always #1
        </p>
      </div>
    </div>
  )
}
