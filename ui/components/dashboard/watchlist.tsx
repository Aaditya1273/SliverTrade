'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, TrendingDown, Loader2, Plus } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useAuth } from '@/hooks/useAuth'
import { PLATFORM } from '@/lib/api-config'

interface WatchlistItem {
  symbol: string
  exchange: string
  ltp: number
  change: number
  change_pct: number
  volume: number
}

/**
 * Multi-symbol watchlist panel.
 *
 * Shows live quotes for the user's saved symbols.
 * Prices would update via WebSocket in production.
 */
export function Watchlist() {
  const { apiKey } = useAuth()
  const [expanded, setExpanded] = useState(true)

  // Default watchlist symbols — user can customise in Phase 8
  const defaultSymbols = [
    { symbol: 'BTC/USDT', exchange: 'CRYPTO' },
    { symbol: 'ETH/USDT', exchange: 'CRYPTO' },
    { symbol: 'SOL/USDT', exchange: 'CRYPTO' },
  ]

  const { data: quotes, isLoading } = useQuery({
    queryKey: ['watchlist', apiKey],
    queryFn: async () => {
      if (!apiKey) return []
      const response = await axios.post(PLATFORM('/api/v1/multiquotes'), {
        apikey: apiKey,
        symbols: defaultSymbols,
      })
      if (response.data.status === 'error') return []
      return response.data.data ?? response.data.quotes ?? []
    },
    enabled: !!apiKey,
    refetchInterval: 15_000,
    retry: 1,
  })

  const items = (Array.isArray(quotes) && quotes.length > 0 ? quotes : defaultSymbols.map(s => ({
    symbol: s.symbol,
    exchange: s.exchange,
    ltp: 0,
    change: 0,
    change_pct: 0,
    volume: 0,
  }))) as WatchlistItem[]

  return (
    <Card className="border-border overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-card/50 transition-colors"
      >
        <h3 className="text-sm font-semibold">Watchlist</h3>
        <div className="flex items-center gap-2">
          {!apiKey && <span className="text-[10px] text-muted-foreground">Connect broker</span>}
          {apiKey && <span className="text-[10px] text-muted-foreground">Custom watchlist (Phase 8)</span>}
        </div>
      </button>

      {expanded && (
        <div className="divide-y divide-border/50">
          {isLoading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="w-4 h-4 animate-spin text-accent" />
            </div>
          ) : (
            items.map((item) => {
              const positive = item.change_pct >= 0
              return (
                <div key={item.symbol} className="px-4 py-3 flex items-center justify-between hover:bg-card/30 transition-colors">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{item.symbol.split('/')[0]}</span>
                    <Badge variant="outline" className="text-[9px] px-1 py-0 border-border text-muted-foreground">
                      {item.exchange}
                    </Badge>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold">
                      {item.ltp > 0 ? `$${item.ltp.toLocaleString()}` : '—'}
                    </p>
                    <p className={`text-[10px] flex items-center gap-0.5 ${positive ? 'text-emerald-500' : 'text-red-500'}`}>
                      {positive ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
                      {item.change_pct !== 0 ? `${positive ? '+' : ''}${item.change_pct.toFixed(2)}%` : '—'}
                    </p>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}
    </Card>
  )
}
