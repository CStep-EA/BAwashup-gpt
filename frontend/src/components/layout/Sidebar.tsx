/**
 * Sidebar — Desktop left navigation (lg+ / 1024px)
 * Same 5 items as BottomNav + admin section.
 * Hidden on mobile. Fixed position, full height.
 */

import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  MessageSquare,
  Package,
  FileText,
  Settings,
  Shield,
  Users,
  Wrench,
  Bug,
  GitBranch,
  LogOut,
  ScrollText,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth'

const MAIN_NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, hideForCustomer: true },
  { to: '/chat', label: 'Chat', icon: MessageSquare, hideForCustomer: true },
  { to: '/products', label: 'Products', icon: Package, hideForCustomer: true },
  { to: '/reports', label: 'Reports', icon: FileText, hideForCustomer: true },
  { to: '/my-reports', label: 'My Reports', icon: FileText, customerOnly: true },
  { to: '/settings', label: 'Settings', icon: Settings },
]

const ADMIN_NAV = [
  { to: '/admin', label: 'Admin Dashboard', icon: Shield },
  { to: '/admin/users', label: 'Users', icon: Users },
  { to: '/admin/config', label: 'Configuration', icon: Wrench },
  { to: '/admin/bugs', label: 'Bug Reports', icon: Bug },
  { to: '/admin/versions', label: 'Versions', icon: GitBranch },
  { to: '/admin/audit', label: 'Audit Log', icon: ScrollText, orgAdminOnly: true },
]

const ADMIN_ROLES = ['org_admin', 'admin']

function SidebarLink({
  to,
  label,
  icon: Icon,
  end,
}: {
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  end?: boolean
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
          isActive
            ? 'bg-accent/10 text-accent'
            : 'text-gray-300 hover:bg-white/5 hover:text-white'
        )
      }
    >
      <Icon className="h-5 w-5 shrink-0" />
      <span>{label}</span>
    </NavLink>
  )
}

export function Sidebar() {
  const { role, profile, logout } = useAuthStore()
  const isCustomer = role === 'customer'
  const isAdmin = role ? ADMIN_ROLES.includes(role) : false
  const isOrgAdmin = role === 'org_admin'

  const mainItems = MAIN_NAV.filter((item) => {
    if (item.hideForCustomer && isCustomer) return false
    if (item.customerOnly && !isCustomer) return false
    return true
  })

  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col bg-navy lg:flex">
      {/* Branding */}
      <div className="flex h-16 items-center gap-3 border-b border-white/10 px-5">
        <span className="text-2xl">🐄</span>
        <div>
          <h1 className="text-base font-bold leading-tight text-white">
            CowCare Tool
          </h1>
          <p className="text-[11px] text-blue-300">Bower Ag Expert System</p>
        </div>
      </div>

      {/* Main nav */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {mainItems.map((item) => (
          <SidebarLink
            key={item.to}
            to={item.to}
            label={item.label}
            icon={item.icon}
            end={item.to === '/' || item.to === '/my-reports'}
          />
        ))}

        {/* Admin section */}
        {isAdmin && (
          <>
            <div className="my-4 border-t border-white/10" />
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-gray-500">
              Admin
            </p>
            {ADMIN_NAV
              .filter((item) => !('orgAdminOnly' in item && item.orgAdminOnly) || isOrgAdmin)
              .map((item) => (
              <SidebarLink
                key={item.to}
                to={item.to}
                label={item.label}
                icon={item.icon}
                end={item.to === '/admin'}
              />
            ))}
          </>
        )}
      </nav>

      {/* User / logout */}
      <div className="border-t border-white/10 p-4">
        <div className="mb-3 truncate text-sm text-gray-300">
          <p className="font-medium text-white">
            {profile?.full_name || 'Bower Ag User'}
          </p>
          <p className="text-xs capitalize text-gray-400">
            {role?.replace('_', ' ') || 'Loading…'}
          </p>
        </div>
        <button
          onClick={() => logout()}
          className="tap-target flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-400 transition-colors hover:bg-white/5 hover:text-white"
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </button>
      </div>
    </aside>
  )
}
