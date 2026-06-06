'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import { API_CONFIG } from '@/lib/api-config'

export interface Tick {
  symbol: string
  ltp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  timestamp: number
  change: number
  change_pct: number
}

interface UseLivePriceOptions {
  symbol: string
  exchange?: string
  enabled?: boolean
}

/**
 * Connects to the Platform WebSocket proxy and subscribes to live price ticks.
 * Auto-reconnects on disconnect with 3-second backoff.
 */
export function useLivePrice({ symbol, exchange = 'NSE', enabled = true }: UseLivePriceOptions) {
  const [tick, setTick] = useState<Tick | null>(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    if (!enabled || !symbol) return

    try {
      const ws = new WebSocket(API_CONFIG.WS_BASE)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        setError(null)
        const token = localStorage.getItem('st_token')
        if (token) {
          ws.send(JSON.stringify({ action: 'authenticate', token }))
        }
        ws.send(JSON.stringify({ action: 'subscribe', symbol, exchange }))
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'tick' && data.symbol === symbol) {
            setTick(data)
          }
        } catch {
          // Ignore non-JSON messages
        }
      }

      ws.onclose = () => {
        setConnected(false)
        reconnectTimer.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => {
        setError('WebSocket connection failed')
        ws.close()
      }
    } catch {
      setError('Failed to create WebSocket connection')
    }
  }, [symbol, exchange, enabled])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { tick, connected, error }
}
