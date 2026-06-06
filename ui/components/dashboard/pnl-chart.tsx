'use client'

import { useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { BarChart3, Loader2 } from 'lucide-react'
import { usePnLHistory, type PnLPoint } from '@/hooks/usePnLHistory'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

interface PnLChartProps {
  height?: number
}

function formatUSD(v: number): string {
  const abs = Math.abs(v)
  const formatted = abs.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return v < 0 ? `-$${formatted}` : `$${formatted}`
}

function PnLTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const p: PnLPoint = payload[0].payload
  return (
    <div className="bg-card/95 border border-border rounded-lg px-3 py-2 shadow-lg text-xs">
      <p className="font-medium text-muted-foreground mb-1">{label}</p>
      <div className="space-y-0.5">
        <p className="flex justify-between gap-4">
          <span>Cumulative P&L</span>
          <span className={cn('font-semibold', p.cumulativePnL >= 0 ? 'text-emerald-500' : 'text-red-500')}>
            {formatUSD(p.cumulativePnL)}
          </span>
        </p>
        <p className="flex justify-between gap-4">
          <span>Day P&L</span>
          <span className={cn('font-semibold', p.dayPnL >= 0 ? 'text-emerald-500' : 'text-red-500')}>
            {formatUSD(p.dayPnL)}
          </span>
        </p>
        <p className="text-muted-foreground">Trades: {p.trades}</p>
      </div>
    </div>
  )
}

export function PnLChart({ height = 300 }: PnLChartProps) {
  const { apiKey } = useAuth()

  const [range, setRange] = useState<number>(30)
  const { data, summary, isLoading, error, refetch } = usePnLHistory(apiKey, range)

  // No broker connected
  if (!apiKey) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center" style={{ height }}>
        <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center mb-4">
          <BarChart3 className="w-6 h-6 text-accent" />
        </div>
        <p className="text-sm text-muted-foreground mb-1">Your performance chart will appear here</p>
        <p className="text-xs text-muted-foreground">Connect a broker and start trading to see your P&amp;L history.</p>
      </div>
    )
  }

  // Loading
  if (isLoading) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <Loader2 className="w-6 h-6 animate-spin text-accent" />
      </div>
    )
  }

  // Error
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center" style={{ height }}>
        <p className="text-sm text-destructive font-medium mb-1">Failed to load P&amp;L history</p>
        <p className="text-xs text-muted-foreground mb-3">Check broker connection</p>
        <button
          onClick={() => refetch()}
          className="px-3 py-1.5 text-xs font-medium bg-accent/10 text-accent rounded-md hover:bg-accent/20 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  // Less than 2 trades
  if (data.length < 2) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center" style={{ height }}>
        <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center mb-4">
          <BarChart3 className="w-6 h-6 text-accent" />
        </div>
        <p className="text-sm text-muted-foreground mb-1">Not enough trade data yet</p>
        <p className="text-xs text-muted-foreground">Your performance chart will appear after your first few trades.</p>
      </div>
    )
  }

  const pnlPositive = summary.totalPnL >= 0

  return (
    <div className="space-y-4">
      {/* Summary stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 rounded-lg bg-card/30 border border-border">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Total P&amp;L</p>
          <p className={cn('text-base font-semibold', pnlPositive ? 'text-emerald-500' : 'text-red-500')}>
            {formatUSD(summary.totalPnL)}
          </p>
        </div>
        <div className="p-3 rounded-lg bg-card/30 border border-border">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Trades</p>
          <p className="text-base font-semibold">{summary.totalTrades}</p>
        </div>
        <div className="p-3 rounded-lg bg-card/30 border border-border">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Winning Days</p>
          <p className="text-base font-semibold text-emerald-500">{summary.winningDays}</p>
        </div>
        <div className="p-3 rounded-lg bg-card/30 border border-border">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Losing Days</p>
          <p className="text-base font-semibold text-red-500">{summary.losingDays}</p>
        </div>
      </div>

      {/* Range selector + chart */}
      <div>
        <div className="flex items-center justify-end mb-3 gap-1">
          {([7, 30, 90] as const).map(r => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={cn(
                'px-2.5 py-1 text-[11px] font-medium rounded-md transition-all',
                range === r
                  ? 'bg-accent/20 text-accent'
                  : 'text-muted-foreground hover:text-foreground hover:bg-card/50'
              )}
            >
              {r}d
            </button>
          ))}
        </div>

        <ResponsiveContainer width="100%" height={height}>
          <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id="pnlGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: '#888' }}
              tickFormatter={(v: string) => {
                const d = new Date(v)
                return `${d.getMonth() + 1}/${d.getDate()}`
              }}
              axisLine={{ stroke: '#2a2a2a' }}
              tickLine={false}
              minTickGap={20}
            />
            <YAxis
              tick={{ fontSize: 10, fill: '#888' }}
              tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
              axisLine={{ stroke: '#2a2a2a' }}
              tickLine={false}
              width={50}
            />
            <Tooltip content={<PnLTooltip />} />
            <Area
              type="monotone"
              dataKey="cumulativePnL"
              stroke="#22c55e"
              strokeWidth={2}
              fill="url(#pnlGradient)"
              dot={false}
              activeDot={{ r: 4, fill: '#22c55e', stroke: '#1a1a1a', strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
