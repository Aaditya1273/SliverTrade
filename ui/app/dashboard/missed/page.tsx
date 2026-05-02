'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { TrendingUp, TrendingDown, Clock, DollarSign, Target, Zap } from 'lucide-react'

interface MissedOpportunity {
  id: number
  symbol: string
  signal: 'buy' | 'sell'
  entryPrice: number
  actualPrice: number
  missedProfit: number
  missedPercentage: number
  timeAgo: string
  reason: string
  confidence: number
}

export default function MissedProfitsPage() {
  const [filter, setFilter] = useState<'all' | 'buy' | 'sell'>('all')

  const missedOpportunities: MissedOpportunity[] = [
    {
      id: 1,
      symbol: 'BTC',
      signal: 'buy',
      entryPrice: 65200,
      actualPrice: 67430,
      missedProfit: 2230,
      missedPercentage: 3.4,
      timeAgo: '12 hours ago',
      reason: 'Golden crossover with 91% historical accuracy',
      confidence: 91,
    },
    {
      id: 2,
      symbol: 'ETH',
      signal: 'sell',
      entryPrice: 3950,
      actualPrice: 3850,
      missedProfit: 100,
      missedPercentage: 2.5,
      timeAgo: '5 hours ago',
      reason: 'Death cross formation detected',
      confidence: 78,
    },
    {
      id: 3,
      symbol: 'SOL',
      signal: 'buy',
      entryPrice: 175,
      actualPrice: 198,
      missedProfit: 23,
      missedPercentage: 13.1,
      timeAgo: '2 hours ago',
      reason: 'Volume surge with RSI divergence',
      confidence: 85,
    },
    {
      id: 4,
      symbol: 'XRP',
      signal: 'buy',
      entryPrice: 2.45,
      actualPrice: 2.68,
      missedProfit: 0.23,
      missedPercentage: 9.4,
      timeAgo: '45 min ago',
      reason: 'Bullish pennant breakout',
      confidence: 72,
    },
    {
      id: 5,
      symbol: 'ADA',
      signal: 'sell',
      entryPrice: 1.15,
      actualPrice: 1.02,
      missedProfit: 0.13,
      missedPercentage: 11.3,
      timeAgo: '30 min ago',
      reason: 'Resistance rejection pattern',
      confidence: 68,
    },
  ]

  const totalMissed = missedOpportunities.reduce((sum, opp) => sum + opp.missedProfit, 0)
  const filtered = filter === 'all' 
    ? missedOpportunities 
    : missedOpportunities.filter(opp => opp.signal === filter)

  const stats = {
    totalMissed,
    averageMissedPercentage: (missedOpportunities.reduce((sum, opp) => sum + opp.missedPercentage, 0) / missedOpportunities.length).toFixed(1),
    totalSignals: missedOpportunities.length,
    highConfidenceSignals: missedOpportunities.filter(opp => opp.confidence >= 80).length,
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Missed Opportunities</h1>
          <p className="text-muted-foreground">Signals you missed and the profits you could have made</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card className="p-6 border-border">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-destructive/10 flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-destructive" />
              </div>
              <h3 className="font-medium text-sm text-muted-foreground">Total Missed Profit</h3>
            </div>
            <p className="text-3xl font-bold text-destructive">${stats.totalMissed.toLocaleString()}</p>
          </Card>

          <Card className="p-6 border-border">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-accent" />
              </div>
              <h3 className="font-medium text-sm text-muted-foreground">Avg. Missed %</h3>
            </div>
            <p className="text-3xl font-bold text-accent">+{stats.averageMissedPercentage}%</p>
          </Card>

          <Card className="p-6 border-border">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-secondary/10 flex items-center justify-center">
                <Zap className="w-5 h-5 text-secondary-foreground" />
              </div>
              <h3 className="font-medium text-sm text-muted-foreground">Total Signals</h3>
            </div>
            <p className="text-3xl font-bold">{stats.totalSignals}</p>
          </Card>

          <Card className="p-6 border-border">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
                <Target className="w-5 h-5 text-accent" />
              </div>
              <h3 className="font-medium text-sm text-muted-foreground">High Confidence</h3>
            </div>
            <p className="text-3xl font-bold">{stats.highConfidenceSignals}</p>
          </Card>
        </div>

        {/* Filter Tabs */}
        <Tabs value={filter} onValueChange={(v) => setFilter(v as 'all' | 'buy' | 'sell')} className="mb-8">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="all">All Signals ({missedOpportunities.length})</TabsTrigger>
            <TabsTrigger value="buy">Buy Signals ({missedOpportunities.filter(o => o.signal === 'buy').length})</TabsTrigger>
            <TabsTrigger value="sell">Sell Signals ({missedOpportunities.filter(o => o.signal === 'sell').length})</TabsTrigger>
          </TabsList>
        </Tabs>

        {/* Missed Opportunities List */}
        <div className="space-y-4">
          {filtered.map((opportunity) => (
            <Card key={opportunity.id} className="p-6 border-border hover:border-accent/30 transition-colors">
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-start">
                {/* Symbol & Signal */}
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <div className="text-2xl font-bold text-muted-foreground">{opportunity.symbol}</div>
                    <Badge
                      variant="outline"
                      className={`border-0 text-xs font-bold ${
                        opportunity.signal === 'buy'
                          ? 'bg-accent/10 text-accent'
                          : 'bg-destructive/10 text-destructive'
                      }`}
                    >
                      {opportunity.signal === 'buy' ? (
                        <TrendingUp className="w-3 h-3 mr-1" />
                      ) : (
                        <TrendingDown className="w-3 h-3 mr-1" />
                      )}
                      {opportunity.signal === 'buy' ? 'BUY' : 'SELL'}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">{opportunity.reason}</p>
                </div>

                {/* Price Info */}
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Entry Price</p>
                  <p className="font-semibold">${opportunity.entryPrice.toFixed(2)}</p>
                  <p className="text-xs text-muted-foreground mt-1">Actual Price</p>
                  <p className="font-semibold text-accent">${opportunity.actualPrice.toFixed(2)}</p>
                </div>

                {/* Missed Profit */}
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Missed Profit</p>
                  <p className="text-2xl font-bold text-destructive">${opportunity.missedProfit.toFixed(2)}</p>
                  <p className="text-xs text-destructive">+{opportunity.missedPercentage.toFixed(1)}%</p>
                </div>

                {/* Confidence */}
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Confidence</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 rounded-full bg-card/50 overflow-hidden">
                      <div
                        className={`h-full ${opportunity.confidence >= 80 ? 'bg-accent' : 'bg-secondary-foreground'}`}
                        style={{ width: `${opportunity.confidence}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold">{opportunity.confidence}%</span>
                  </div>
                </div>

                {/* Time */}
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Signal Time</p>
                  <p className="font-semibold flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    {opportunity.timeAgo}
                  </p>
                  <Button size="sm" variant="outline" className="w-full mt-2 border-border hover:bg-card/50 text-xs">
                    Learn More
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Insights */}
        <Card className="mt-8 p-6 border-border bg-accent/5">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-accent" />
            Key Insights
          </h3>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>✓ Your missed opportunities averaged <span className="text-accent font-medium">{stats.averageMissedPercentage}% gains</span></li>
            <li>✓ {stats.highConfidenceSignals} signals had <span className="text-accent font-medium">80%+ confidence</span> - high reliability</li>
            <li>✓ Most signals came from <span className="text-accent font-medium">technical pattern analysis</span> and volume signals</li>
            <li>✓ Consider using alerts to get notified of future signals in real-time</li>
          </ul>
        </Card>
      </div>
    </main>
  )
}
