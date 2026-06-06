'use client'

import { useQuery } from '@tanstack/react-query'
import { PLATFORM } from '@/lib/api-config'

export interface TradingSettings {
  default_exchange: string
  default_product_type: string
  default_order_type: string
  risk_per_trade_pct: number
  min_signal_confidence: number
  max_open_positions: number
  daily_loss_limit_pct: number
  auto_execute: boolean
}

const defaultSettings: TradingSettings = {
  default_exchange: 'NSE',
  default_product_type: 'MIS',
  default_order_type: 'MARKET',
  risk_per_trade_pct: 2,
  min_signal_confidence: 60,
  max_open_positions: 5,
  daily_loss_limit_pct: 5,
  auto_execute: false,
}

/**
 * Fetch the current user's trading settings from GET /api/v1/settings.
 *
 * Uses session-based auth (credentials: 'include').
 * Returns a full TradingSettings object with defaults for any unset fields.
 * The query is disabled when staleTime is set to avoid refetching on every signal poll.
 */
export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: async (): Promise<TradingSettings> => {
      try {
        const response = await fetch(PLATFORM('/api/v1/settings'), {
          method: 'GET',
          credentials: 'include',
          headers: { 'Accept': 'application/json' },
        })
        const result = await response.json()
        if (result.status === 'success' && result.data) {
          return {
            default_exchange: result.data.default_exchange ?? defaultSettings.default_exchange,
            default_product_type: result.data.default_product_type ?? defaultSettings.default_product_type,
            default_order_type: result.data.default_order_type ?? defaultSettings.default_order_type,
            risk_per_trade_pct: result.data.risk_per_trade_pct ?? defaultSettings.risk_per_trade_pct,
            min_signal_confidence: result.data.min_signal_confidence ?? defaultSettings.min_signal_confidence,
            max_open_positions: result.data.max_open_positions ?? defaultSettings.max_open_positions,
            daily_loss_limit_pct: result.data.daily_loss_limit_pct ?? defaultSettings.daily_loss_limit_pct,
            auto_execute: result.data.auto_execute ?? defaultSettings.auto_execute,
          }
        }
        return defaultSettings
      } catch {
        return defaultSettings
      }
    },
    staleTime: 30_000,       // Refetch at most every 30s
    refetchInterval: 30_000, // Poll every 30s to catch setting changes
  })
}
