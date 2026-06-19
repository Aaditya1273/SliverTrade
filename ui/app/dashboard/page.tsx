'use client'

'use client'

import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, TrendingDown, Loader2 } from 'lucide-react'
import { PortfolioCard } from '@/components/dashboard/portfolio-card'
import { PnLChart } from '@/components/dashboard/pnl-chart'
import { AIFeed } from '@/components/dashboard/ai-feed'
import { AlertsList } from '@/components/dashboard/alerts-list'
import { usePortfolio, type Holding } from '@/hooks/usePortfolio'
import { useAuth } from '@/hooks/useAuth'
import { useHideBalances } from './layout'

export default function DashboardPage() {
  const { apiKey } = useAuth()
  const { hideBalances } = useHideBalances()
  const { holdings, isLoading: holdingsLoading, error: holdingsError } = usePortfolio(apiKey)

  return (
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
  )
}
