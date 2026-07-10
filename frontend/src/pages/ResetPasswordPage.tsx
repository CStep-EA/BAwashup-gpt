/**
 * ResetPasswordPage — Handles password reset flow
 * 
 * Three scenarios:
 * 1. User clicked a reset link from email → has access_token in URL hash
 *    → Supabase fires PASSWORD_RECOVERY event → Shows password form
 * 2. User navigated here from invite link → session established by Supabase
 *    → SIGNED_IN event fires → Shows password form
 * 3. Admin set a temporary password → user logged in → auth store redirected
 *    here with ?forced=true → user already has session → Shows password form immediately
 * 
 * After setting password, redirects to login.
 */

import { useState, useEffect, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { supabase } from '@/lib/supabase'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Loader2, AlertCircle, CheckCircle2, Lock } from 'lucide-react'

export function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const isForced = searchParams.get('forced') === 'true'

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [sessionReady, setSessionReady] = useState(false)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    // Scenario 3: Admin forced password change — user is already logged in
    // Just verify the session exists and show the form immediately
    if (isForced) {
      const verifyForcedSession = async () => {
        const { data: { session } } = await supabase.auth.getSession()
        if (session) {
          setSessionReady(true)
        }
        setChecking(false)
      }
      verifyForcedSession()
      return
    }

    // Scenarios 1 & 2: Email link recovery or invite link
    // Supabase handles the token exchange from the URL hash automatically
    // via detectSessionInUrl: true in the client config.
    const checkSession = async () => {
      // Give Supabase a moment to process the URL hash/params
      await new Promise((resolve) => setTimeout(resolve, 1500))

      const { data: { session } } = await supabase.auth.getSession()
      if (session) {
        setSessionReady(true)
      }
      setChecking(false)
    }

    // Listen for auth events (SIGNED_IN from magic link / recovery)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, _session) => {
        if (event === 'PASSWORD_RECOVERY' || event === 'SIGNED_IN') {
          setSessionReady(true)
          setChecking(false)
        }
      }
    )

    checkSession()

    return () => {
      subscription.unsubscribe()
    }
  }, [isForced])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setSubmitting(true)

    try {
      const { error: updateError } = await supabase.auth.updateUser({
        password,
      })

      if (updateError) {
        setError(updateError.message)
      } else {
        // Clear the must_change_password flag if it was set
        const { data: { user: currentUser } } = await supabase.auth.getUser()
        if (currentUser) {
          await supabase
            .from('profiles')
            .update({ must_change_password: false })
            .eq('id', currentUser.id)
        }

        setSuccess(true)
        // Sign out so they can log in fresh with the new password
        await supabase.auth.signOut()
        setTimeout(() => navigate('/login', { replace: true }), 2500)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update password')
    } finally {
      setSubmitting(false)
    }
  }

  // Determine headline text based on scenario
  const headline = isForced
    ? 'Create Your New Password'
    : 'Set Your Password'
  const subtext = isForced
    ? 'Your administrator has required you to set a new password before continuing.'
    : 'Create a secure password for your account'

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
          <h1 className="text-2xl font-bold text-charcoal">{headline}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {subtext}
          </p>
        </div>

        {/* Loading state */}
        {checking && (
          <div className="flex flex-col items-center py-8 text-center">
            <Loader2 className="h-8 w-8 animate-spin text-accent" />
            <p className="mt-3 text-sm text-muted-foreground">
              {isForced ? 'Preparing…' : 'Verifying your link…'}
            </p>
          </div>
        )}

        {/* No session — invalid/expired link */}
        {!checking && !sessionReady && !success && (
          <div className="space-y-4 text-center">
            <div className="flex justify-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
            </div>
            <p className="font-medium text-navy">
              {isForced ? 'Session expired' : 'Link expired or invalid'}
            </p>
            <p className="text-sm text-muted-foreground">
              {isForced
                ? 'Your session has expired. Please log in again and you will be prompted to set a new password.'
                : 'This password reset link has expired or is no longer valid. Please request a new one from your administrator or use the login page.'}
            </p>
            <Button
              onClick={() => navigate('/login', { replace: true })}
              className="tap-target h-[48px] w-full rounded-lg bg-barn-red text-base font-semibold text-white hover:bg-barn-red-light"
            >
              Go to Login
            </Button>
          </div>
        )}

        {/* Success state */}
        {success && (
          <div className="space-y-4 text-center">
            <div className="flex justify-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <CheckCircle2 className="h-6 w-6 text-green-600" />
              </div>
            </div>
            <p className="font-medium text-navy">Password updated!</p>
            <p className="text-sm text-muted-foreground">
              Your password has been set. Redirecting to login…
            </p>
          </div>
        )}

        {/* Password form */}
        {!checking && sessionReady && !success && (
          <>
            {error && (
              <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-danger">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label
                  htmlFor="password"
                  className="text-sm font-medium text-foreground"
                >
                  New Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="Minimum 8 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    className="h-12 rounded-lg pl-10 text-base"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="confirm-password"
                  className="text-sm font-medium text-foreground"
                >
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="confirm-password"
                    type="password"
                    placeholder="Re-enter your password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    className="h-12 rounded-lg pl-10 text-base"
                  />
                </div>
              </div>

              <Button
                type="submit"
                disabled={submitting || !password || !confirmPassword}
                className="tap-target h-[52px] w-full rounded-lg bg-barn-red text-base font-semibold text-white hover:bg-barn-red-light disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Setting Password…
                  </>
                ) : (
                  'Set Password'
                )}
              </Button>
            </form>
          </>
        )}

        {/* Footer */}
        <p className="mt-8 text-center text-xs text-muted-foreground">
          v1.0 Beta · Bower Ag · Cow comfort is always #1
        </p>
      </div>
    </div>
  )
}
