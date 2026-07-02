/**
 * ForgotPasswordPage — Request a password reset email
 * 
 * Public page (no auth required).
 * Sends request to backend /auth/forgot-password endpoint.
 */

import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Loader2, AlertCircle, CheckCircle2, Mail, ArrowLeft } from 'lucide-react'

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '')

export function ForgotPasswordPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      const res = await fetch(`${API_URL}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })

      if (!res.ok) {
        const detail = await res.text().catch(() => 'Request failed')
        setError(detail)
      } else {
        setSuccess(true)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error. Please try again.')
    } finally {
      setSubmitting(false)
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
          <h1 className="text-2xl font-bold text-charcoal">Reset Password</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Enter your email and we&apos;ll send you a reset link
          </p>
        </div>

        {/* Success state */}
        {success ? (
          <div className="space-y-4 text-center">
            <div className="flex justify-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <CheckCircle2 className="h-6 w-6 text-green-600" />
              </div>
            </div>
            <p className="font-medium text-navy">Check your email</p>
            <p className="text-sm text-muted-foreground">
              If an account exists with <strong>{email}</strong>, you&apos;ll receive
              a password reset link shortly. Check your spam folder if you don&apos;t see it.
            </p>
            <Button
              onClick={() => navigate('/login', { replace: true })}
              className="tap-target h-[48px] w-full rounded-lg bg-barn-red text-base font-semibold text-white hover:bg-barn-red-light"
            >
              Back to Login
            </Button>
          </div>
        ) : (
          <>
            {/* Error Banner */}
            {error && (
              <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-danger">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label
                  htmlFor="email"
                  className="text-sm font-medium text-foreground"
                >
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@bowerag.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    autoFocus
                    className="h-12 rounded-lg pl-10 text-base"
                  />
                </div>
              </div>

              <Button
                type="submit"
                disabled={submitting || !email}
                className="tap-target h-[52px] w-full rounded-lg bg-barn-red text-base font-semibold text-white hover:bg-barn-red-light disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Sending…
                  </>
                ) : (
                  'Send Reset Link'
                )}
              </Button>
            </form>

            {/* Back to login link */}
            <button
              onClick={() => navigate('/login')}
              className="mt-4 flex w-full items-center justify-center gap-2 text-sm text-muted-foreground hover:text-navy transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Login
            </button>
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
