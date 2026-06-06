'use client'

import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { createChart, ColorType, CandlestickSeries, HistogramSeries, IChartApi, ISeriesApi, CrosshairMode, UTCTimestamp } from 'lightweight-charts'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Loader2, Maximize2, Minimize2 } from 'lucide-react'
import { PLATFORM } from '@/lib/api-config'
import { useLivePrice, type Tick } from '@/hooks/useLivePrice'
import { cn } from '@/lib/utils'

interface Candle {
  time: UTCTimestamp
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface PriceChartLiveProps {
  symbol?: string
  exchange?: string
  height?: number
  compact?: boolean
}

const TIMEFRAMES = [
  { label: '1m', value: '1m' },
  { label: '5m', value: '5m' },
  { label: '15m', value: '15m' },
  { label: '1h', value: '1h' },
  { label: '4h', value: '4h' },
  { label: '1d', value: '1d' },
]

/** Fetch OHLCV candles from the Binance data service (port 5000). */
async function fetchCandles(
  symbol: string,
  exchange: string,
  interval: string,
  days: number = 7
): Promise<Candle[]> {
  const now = new Date()
  const start = new Date(now.getTime() - days * 24 * 60 * 60 * 1000)

  const { data } = await axios.post(PLATFORM('/api/v1/history'), {
    symbol,
    exchange,
    interval,
    start_date: start.toISOString().split('T')[0],
    end_date: now.toISOString().split('T')[0],
  })

  if (data.status === 'error') throw new Error(data.message || 'Failed to fetch candles')

  const raw = data.data ?? []
  const seen = new Set<number>()
  const deduped: Candle[] = []
  for (const c of raw) {
    const ts = Math.floor(c.timestamp ?? 0) as UTCTimestamp
    if (!ts || seen.has(ts)) continue
    seen.add(ts)
    deduped.push({
      time: ts,
      open: Number(c.open),
      high: Number(c.high),
      low: Number(c.low),
      close: Number(c.close),
      volume: Number(c.volume),
    })
  }

  return deduped.sort((a, b) => a.time - b.time)
}

function lookbackDays(interval: string): number {
  switch (interval) {
    case '1m': return 1
    case '5m': return 3
    case '15m': return 7
    case '1h': return 30
    case '4h': return 60
    case '1d': return 180
    default: return 7
  }
}

function formatPrice(v: number): string {
  return v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function PriceChartLive({
  symbol = 'BTC/USDT',
  exchange = 'CRYPTO',
  height = 400,
  compact = false,
}: PriceChartLiveProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const [selectedTF, setSelectedTF] = useState('15m')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const { tick, connected } = useLivePrice({ symbol, exchange, enabled: true })
  const lastCandleTimeRef = useRef<UTCTimestamp | null>(null)

  // Query: fetch historical candles
  const days = useMemo(() => lookbackDays(selectedTF), [selectedTF])
  const {
    data: candles = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['candles', symbol, exchange, selectedTF, days],
    queryFn: () => fetchCandles(symbol, exchange, selectedTF, days),
    refetchInterval: 60_000,
    retry: 2,
    staleTime: 30_000,
  })

  // ── Build chart ──────────────────────────────────────────────────
  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#888888',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#1a1a1a' },
        horzLines: { color: '#1a1a1a' },
      },
      width: chartContainerRef.current.clientWidth,
      height,
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#555555', width: 1, style: 2, labelBackgroundColor: '#1a9fff' },
        horzLine: { color: '#555555', width: 1, style: 2, labelBackgroundColor: '#1a9fff' },
      },
      timeScale: {
        borderColor: '#2a2a2a',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 8,
        barSpacing: compact ? 4 : 8,
      },
      rightPriceScale: {
        borderColor: '#2a2a2a',
        scaleMargins: { top: 0.05, bottom: 0.25 },
      },
      handleScroll: { vertTouchDrag: false },
    })

    // Candlestick series with current price line
    const cs = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
      lastValueVisible: true,
      priceLineVisible: true,
      priceLineColor: '#888888',
      priceLineStyle: 2, // dashed
      priceLineWidth: 1,
    })

    // Volume histogram
    const vs = chart.addSeries(HistogramSeries, {
      color: '#1a9fff33',
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    chartRef.current = chart
    candlestickSeriesRef.current = cs
    volumeSeriesRef.current = vs

    // ── Crosshair tooltip ──────────────────────────────────────────
    chart.subscribeCrosshairMove((param) => {
      if (!tooltipRef.current || !chartContainerRef.current) return
      const container = chartContainerRef.current
      const rect = container.getBoundingClientRect()

      if (!param.time || !param.point) {
        tooltipRef.current.style.display = 'none'
        return
      }

      const data = param.seriesData.get(cs) as {
        open: number; high: number; low: number; close: number
      } | undefined
      const volData = param.seriesData.get(vs) as { value: number } | undefined

      if (!data) {
        tooltipRef.current.style.display = 'none'
        return
      }

      const isUp = data.close >= data.open
      tooltipRef.current.style.display = 'block'

      // Position tooltip — keep within container bounds
      const tooltipW = 160
      let left = param.point.x + 12
      if (left + tooltipW > rect.width) left = param.point.x - tooltipW - 12
      let top = param.point.y - 60
      if (top < 0) top = param.point.y + 12
      if (top + 120 > rect.height) top = rect.height - 130

      tooltipRef.current.style.left = `${left}px`
      tooltipRef.current.style.top = `${top}px`

      tooltipRef.current.innerHTML = `
        <div style="font-size:10px;font-weight:600;color:${isUp ? '#22c55e' : '#ef4444'};margin-bottom:4px;border-bottom:1px solid #2a2a2a;padding-bottom:3px">
          O ${formatPrice(data.open)}
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1px 8px;font-size:10px">
          <span style="color:#888">H</span><span style="text-align:right;font-weight:500">${formatPrice(data.high)}</span>
          <span style="color:#888">L</span><span style="text-align:right;font-weight:500">${formatPrice(data.low)}</span>
          <span style="color:#888">C</span><span style="text-align:right;font-weight:500;color:${isUp ? '#22c55e' : '#ef4444'}">${formatPrice(data.close)}</span>
          <span style="color:#888">Vol</span><span style="text-align:right;font-weight:500">${volData ? (volData.value / 1).toFixed(0) : '—'}</span>
        </div>
      `
    })

    // Handle resize
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
  }, [height, compact])

  // ── Update data when candles load ────────────────────────────────
  useEffect(() => {
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current || candles.length === 0) return

    const candleData = candles.map(c => ({
      time: c.time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }))

    const volumeData = candles.map(c => ({
      time: c.time,
      value: c.volume,
      color: c.close >= c.open ? '#22c55e33' : '#ef444433',
    }))

    candlestickSeriesRef.current.setData(candleData)
    volumeSeriesRef.current.setData(volumeData)
    chartRef.current?.timeScale().fitContent()

    if (candles.length > 0) {
      lastCandleTimeRef.current = candles[candles.length - 1].time
    }
  }, [candles])

  // ── Live tick update ─────────────────────────────────────────────
  useEffect(() => {
    if (!tick || !candlestickSeriesRef.current || !volumeSeriesRef.current) return
    if (!lastCandleTimeRef.current || candles.length === 0) return

    const tickTime = Math.floor(tick.timestamp) as UTCTimestamp
    const lastTime = lastCandleTimeRef.current

    if (tickTime >= lastTime) {
      const last = candles[candles.length - 1]
      const updatedClose = tick.ltp

      candlestickSeriesRef.current.update({
        time: lastTime,
        open: last.open,
        high: Math.max(last.high, updatedClose, tick.ltp),
        low: Math.min(last.low, updatedClose, tick.ltp),
        close: updatedClose,
      })

      volumeSeriesRef.current.update({
        time: lastTime,
        value: last.volume,
        color: updatedClose >= last.open ? '#22c55e33' : '#ef444433',
      })
    }
  }, [tick, candles])

  const toggleFullscreen = useCallback(() => {
    setIsFullscreen(prev => !prev)
    setTimeout(() => {
      chartRef.current?.applyOptions({
        width: chartContainerRef.current?.clientWidth ?? 600,
      })
      chartRef.current?.timeScale().fitContent()
    }, 100)
  }, [])

  return (
    <div className={cn(
      'relative flex flex-col bg-card/30 rounded-xl border border-border overflow-hidden transition-all duration-300',
      isFullscreen && 'fixed inset-4 z-50 bg-card shadow-2xl'
    )}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/50 bg-card/20">
        <div className="flex items-center gap-1.5">
          {TIMEFRAMES.map(tf => (
            <button
              key={tf.value}
              onClick={() => setSelectedTF(tf.value)}
              className={cn(
                'px-2.5 py-1 text-[11px] font-medium rounded-md transition-all',
                selectedTF === tf.value
                  ? 'bg-accent/20 text-accent'
                  : 'text-muted-foreground hover:text-foreground hover:bg-card/50'
              )}
            >
              {tf.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div className={cn(
              'w-1.5 h-1.5 rounded-full animate-pulse',
              connected ? 'bg-emerald-500' : 'bg-yellow-500'
            )} />
            <span className="text-[10px] text-muted-foreground">
              {connected ? 'Live' : 'Reconnecting'}
            </span>
          </div>
          <button
            onClick={toggleFullscreen}
            className="p-1 rounded hover:bg-card/50 text-muted-foreground hover:text-foreground transition-colors"
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Chart area */}
      <div className="relative flex-1 min-h-[200px]">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/60 z-10 backdrop-blur-sm">
            <Loader2 className="w-6 h-6 animate-spin text-accent" />
          </div>
        )}

        {error && !isLoading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center z-10 gap-2 p-4">
            <p className="text-sm text-destructive font-medium">Failed to load chart data</p>
            <p className="text-xs text-muted-foreground text-center max-w-md">{error.message}</p>
            <button
              onClick={() => refetch()}
              className="px-3 py-1.5 text-xs font-medium bg-accent/10 text-accent rounded-md hover:bg-accent/20 transition-colors mt-1"
            >
              Retry
            </button>
          </div>
        )}

        {!isLoading && !error && candles.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <p className="text-sm text-muted-foreground">No data available for {symbol}</p>
          </div>
        )}

        <div ref={chartContainerRef} className="w-full" style={{ height: isFullscreen ? undefined : height }} />

        {/* Crosshair tooltip */}
        <div
          ref={tooltipRef}
          className="absolute pointer-events-none z-20 hidden bg-card/95 border border-border rounded-lg px-3 py-2 shadow-lg"
          style={{ minWidth: 120 }}
        />
      </div>

      {/* Footer: last price + change */}
      {tick && (
        <div className="flex items-center justify-between px-3 py-1.5 border-t border-border/50 bg-card/20">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold">
              ${formatPrice(tick.ltp)}
            </span>
            <span className={cn(
              'text-xs font-medium',
              tick.change >= 0 ? 'text-emerald-500' : 'text-red-500'
            )}>
              {tick.change >= 0 ? '+' : ''}{tick.change?.toFixed(2)} ({tick.change_pct?.toFixed(2)}%)
            </span>
          </div>
          <span className="text-[10px] text-muted-foreground">
            {symbol} · {selectedTF}
          </span>
        </div>
      )}
    </div>
  )
}
