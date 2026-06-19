/**
 * CustomerLayout — Simplified layout for customer portal.
 * Sprint 13: No nav panels. Clean branded header + footer.
 *
 * Design: Mobile-first, warm, professional.
 * Header: Bower Ag branding + customer name + sign-out
 * Footer: Support info + copyright
 */

import { Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { LogOut } from 'lucide-react'

export function CustomerLayout() {
  const { profile, logout } = useAuthStore()

  const customerName = profile?.full_name || 'Valued Customer'
  const operationName = profile?.customer_operation || ''

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 border-b bg-white shadow-sm">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4">
          {/* Branding */}
          <div className="flex items-center gap-3">
            <span className="text-2xl" role="img" aria-label="Cow">🐄</span>
            <div>
              <h1 className="text-sm font-bold leading-tight text-navy">
                Bower Ag
              </h1>
              <p className="text-[10px] text-muted-foreground">CowCare Reports</p>
            </div>
          </div>

          {/* Customer info + sign out */}
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium text-navy" data-testid="customer-name">
                {customerName}
              </p>
              {operationName && (
                <p className="text-[11px] text-muted-foreground" data-testid="customer-operation">
                  {operationName}
                </p>
              )}
            </div>
            <button
              onClick={() => logout()}
              className="tap-target flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-gray-100 hover:text-danger"
              aria-label="Sign out"
              data-testid="customer-sign-out"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* ── Main content ───────────────────────────────────────────────── */}
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6" data-testid="customer-main">
        <Outlet />
      </main>

      {/* ── Footer ─────────────────────────────────────────────────────── */}
      <footer className="border-t bg-white py-4 text-center">
        <div className="mx-auto max-w-3xl px-4">
          <p className="text-xs text-muted-foreground">
            Questions about your report? Contact your Bower Ag representative.
          </p>
          <p className="mt-1 text-[10px] text-muted-foreground/60">
            &copy; {new Date().getFullYear()} Bower Ag &mdash; CowCare Tool
          </p>
        </div>
      </footer>
    </div>
  )
}
