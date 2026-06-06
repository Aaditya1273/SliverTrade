'use client'

import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, AreaSeries, IChartApi, ISeriesApi, Time } from 'lightweight-charts'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useAuth } from '@/hooks/useAuth'
import { PLATFORM } from '@/lib/api-config'
import { Loader2 } from 'lucide-react'

type Range = '7d' | '30d' | '90d'

/**
 * Portfolio P&L chart.
 *
 * Fetches tradebook from POST /api/v1/tradebook (Platform API) and computes cumulative
 * P&L over the selected time range. Renders as an area chart with
 *
 * Expected API response shape:
 * {
 *   status: 'success',
 *   data: [{
 *     fill_timestamp: string,  // ISO date
 *     pnl?: string | number,   // field name may vary (pnl, profit_and_loss, net, pl, pnl_amt)
 *     ...
 *   }]
 * }
 * green fill above zero, red fill below zero.
 *
 * Shows an empty state when fewer than 2 trades exist.
 */
export function PerformanceChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null)
  const [range, setRange] = useState<Range>('30d')
  const { apiKey } = useAuth()

  const { data: trades, isLoading } = useQuery({
    queryKey: ['tradebook', range, apiKey],
    queryFn: async () => {
      if (!apiKey) return []
      const response = await axios.post(PLATFORM('/api/v1/tradebook'), { apikey: apiKey })
      if (response.data.status === 'error') throw new Error(response.data.message)
      return response.data.data ?? response.data.trades ?? []
    },
    enabled: !!apiKey,
    retry: 1,
  })

  // Compute cumulative P&L from trades
  const pnlData = (() => {
    if (!Array.isArray(trades) || trades.length < 2) return null

    const sorted = [...trades]
      .filter((t: any) => t.fill_timestamp || t.timestamp)
      .sort((a: any, b: any) => new Date(a.fill_timestamp || a.timestamp).getTime() - new Date(b.fill_timestamp || b.timestamp).getTime())

    let cumulative = 0
    const points: { time: Time; value: number }[] = []
    const now = Date.now()
    const rangeMs = { '7d': 7, '30d': 30, '90d': 90 }[range] * 24 * 60 * 60 * 1000
    const cutoff = now - rangeMs

    for (const t of sorted) {
      const ts = new Date(t.fill_timestamp || t.timestamp).getTime()
      if (ts < cutoff) continue

      // Expected Platform API tradebook fields: pnl, profit_and_loss, net
      const pnl = parseFloat(t.pnl ?? t.profit_and_loss ?? t.net ?? 0)
      if (isNaN(pnl)) continue

      cumulative += pnl
      points.push({ time: Math.floor(ts / 1000) as Time, value: cumulative })
    }

    return points.length >= 2 ? points : null
  })()

  const pnlPositive = pnlData ? pnlData[pnlData.length - 1].value >= 0 : true

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#a0a0a0',
      },
      grid: {
        vertLines: { color: '#1a1a1a' },
        horzLines: { color: '#1a1a1a' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 200,
      timeScale: {
        borderColor: '#1a1a1a',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: { borderColor: '#1a1a1a' },
    })

    const series = chart.addSeries(AreaSeries, {
      lineColor: '#22c55e',
      topColor: 'rgba(34, 197, 94, 0.3)',
      bottomColor: 'rgba(34, 197, 94, 0.0)',
      lineWidth: 2,
    })

    chartRef.current = chart
    seriesRef.current = series

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [])

  // Update data
  useEffect(() => {
    if (!seriesRef.current || !pnlData) return

    const lastValue = pnlData[pnlData.length - 1].value
    const color = lastValue >= 0 ? '#22c55e' : '#ef4444'
    const topColor = lastValue >= 0 ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'
    const bottomColor = lastValue >= 0 ? 'rgba(34, 197, 94, 0.0)' : 'rgba(239, 68, 68, 0.0)'

    seriesRef.current.applyOptions({ lineColor: color, topColor, bottomColor })
    seriesRef.current.setData(pnlData)
    chartRef.current?.timeScale().fitContent()
  }, [pnlData])

  // Not connected — show empty state
  if (!apiKey) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center">
        <p className="text-sm text-muted-foreground mb-1">Connect a broker to see your performance chart</p>
        <p className="text-xs text-muted-foreground">Your P&L history will appear here after your first trade.</p>
      </div>
    )
  }

  // Loading
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="w-5 h-5 animate-spin text-accent" />
      </div>
    )
  }

  // No data or too few trades
  if (!pnlData) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center">
        <p className="text-sm text-muted-foreground">Your performance chart will appear here after your first trade.</p>
      </div>
    )
  }

  return (
    <div>
      {/* Range selector */}
      <div className="flex items-center gap-2 mb-4">
        {(['7d', '30d', '90d'] as const).map(r => (
          <button
            key={r}
            onClick={() => setRange(r)}
            className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
              range === r
                ? 'bg-accent text-accent-foreground'
                : 'bg-card/50 text-muted-foreground hover:text-foreground border border-border'
            }`}
          >
            {r}
          </button>
        ))}
        <span className={`ml-auto text-sm font-semibold ${pnlPositive ? 'text-emerald-500' : 'text-red-500'}`}>
          {pnlPositive ? '+' : ''}${pnlData[pnlData.length - 1].value.toFixed(2)}
        </span>
      </div>
      <div ref={chartContainerRef} className="rounded-xl overflow-hidden" />
    </div>
  )
}
