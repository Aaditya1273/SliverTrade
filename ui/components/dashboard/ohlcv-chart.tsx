'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { createChart, CandlestickSeries, IChartApi, ISeriesApi, CandlestickData, HistogramSeries, Time, WhitespaceData, ColorType } from 'lightweight-charts'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Loader2 } from 'lucide-react'
import { DATA } from '@/lib/api-config'
import { useLivePrice } from '@/hooks/useLivePrice'
import { useAuth } from '@/hooks/useAuth'

interface OHLCVChartProps {
  symbol?: string
  exchange?: string
  height?: number
}

const TIMEFRAMES = [
  { label: '1m', value: '1m' },
  { label: '5m', value: '5m' },
  { label: '15m', value: '15m' },
  { label: '1h', value: '1h' },
  { label: '1d', value: '1d' },
] as const

type Timeframe = typeof TIMEFRAMES[number]['value']

export function OHLCVChart({ symbol = 'BTC/USDT', exchange = 'CRYPTO', height = 400 }: OHLCVChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const [timeframe, setTimeframe] = useState<Timeframe>('15m')
  const { apiKey } = useAuth()

  // Live price tick — used to update the last candle in real time
  const { tick, connected } = useLivePrice({ symbol, exchange })

  // Fetch OHLCV history from data_fetch service
  const { data: candles, isLoading, error } = useQuery({
    queryKey: ['ohlcv', symbol, exchange, timeframe],
    queryFn: async () => {
      const params = new URLSearchParams({
        symbol,
        exchange,
        interval: timeframe,
        limit: '200',
        ...(apiKey ? { apikey: apiKey } : {}),
      })
      const response = await axios.get(`${DATA('/api/data')}?${params}`)
      return response.data.data ?? response.data.candles ?? response.data ?? []
    },
    refetchInterval: timeframe === '1m' ? 30_000 : 60_000,
    retry: 2,
  })

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
      height,
      crosshair: {
        mode: 0,
        vertLine: { color: '#3b3b3b', width: 1, style: 2, labelBackgroundColor: '#1a1a1a' },
        horzLine: { color: '#3b3b3b', width: 1, style: 2, labelBackgroundColor: '#1a1a1a' },
      },
      timeScale: {
        borderColor: '#1a1a1a',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#1a1a1a',
      },
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderDownColor: '#ef4444',
      borderUpColor: '#22c55e',
      wickDownColor: '#ef4444',
      wickUpColor: '#22c55e',
    })

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    chartRef.current = chart
    candleSeriesRef.current = candleSeries
    volumeSeriesRef.current = volumeSeries

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
  }, [height])

  // Update chart when candle data arrives
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return
    const candleData = Array.isArray(candles) ? candles : []
    if (candleData.length === 0) return

    const formattedCandles: CandlestickData[] = []
    const formattedVolume: { time: Time; value: number; color: string }[] = []

    for (const d of candleData) {
      const time = d.time ?? d.timestamp ?? Math.floor(new Date(d.date ?? d.datetime).getTime() / 1000)
      const open = parseFloat(d.open ?? d.o)
      const high = parseFloat(d.high ?? d.h)
      const low = parseFloat(d.low ?? d.l)
      const close = parseFloat(d.close ?? d.c)
      const volume = parseFloat(d.volume ?? d.v ?? d.vol ?? 0)

      if (isNaN(open) || isNaN(high) || isNaN(low) || isNaN(close)) continue

      formattedCandles.push({ time: time as Time, open, high, low, close })
      formattedVolume.push({
        time: time as Time,
        value: volume,
        color: close >= open ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)',
      })
    }

    candleSeriesRef.current.setData(formattedCandles)
    volumeSeriesRef.current.setData(formattedVolume)
    chartRef.current?.timeScale().fitContent()
  }, [candles])

  // Update last candle in real time from live tick
  useEffect(() => {
    if (!candleSeriesRef.current || !tick || !Array.isArray(candles) || candles.length === 0) return

    const lastCandle = candleSeriesRef.current.dataByIndex(-1)
    if (!lastCandle) return

    // dataByIndex returns CandlestickData | WhitespaceData
    // WhitespaceData only has `time` — skip if no OHLC data
    const candle = lastCandle as CandlestickData
    if (candle.open === undefined) return

    const tickTime = Math.floor(tick.timestamp / 1000)
    // Only update if tick is within the current candle's timeframe window
    if (tickTime >= (candle.time as number)) {
      candleSeriesRef.current.update({
        time: candle.time,
        open: candle.open,
        high: Math.max(candle.high, tick.ltp),
        low: Math.min(candle.low, tick.ltp),
        close: tick.ltp,
      })
    }
  }, [tick, candles])

  return (
    <div className="relative w-full">
      {/* Timeframe selector */}
      <div className="flex items-center gap-1 mb-3">
        {TIMEFRAMES.map(tf => (
          <button
            key={tf.value}
            onClick={() => setTimeframe(tf.value)}
            className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
              timeframe === tf.value
                ? 'bg-accent text-accent-foreground'
                : 'bg-card/50 text-muted-foreground hover:text-foreground border border-border'
            }`}
          >
            {tf.label}
          </button>
        ))}
        {connected && (
          <span className="ml-auto flex items-center gap-1 text-[10px] text-emerald-500">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Live
          </span>
        )}
      </div>

      {/* Chart */}
      <div className="relative" style={{ height }}>
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10 backdrop-blur-sm rounded-xl">
            <Loader2 className="w-6 h-6 animate-spin text-accent" />
          </div>
        )}
        {error && !isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10 rounded-xl">
            <p className="text-sm text-destructive">Failed to load chart data</p>
          </div>
        )}
        <div ref={chartContainerRef} className="rounded-xl overflow-hidden" />
      </div>
    </div>
  )
}
