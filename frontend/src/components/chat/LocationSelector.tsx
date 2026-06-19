/**
 * LocationSelector — Fixed top bar for location selection
 * Sprint 7: Bottom sheet (mobile) / dropdown (desktop).
 * Confirmation dialog on location change.
 */

import { useState, useRef, useEffect } from 'react'
import { ChevronDown, MapPin, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { LOCATIONS, useChatStore } from '@/store/chat'
import { setLocation as apiSetLocation } from '@/lib/api'

export function LocationSelector() {
  const { locationCode, locationName, sessionId, setLocation, isStreaming } = useChatStore()
  const [open, setOpen] = useState(false)
  const [confirmTarget, setConfirmTarget] = useState<{ code: string; name: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 3000)
      return () => clearTimeout(t)
    }
  }, [toast])

  const handleSelect = (code: string) => {
    const name = LOCATIONS[code]
    setOpen(false)

    // If already locked to a different location, confirm
    if (locationCode && locationCode !== code) {
      setConfirmTarget({ code, name })
      return
    }

    doSetLocation(code, name, false)
  }

  const doSetLocation = async (code: string, name: string, force: boolean) => {
    setLoading(true)
    try {
      const res = await apiSetLocation({ location_code: code, force }, sessionId)
      setLocation(code, res.location_name)
      setToast(`Location set to ${res.location_name}`)
    } catch {
      // If API fails (no backend), still set locally
      setLocation(code, name)
      setToast(`Location set to ${name}`)
    } finally {
      setLoading(false)
      setConfirmTarget(null)
    }
  }

  return (
    <>
      {/* Location bar */}
      <div className="flex items-center justify-between border-b bg-white px-4 py-2" ref={dropdownRef}>
        <button
          onClick={() => !isStreaming && setOpen(!open)}
          disabled={isStreaming}
          className="tap-target flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors hover:bg-gray-50 disabled:opacity-50"
        >
          <MapPin className="h-4 w-4 text-accent" />
          <span className="font-medium text-navy">
            {locationName || 'Select Location'}
          </span>
          <ChevronDown className={cn('h-3.5 w-3.5 text-gray-400 transition-transform', open && 'rotate-180')} />
        </button>

        {locationCode && (
          <span className="rounded-full bg-accent/10 px-2.5 py-0.5 text-[10px] font-semibold text-accent">
            {locationCode}
          </span>
        )}

        {/* Dropdown / bottom-sheet */}
        {open && (
          <>
            {/* Mobile: bottom sheet overlay */}
            <div className="fixed inset-0 z-50 bg-black/30 lg:hidden" onClick={() => setOpen(false)} />

            {/* Mobile: bottom sheet */}
            <div className="fixed inset-x-0 bottom-0 z-50 rounded-t-2xl bg-white p-4 pb-8 shadow-xl lg:hidden">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-base font-semibold text-navy">Select Location</h3>
                <button
                  onClick={() => setOpen(false)}
                  className="tap-target flex h-8 w-8 items-center justify-center rounded-full hover:bg-gray-100"
                >
                  <X className="h-5 w-5 text-gray-400" />
                </button>
              </div>
              <div className="space-y-1">
                {Object.entries(LOCATIONS).map(([code, name]) => (
                  <button
                    key={code}
                    onClick={() => handleSelect(code)}
                    className={cn(
                      'tap-target flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-sm transition-colors',
                      locationCode === code
                        ? 'bg-accent/10 font-semibold text-accent'
                        : 'hover:bg-gray-50'
                    )}
                  >
                    <MapPin className="h-4 w-4 shrink-0" />
                    <div>
                      <p className="font-medium">{name}</p>
                      <p className="text-[11px] text-gray-400">{code}</p>
                    </div>
                    {locationCode === code && (
                      <span className="ml-auto text-xs text-accent">Current</span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Desktop: dropdown */}
            <div className="absolute left-4 top-full z-50 mt-1 hidden w-64 rounded-xl border bg-white p-2 shadow-lg lg:block">
              {Object.entries(LOCATIONS).map(([code, name]) => (
                <button
                  key={code}
                  onClick={() => handleSelect(code)}
                  className={cn(
                    'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors',
                    locationCode === code
                      ? 'bg-accent/10 font-medium text-accent'
                      : 'hover:bg-gray-50'
                  )}
                >
                  <MapPin className="h-3.5 w-3.5 shrink-0" />
                  <span>{name}</span>
                  {locationCode === code && (
                    <span className="ml-auto text-[10px] text-accent">●</span>
                  )}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Confirmation dialog */}
      {confirmTarget && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-base font-bold text-navy">Switch Location?</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Switching to {confirmTarget.name} pricing. All pricing in this conversation
              will use <span className="font-semibold">{confirmTarget.code}</span> rates. Continue?
            </p>
            <div className="mt-4 flex gap-3">
              <button
                onClick={() => setConfirmTarget(null)}
                className="tap-target flex-1 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors hover:bg-gray-50"
                disabled={loading}
              >
                Cancel
              </button>
              <button
                onClick={() => doSetLocation(confirmTarget.code, confirmTarget.name, true)}
                disabled={loading}
                className="tap-target flex-1 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
              >
                {loading ? 'Switching…' : 'Yes, Switch'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed left-1/2 top-20 z-[70] -translate-x-1/2 rounded-lg bg-navy px-4 py-2 text-sm font-medium text-white shadow-lg">
          ✓ {toast}
        </div>
      )}
    </>
  )
}
