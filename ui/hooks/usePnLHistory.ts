'use client'

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { PLATFORM } from '@/lib/api-config'

export interface Trade {
  symbol: string
  exchange: string
  action: 'BUY' | 'SELL'
  quantity: number
  price: number
  trade_value: number
  pnl: number
  trade_date: string
  timestamp: string
}

export interface PnLPoint {
  date: string
  cumulativePnL: number
  dayPnL: number
  trades: number
}

export interface PnLHistoryResult {
  /** Sorted oldest → newest for charting via recharts or similar. */
  data: PnLPoint[]
  /** Summary stats for display cards. */
  summary: {
    totalTrades: number
    totalPnL: number
    avgDayPnL: number
    winningDays: number
    losingDays: number
    bestDay: PnLPoint | null
    worstDay: PnLPoint | null
  }
  isLoading: boolean
  error: Error | null
  refetch: () => void
}

/**
 * Fetches the user's tradebook from the Platform API and computes daily
 * cumulative P&L for the dashboard performance chart.
 *
 * Data source: POST /api/v1/tradebook (Platform API, port 5000)
 * Requires a valid apiKey from an authenticated broker connection.
 *
 * Returns:
 *   - data: array of { date, cumulativePnL, dayPnL, trades } sorted by date
 *   - summary: aggregate stats for display cards
 *   - isLoading / error / refetch
 */
export function usePnLHistory(apiKey: string | null, days: number = 30): PnLHistoryResult {
  const { data: rawTrades, isLoading, error, refetch } = useQuery<Trade[]>({
    queryKey: ['tradebook', apiKey, days],
    queryFn: async () => {
      if (!apiKey) return []

      const { data } = await axios.post(PLATFORM('/api/v1/tradebook'), {
        apikey: apiKey,
        days,
      })

      if (data.status === 'error') throw new Error(data.message || 'Failed to fetch tradebook')

      // The response structure can be nested — normalise it
      const trades: Trade[] =
        data.data?.trades ??
        data.data ??
        data.trades ??
        []

      return trades
    },
    // Refresh every 5 minutes (trades don't change every second)
    refetchInterval: 300_000,
    enabled: !!apiKey,
    retry: 2,
    staleTime: 60_000,
  })

  const result = useMemo(() => {
    if (!rawTrades || rawTrades.length === 0) {
      return {
        data: [] as PnLPoint[],
        summary: {
          totalTrades: 0,
          totalPnL: 0,
          avgDayPnL: 0,
          winningDays: 0,
          losingDays: 0,
          bestDay: null,
          worstDay: null,
        },
      }
    }

    // 1. Group trades by date (YYYY-MM-DD)
    const dayMap = new Map<string, Trade[]>()
    for (const trade of rawTrades) {
      // Try multiple date field formats
      const dateStr = trade.trade_date ?? trade.timestamp?.split('T')[0]
      if (!dateStr) continue
      if (!dayMap.has(dateStr)) dayMap.set(dateStr, [])
      dayMap.get(dateStr)!.push(trade)
    }

    // 2. Compute cumulative P&L per day
    const sortedDates = Array.from(dayMap.keys()).sort()
    let cumulative = 0
    const points: PnLPoint[] = []

    for (const date of sortedDates) {
      const dayTrades = dayMap.get(date)!
      const dayPnL = dayTrades.reduce((sum, t) => sum + (t.pnl ?? 0), 0)
      cumulative += dayPnL

      points.push({
        date,
        cumulativePnL: Math.round(cumulative * 100) / 100,
        dayPnL: Math.round(dayPnL * 100) / 100,
        trades: dayTrades.length,
      })
    }

    // 3. Summary
    const winningDays = points.filter(p => p.dayPnL > 0)
    const losingDays = points.filter(p => p.dayPnL < 0)
    const totalPnL = points.length > 0 ? points[points.length - 1].cumulativePnL : 0
    const avgDayPnL = points.length > 0
      ? Math.round((points.reduce((s, p) => s + p.dayPnL, 0) / points.length) * 100) / 100
      : 0

    const bestDay = points.reduce((best, p) => p.dayPnL > (best?.dayPnL ?? -Infinity) ? p : best, null as PnLPoint | null)
    const worstDay = points.reduce((worst, p) => p.dayPnL < (worst?.dayPnL ?? Infinity) ? p : worst, null as PnLPoint | null)

    return {
      data: points,
      summary: {
        totalTrades: rawTrades.length,
        totalPnL,
        avgDayPnL,
        winningDays: winningDays.length,
        losingDays: losingDays.length,
        bestDay,
        worstDay,
      },
    }
  }, [rawTrades])

  return {
    data: result.data,
    summary: result.summary,
    isLoading,
    error,
    refetch,
  }
}
