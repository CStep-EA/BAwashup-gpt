/**
 * AppLayout — Main layout wrapper
 * Mobile: header + content + bottom nav
 * Desktop: sidebar + content (no bottom nav)
 * Renders <Outlet /> for nested routes.
 */

import { Outlet } from 'react-router-dom'
import { BottomNav } from './BottomNav'
import { Sidebar } from './Sidebar'
import { useAuthStore } from '@/store/auth'
import { LogOut, Menu } from 'lucide-react'
import { useState } from 'react'

export function AppLayout() {
  const { profile, role, logout } = useAuthStore()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Desktop sidebar */}
      <Sidebar />

      {/* Main content area — offset by sidebar on lg+ */}
      <div className="flex min-h-screen flex-col lg:pl-64">
        {/* Mobile header — hidden on desktop (sidebar has branding) */}
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between bg-charcoal px-4 lg:hidden">
          <div className="flex items-center gap-3">
            <img src="/bower-ag-logo.jpg" alt="Bower Ag" className="h-8 w-auto brightness-0 invert" />
            <div>
              <h1 className="text-sm font-bold leading-tight text-white">
                CowCare Tool
              </h1>
              <p className="text-[10px] text-gray-300">Bower Ag</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* User badge */}
            <span className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] font-medium capitalize text-gray-200">
              {role?.replace('_', ' ') || '…'}
            </span>

            {/* Mobile menu toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="tap-target flex items-center justify-center rounded-lg p-2 text-gray-300 hover:bg-white/10"
              aria-label="Menu"
            >
              <Menu className="h-5 w-5" />
            </button>
          </div>
        </header>

        {/* Mobile dropdown menu */}
        {mobileMenuOpen && (
          <div className="absolute right-2 top-14 z-40 w-48 rounded-lg border bg-white p-2 shadow-lg lg:hidden">
            <div className="border-b px-3 py-2 text-sm">
              <p className="font-medium text-charcoal">
                {profile?.full_name || 'Bower Ag User'}
              </p>
              <p className="text-xs capitalize text-muted-foreground">
                {role?.replace('_', ' ')}
              </p>
            </div>
            <button
              onClick={() => {
                setMobileMenuOpen(false)
                logout()
              }}
              className="mt-1 flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-danger hover:bg-gray-50"
            >
              <LogOut className="h-4 w-4" />
              Sign Out
            </button>
          </div>
        )}

        {/* Desktop header bar */}
        <header className="hidden h-14 items-center justify-end border-b bg-white px-6 lg:flex">
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">
              {profile?.full_name || 'Bower Ag User'}
            </span>
            <span className="rounded-full bg-accent/10 px-2.5 py-1 text-[11px] font-medium capitalize text-accent">
              {role?.replace('_', ' ') || '…'}
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 pb-20 lg:pb-4">
          <Outlet />
        </main>
      </div>

      {/* Mobile bottom navigation */}
      <BottomNav />
    </div>
  )
}
