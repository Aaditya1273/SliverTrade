'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { useRouter } from 'next/navigation'
import { Bell, Settings, LogOut, TrendingUp, TrendingDown, Zap, Eye, EyeOff, Menu, X, Loader2 } from 'lucide-react'
import { DashboardHeader } from '@/components/dashboard/header'
import { PortfolioCard } from '@/components/dashboard/portfolio-card'
import { PnLChart } from '@/components/dashboard/pnl-chart'
import { AIFeed } from '@/components/dashboard/ai-feed'
import { AlertsList } from '@/components/dashboard/alerts-list'
import { useQueryClient } from '@tanstack/react-query'
import { useSystemHealth, SystemStatusDot } from '@/hooks/useSystemHealth'
import { usePortfolio, type Holding } from '@/hooks/usePortfolio'
import { useAuth } from '@/hooks/useAuth'
import { PLATFORM } from '@/lib/api-config'

export default function DashboardPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [hideBalances, setHideBalances] = useState(false)
  const systemHealth = useSystemHealth()
  const { apiKey } = useAuth()
  const router = useRouter()
  const queryClient = useQueryClient()
  const { holdings, isLoading: holdingsLoading, error: holdingsError } = usePortfolio(apiKey)

  const handleLogout = async () => {
    try {
      await fetch(PLATFORM('/auth/logout'), {
        method: 'POST',
        credentials: 'include',
      })
    } catch {
      // Proceed with redirect even if logout API call fails
    }
    // Clear all cached data (signals, portfolio, etc.)
    queryClient.clear()
    router.push('/login')
    router.refresh()
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      {/* Mobile Sidebar Toggle */}
      <div className="md:hidden flex items-center justify-between p-4 border-b border-border">
        <Link href="/" className="text-xl font-bold tracking-tight">SilverTrade</Link>
        <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 hover:bg-card/50 rounded-lg transition-colors">
          {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      <div className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <aside className={`${sidebarOpen ? 'absolute z-40 left-0 top-0' : 'hidden md:block'} w-full md:w-64 bg-card/50 border-r border-border overflow-y-auto`}>
          <div className="p-4 md:p-6">
            <Link href="/" className="text-xl font-bold tracking-tight hidden md:block mb-8">SilverTrade</Link>
            
            <nav className="space-y-2">
              <a href="#" className="flex items-center gap-3 px-4 py-2 rounded-lg bg-accent/10 text-accent font-medium transition-colors">
                <TrendingUp className="w-5 h-5" />
                Dashboard
              </a>
              <a href="#" className="flex items-center gap-3 px-4 py-2 rounded-lg text-muted-foreground hover:bg-card/50 transition-colors">
                <Zap className="w-5 h-5" />
                AI Signals
              </a>
              <a href="#" className="flex items-center gap-3 px-4 py-2 rounded-lg text-muted-foreground hover:bg-card/50 transition-colors">
                <Bell className="w-5 h-5" />
                Alerts
              </a>
              <a href="#" className="flex items-center gap-3 px-4 py-2 rounded-lg text-muted-foreground hover:bg-card/50 transition-colors">
                <Settings className="w-5 h-5" />
                Settings
              </a>
            </nav>

            <div className="mt-8 pt-8 border-t border-border">
              <button 
                onClick={handleLogout}
                className="flex items-center gap-3 px-4 py-2 rounded-lg text-muted-foreground hover:bg-card/50 w-full transition-colors"
              >
                <LogOut className="w-5 h-5" />
                Sign Out
              </button>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto">
          <DashboardHeader hideBalances={hideBalances} setHideBalances={setHideBalances} />

          <div className="p-4 md:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
            {/* Portfolio Summary */}
            <PortfolioCard hideBalances={hideBalances} apiKey={apiKey} />

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column - Charts & Alerts */}
              <div className="lg:col-span-2 space-y-6">
                {/* Portfolio P&L Performance */}
                <Card className="p-6 border-border">
                  <h2 className="text-lg font-semibold mb-6 flex items-center justify-between">
                    P&amp;L Performance
                    <span className="text-xs font-normal text-muted-foreground">Tradebook</span>
                  </h2>
                  <PnLChart />
                </Card>

                {/* Assets Table */}
                <Card className="p-6 border-border">
                  <h2 className="text-lg font-semibold mb-6">Holdings</h2>
                  {!apiKey ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center mb-4">
                        <TrendingUp className="w-6 h-6 text-accent" />
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">No holdings found</p>
                      <p className="text-xs text-muted-foreground">Connect a broker or make your first trade to see your holdings here.</p>
                    </div>
                  ) : holdingsLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="w-6 h-6 animate-spin text-accent" />
                    </div>
                  ) : holdingsError ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <p className="text-sm text-destructive mb-1">Failed to load holdings</p>
                      <p className="text-xs text-muted-foreground">Check broker connection</p>
                    </div>
                  ) : holdings.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center mb-4">
                        <TrendingUp className="w-6 h-6 text-accent" />
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">No holdings found</p>
                      <p className="text-xs text-muted-foreground">Make your first trade to see your holdings here.</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {holdings.map((asset: Holding) => (
                        <div key={asset.symbol} className="flex items-center justify-between p-3 rounded-lg hover:bg-card/30 transition-colors border border-transparent hover:border-border">
                          <div>
                            <p className="font-medium">{asset.symbol}</p>
                            <p className="text-sm text-muted-foreground">{asset.exchange}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-medium">${asset.current_value?.toLocaleString()}</p>
                            <p className={`text-sm ${asset.pnl >= 0 ? 'text-accent' : 'text-destructive'}`}>
                              {asset.pnl >= 0 ? '+' : ''}{asset.pnl_pct?.toFixed(1)}%
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>

              {/* Right Column - AI Feed & Alerts */}
              <div className="space-y-6">
                <AIFeed />
                <AlertsList />
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* System Status Footer */}
      <footer className="fixed bottom-0 left-0 right-0 h-8 bg-card/80 backdrop-blur-md border-t border-border flex items-center justify-between px-4 z-50">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <SystemStatusDot status={systemHealth.platform} />
            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Platform: {systemHealth.platform}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <SystemStatusDot status={systemHealth.strategy} />
            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">AI Engine: {systemHealth.strategy}</span>
          </div>
        </div>
        <div className="text-[10px] text-muted-foreground uppercase tracking-wider font-mono">
          {systemHealth.lastUpdated}
        </div>
      </footer>
    </main>
  )
}
