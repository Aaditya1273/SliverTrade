'use client'

import { useEffect, useRef } from 'react'
import { createChart, ColorType, AreaSeries, IChartApi, ISeriesApi } from 'lightweight-charts'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Loader2 } from 'lucide-react'
import { DATA } from '@/lib/api-config'

export function PriceChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null)

  const { data: chartData, isLoading } = useQuery({
    queryKey: ['market-data'],
    queryFn: async () => {
      // In production, this would call our data_fetch service on port 5005
      // For this MVP, we'll fetch from the platform's unified market-data endpoint
      // if it existed, or just use our normalized mock data for now.
      const response = await axios.get(DATA('/api/data?symbol=SBIN&exchange=NSE&interval=5m'))
      return response.data.data
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  useEffect(() => {
    if (!chartContainerRef.current) return

    const handleResize = () => {
      chartRef.current?.applyOptions({ width: chartContainerRef.current?.clientWidth })
    }

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
      height: 300,
      timeScale: {
        borderColor: '#1a1a1a',
      },
    })

    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: '#1a9fff',
      topColor: 'rgba(26, 159, 255, 0.3)',
      bottomColor: 'rgba(26, 159, 255, 0.0)',
      lineWidth: 2,
    })

    chartRef.current = chart
    seriesRef.current = areaSeries

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [])

  useEffect(() => {
    if (seriesRef.current && chartData) {
      // Format data for lightweight-charts
      const formattedData = chartData.map((d: any) => ({
        time: d.time,
        value: d.close,
      }))
      seriesRef.current.setData(formattedData)
      chartRef.current?.timeScale().fitContent()
    }
  }, [chartData])

  return (
    <div className="relative w-full h-[300px]">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10 backdrop-blur-sm rounded-xl">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
        </div>
      )}
      <div ref={chartContainerRef} />
    </div>
  )
}
