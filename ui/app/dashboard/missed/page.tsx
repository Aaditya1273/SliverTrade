'use client'

import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DollarSign, Zap, TrendingUp, TrendingDown, Clock, AlertTriangle } from 'lucide-react'
import Link from 'next/link'
import { STRATEGY } from '@/lib/api-config'
import { Loader2 } from 'lucide-react'

const STRATEGY_BASE = STRATEGY('/api/v1')

interface MissedSignal {
  id: string
  symbol: string
  exchange: string
  decision: string
  confidence: number
  price: number
  outcome_price: number
  missed_profit_pct: number
  reasoning: string
  timestamp: string
}

export default function MissedProfitsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['missed-opportunities'],
    queryFn: async () => {
      const response = await axios.get(`${STRATEGY_BASE}/missed-opportunities`, {
        params: { days: 7, limit: 50 }
      })
      return response.data.data
    },
    refetchInterval: 60000,
  })

  const aggregate = data?.aggregate || {
    signals_missed_count: 0,
    total_missed_profit_pct: 0,
    avg_missed_pct: 0,
    high_confidence_missed: 0,
  }

  const signals = data?.signals || []

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return `${diffDays}d ago`
  }

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Missed Opportunities</h1>
          <p className="text-muted-foreground">
            Signals you didn't execute that would have been profitable
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card className="p-6 border-border">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-rose-500/10 flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-rose-500" />
              </div>
              <h3 className="font-medium text-sm text-muted-foreground">Total Missed Profit</h3>
            </div>
            <p className="text-3xl font-bold text-rose-500">
              {aggregate.signals_missed_count > 0 ? `${aggregate.total_missed_profit_pct.toFixed(1)}%` : '—'}
            </p>
          </Card>

          <Card className="p-6 border-border">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-emerald-500" />
              </div>
              <h3 className="font-medium text-sm text-muted-foreground">Avg. Missed %</h3>
            </div>
            <p className="text-3xl font-bold text-emerald-500">
              {aggregate.signals_missed_count > 0 ? `${aggregate.avg_missed_pct.toFixed(1)}%` : '—'}
            </p>
          </Card>

          <Card className="p-6 border-border">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
                <Zap className="w-5 h-5 text-accent" />
              </div>
              <h3 className="font-medium text-sm text-muted-foreground">Total Signals</h3>
            </div>
            <p className="text-3xl font-bold">{aggregate.signals_missed_count}</p>
          </Card>

          <Card className="p-6 border-border">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
              </div>
              <h3 className="font-medium text-sm text-muted-foreground">High Confidence</h3>
            </div>
            <p className="text-3xl font-bold text-amber-500">{aggregate.high_confidence_missed}</p>
          </Card>
        </div>

        {isLoading ? (
          <Card className="p-12 border-border flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-accent" />
          </Card>
        ) : error ? (
          <Card className="p-12 border-border flex items-center justify-center">
            <p className="text-destructive">Failed to load missed opportunities</p>
          </Card>
        ) : signals.length === 0 ? (
          <Card className="p-12 border-border flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-4">
              <Zap className="w-8 h-8 text-accent" />
            </div>
            <h2 className="text-xl font-semibold mb-2">No Missed Signals</h2>
            <p className="text-sm text-muted-foreground mb-6 max-w-md">
              {aggregate.signals_missed_count === 0 
                ? "Start generating signals to track your missed opportunities. Every signal you don't act on will be recorded here."
                : "Perfect execution! You acted on every profitable signal in this period."
              }
            </p>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-accent-foreground text-sm font-medium hover:bg-accent/90 transition-colors"
            >
              Go to Dashboard
            </Link>
          </Card>
        ) : (
          <div className="space-y-4">
            {signals.map((signal: MissedSignal) => (
              <Card key={signal.id} className="p-6 border-border bg-card/30 hover:border-accent/30 hover:bg-card/50 transition-all">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold">{signal.symbol}</span>
                    <Badge variant="outline" className="text-xs">{signal.exchange}</Badge>
                    <Badge
                      className={`text-xs ${
                        signal.decision === 'BUY'
                          ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-500 border-rose-500/20'
                      }`}
                    >
                      {signal.decision === 'BUY' ? (
                        <TrendingUp className="w-3 h-3 mr-1" />
                      ) : (
                        <TrendingDown className="w-3 h-3 mr-1" />
                      )}
                      {signal.decision}
                    </Badge>
                    {signal.confidence >= 80 && (
                      <Badge className="text-xs bg-amber-500/10 text-amber-500 border-amber-500/20">
                        High Confidence
                      </Badge>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-rose-500">
                      +{signal.missed_profit_pct.toFixed(1)}%
                    </div>
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatTime(signal.timestamp)}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
                  <div>
                    <div className="text-muted-foreground">Signal Price</div>
                    <div className="font-medium">${signal.price.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Price 1h Later</div>
                    <div className="font-medium">${signal.outcome_price.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Confidence</div>
                    <div className="font-medium">{signal.confidence}%</div>
                  </div>
                </div>

                <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                  {signal.reasoning}
                </p>

                <Button variant="outline" size="sm" className="w-full">
                  Enable Alerts for {signal.symbol}
                </Button>
              </Card>
            ))}
          </div>
        )}

        {/* Info card */}
        <Card className="mt-8 p-6 border-border bg-accent/5">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-accent" />
            How It Works
          </h3>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>✓ Every signal you don&apos;t execute is automatically tracked</li>
            <li>✓ Missed profit is calculated from actual price movement 1 hour after signal</li>
            <li>✓ High confidence signals (80%+) you missed are highlighted</li>
            <li>✓ Enable alerts to get notified of future signals in real-time</li>
          </ul>
        </Card>
      </div>
    </div>
  )
}
