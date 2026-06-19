'use client'

import { useState, createContext, useContext, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { Sidebar } from '@/components/dashboard/sidebar'
import { DashboardHeader } from '@/components/dashboard/header'
import { SystemFooter } from '@/components/dashboard/system-footer'
import { Loader2 } from 'lucide-react'

// Share hideBalances state across all dashboard pages
const HideBalancesContext = createContext<{
  hideBalances: boolean
  setHideBalances: (v: boolean) => void
}>({ hideBalances: false, setHideBalances: () => {} })

export function useHideBalances() {
  return useContext(HideBalancesContext)
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [hideBalances, setHideBalances] = useState(false)
  const { authenticated, loading } = useAuth()
  const router = useRouter()

  // Auth guard — redirect to login if not authenticated
  useEffect(() => {
    if (!loading && !authenticated) {
      router.push('/login')
    }
  }, [authenticated, loading, router])

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-accent" />
          <p className="text-sm text-muted-foreground">Checking session...</p>
        </div>
      </div>
    )
  }

  // Not authenticated — will redirect
  if (!authenticated) {
    return null
  }

  return (
    <HideBalancesContext.Provider value={{ hideBalances, setHideBalances }}>
    <div className="min-h-screen bg-background text-foreground flex">
      {/* Sidebar */}
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Top Header */}
        <DashboardHeader
          hideBalances={hideBalances}
          setHideBalances={setHideBalances}
          onMenuClick={() => setSidebarOpen(true)}
        />

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto pb-12">
          {children}
        </main>

        {/* System Status Footer */}
        <SystemFooter />
      </div>
    </div>
    </HideBalancesContext.Provider>
  )
}
