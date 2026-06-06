'use client'

import Link from 'next/link'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Shield, AlertTriangle, Wifi, ArrowRight } from 'lucide-react'
import { usePortfolio } from '@/hooks/usePortfolio'

export function RiskPanel({ apiKey }: { apiKey: string | null }) {
  if (!apiKey) {
    return (
      <Card className="p-6 border-border bg-amber-500/5 border-amber-500/20">
        <div className="flex flex-col items-center text-center py-4">
          <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-amber-500/10 flex items-center justify-center">
            <Shield className="w-6 h-6 text-amber-500" />
          </div>
          <p className="text-sm font-medium mb-1">Broker not connected</p>
          <p className="text-xs text-muted-foreground mb-4 max-w-xs">Connect a broker to view portfolio risk metrics, margin usage, and day P&L.</p>
          <Link
            href="/setup"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold transition-colors"
          >
            <Wifi className="w-3.5 h-3.5" />
            Connect Broker
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </Card>
    )
  }

  const { funds, totalValue, dayPnL, isLoading } = usePortfolio(apiKey)

  if (isLoading) {
    return (
      <Card className="p-6 border-border">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5 text-accent" />
          <h3 className="font-semibold">Portfolio Risk</h3>
        </div>
        <p className="text-sm text-muted-foreground">Loading risk metrics...</p>
      </Card>
    )
  }

  const dayPnLPct = totalValue > 0 ? (dayPnL / totalValue) * 100 : 0
  
  // Calculate capital at risk (using used margin as proxy)
  const usedMargin = funds?.used_margin || 0
  const capitalAtRisk = usedMargin
  const capitalAtRiskPct = totalValue > 0 ? (capitalAtRisk / totalValue) * 100 : 0
  
  // Determine risk level color
  const getRiskColor = (pct: number) => {
    if (pct < 5) return 'text-emerald-500'
    if (pct < 10) return 'text-yellow-500'
    return 'text-rose-500'
  }

  const getRiskLabel = (pct: number) => {
    if (pct < 5) return 'LOW'
    if (pct < 10) return 'MODERATE'
    return 'HIGH'
  }

  const getDayPnLColor = (pct: number) => {
    if (pct > 0) return 'text-emerald-500'
    if (pct > -2) return 'text-yellow-500'
    return 'text-rose-500'
  }

  return (
    <Card className="p-6 border-border">
      <div className="flex items-center gap-2 mb-4">
        <Shield className="w-5 h-5 text-accent" />
        <h3 className="font-semibold">Portfolio Risk</h3>
      </div>

      <div className="space-y-4">
        {/* Risk Overview */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Capital at Risk</p>
            <p className={`text-lg font-bold ${getRiskColor(capitalAtRiskPct)}`}>
              ₹{capitalAtRisk.toLocaleString()}
              <span className="text-sm ml-1">({capitalAtRiskPct.toFixed(1)}%)</span>
            </p>
            <Badge variant="outline" className={`text-xs mt-1 ${getRiskColor(capitalAtRiskPct)}`}>
              {getRiskLabel(capitalAtRiskPct)}
            </Badge>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Day P&L</p>
            <p className={`text-lg font-bold ${getDayPnLColor(dayPnLPct)}`}>
              {dayPnL >= 0 ? '+' : ''}₹{dayPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              <span className="text-sm ml-1">({dayPnLPct.toFixed(2)}%)</span>
            </p>
          </div>
        </div>

        {/* Daily Loss Progress Bar */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Daily Loss Limit</span>
            <span className={getDayPnLColor(dayPnLPct)}>
              {Math.abs(dayPnLPct).toFixed(1)}% / 5.0%
            </span>
          </div>
          <div className="w-full bg-card/50 rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                Math.abs(dayPnLPct) < 2 ? 'bg-emerald-500' :
                Math.abs(dayPnLPct) < 4 ? 'bg-yellow-500' : 'bg-rose-500'
              }`}
              style={{ width: `${Math.min(Math.abs(dayPnLPct) / 5 * 100, 100)}%` }}
            />
          </div>
        </div>

        {/* Position Count */}
        <div className="flex items-center justify-between py-2 border-t border-border/50">
          <span className="text-sm text-muted-foreground">Margin Used</span>
          <span className="text-sm font-medium">₹{usedMargin.toLocaleString()}</span>
        </div>

        {/* Warnings */}
        {dayPnLPct < -2 && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20">
            <AlertTriangle className="w-4 h-4 text-rose-500 mt-0.5" />
            <p className="text-xs text-rose-500">
              Daily loss exceeds 2%. Consider reviewing your risk settings or closing positions.
            </p>
          </div>
        )}
      </div>
    </Card>
  )
}
