'use client'

import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { PLATFORM } from '@/lib/api-config'

export interface Funds {
  total_balance: number
  available_balance: number
  used_margin: number
  unrealised_pnl: number
  realised_pnl: number
}

export interface Holding {
  symbol: string
  exchange: string
  quantity: number
  avg_price: number
  ltp: number
  current_value: number
  pnl: number
  pnl_pct: number
}

/**
 * Fetches live portfolio data (funds + holdings) from the Platform API.
 * Refreshes every 30 seconds.
 * Disabled when apiKey is empty (no broker connected).
 */
export function usePortfolio(apiKey: string | null) {
  const hasKey = !!apiKey

  const funds = useQuery<Funds>({
    queryKey: ['funds', apiKey],
    queryFn: async () => {
      const { data } = await axios.post(PLATFORM('/api/v1/funds'), { apikey: apiKey })
      if (data.status === 'error') throw new Error(data.message)
      return data.data
    },
    refetchInterval: 30_000,
    enabled: hasKey,
    retry: 2,
    staleTime: 10_000,
  })

  const holdings = useQuery<Holding[]>({
    queryKey: ['holdings', apiKey],
    queryFn: async () => {
      const { data } = await axios.post(PLATFORM('/api/v1/holdings'), { apikey: apiKey })
      if (data.status === 'error') throw new Error(data.message)
      return data.data ?? []
    },
    refetchInterval: 30_000,
    enabled: hasKey,
    retry: 2,
    staleTime: 10_000,
  })

  const totalValue = (funds.data?.total_balance ?? 0) +
    (funds.data?.unrealised_pnl ?? 0)

  const dayPnL = funds.data?.unrealised_pnl ?? 0

  return {
    funds: funds.data ?? null,
    holdings: holdings.data ?? [],
    totalValue,
    dayPnL,
    isLoading: funds.isLoading || holdings.isLoading,
    error: funds.error ?? holdings.error ?? null,
    refetch: () => { funds.refetch(); holdings.refetch() },
  }
}
