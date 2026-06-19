/**
 * BottomNav — Fixed bottom tab bar for mobile (<lg)
 * 5 tabs: Dashboard, Chat, Products, Reports, Settings
 * Hidden at lg+ (1024px). 48px min tap targets.
 */

import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  MessageSquare,
  Package,
  FileText,
  Settings,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth'

const NAV_ITEMS = [
  { to: '/', label: 'Home', icon: LayoutDashboard },
  { to: '/chat', label: 'Chat', icon: MessageSquare, hideForCustomer: true },
  { to: '/products', label: 'Products', icon: Package, hideForCustomer: true },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function BottomNav() {
  const { role } = useAuthStore()
  const isCustomer = role === 'customer'

  const items = NAV_ITEMS.filter(
    (item) => !(item.hideForCustomer && isCustomer)
  )

  // Customer sees: Home → /my-reports, Reports → /my-reports
  const getTo = (item: (typeof NAV_ITEMS)[number]) => {
    if (isCustomer && (item.to === '/' || item.to === '/reports')) {
      return '/my-reports'
    }
    return item.to
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t bg-white lg:hidden">
      <div className="flex h-16 items-center justify-around px-1">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={getTo(item)}
            end={item.to === '/' || item.to === '/my-reports'}
            className={({ isActive }) =>
              cn(
                'tap-target flex flex-1 flex-col items-center justify-center gap-0.5 rounded-lg py-1 text-[11px] font-medium transition-colors',
                isActive
                  ? 'text-accent'
                  : 'text-muted-foreground hover:text-foreground'
              )
            }
          >
            <item.icon className="h-5 w-5" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>
      {/* Safe area for iOS home indicator */}
      <div className="h-[env(safe-area-inset-bottom)]" />
    </nav>
  )
}
