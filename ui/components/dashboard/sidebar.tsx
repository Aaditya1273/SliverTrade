'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import {
  LayoutDashboard,
  TrendingUp,
  Bell,
  MessageSquare,
  History,
  Settings,
  Activity,
  CreditCard,
  LogOut,
  Menu,
  X,
  Sparkles,
  Shield,
  Users,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { PLATFORM } from '@/lib/api-config'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/dashboard/trade', label: 'Trade', icon: TrendingUp },
  { href: '/dashboard/missed', label: 'Missed Signals', icon: Bell },
  { href: '/dashboard/chat', label: 'AI Chat', icon: MessageSquare },
  { href: '/dashboard/chat/history', label: 'Chat History', icon: History },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings },
  { href: '/billing', label: 'Billing', icon: CreditCard },
  { href: '/pricing', label: 'Upgrade Plan', icon: Sparkles },
]

export function Sidebar({ open, onClose }: SidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const queryClient = useQueryClient()
  const { authenticated, loading } = useAuth()

  const isActive = (href: string) => {
    if (href === '/dashboard') return pathname === '/dashboard'
    return pathname.startsWith(href)
  }

  const handleLogout = async () => {
    try {
      await fetch(PLATFORM('/auth/logout'), {
        method: 'POST',
        credentials: 'include',
      })
    } catch {
      // Proceed even if API call fails
    }
    queryClient.clear()
    router.push('/login')
    router.refresh()
  }

  // Basic section check — admin links only shown for users with admin access
  const isAdmin = false // Will be checked via API in production

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`
          fixed md:sticky top-0 left-0 z-40
          h-full w-64 bg-card/95 backdrop-blur-xl
          border-r border-border
          overflow-y-auto
          transition-transform duration-300
          ${open ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between p-4 md:p-6 border-b border-border">
            <Link href="/" className="text-xl font-bold tracking-tight">
              SilverTrade
            </Link>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-card/50 transition-colors md:hidden"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-3 space-y-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon
              const active = isActive(item.href)
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onClose}
                  className={`
                    flex items-center gap-3 px-4 py-2.5 rounded-xl
                    text-sm font-medium
                    transition-all duration-200
                    ${
                      active
                        ? 'bg-accent/10 text-accent shadow-sm'
                        : 'text-muted-foreground hover:text-foreground hover:bg-card/50'
                    }
                  `}
                >
                  <Icon className={`w-5 h-5 ${active ? 'text-accent' : ''}`} />
                  {item.label}
                </Link>
              )
            })}

            {/* Divider */}
            <div className="my-3 border-t border-border" />

            {/* System Health — inline status */}
            <Link
              href="/admin"
              onClick={onClose}
              className={`
                flex items-center gap-3 px-4 py-2.5 rounded-xl
                text-sm font-medium
                transition-all duration-200
                ${isActive('/admin')
                  ? 'bg-accent/10 text-accent shadow-sm'
                  : 'text-muted-foreground hover:text-foreground hover:bg-card/50'
                }
              `}
            >
              <Shield className="w-5 h-5" />
              Admin
              <span className="ml-auto text-[10px] text-muted-foreground uppercase tracking-wider px-1.5 py-0.5 rounded-md bg-card/50 border border-border">
                Tools
              </span>
            </Link>
          </nav>

          {/* Logout */}
          <div className="p-3 border-t border-border">
            <button
              onClick={handleLogout}
              className="
                flex items-center gap-3 w-full px-4 py-2.5 rounded-xl
                text-sm font-medium text-muted-foreground
                hover:text-foreground hover:bg-card/50
                transition-all duration-200
              "
            >
              <LogOut className="w-5 h-5" />
              Sign Out
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
