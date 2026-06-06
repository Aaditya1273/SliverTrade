'use client'

import { useState, useEffect, useCallback } from 'react'

export type ServiceStatus = 'healthy' | 'degraded' | 'down'

interface SystemHealth {
  platform: ServiceStatus
  strategy: ServiceStatus
  lastUpdated: string
}

import { PLATFORM, STRATEGY } from '@/lib/api-config'

// Platform uses /health/* endpoints, not /api/v1/health
const PLATFORM_HEALTH_URL = PLATFORM('/health/status')
const STRATEGY_HEALTH_URL = STRATEGY('/api/v1/health')

async function checkService(url: string, timeoutMs = 5000): Promise<ServiceStatus> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const start = performance.now()
    const response = await fetch(url, {
      method: 'GET',
      signal: controller.signal,
      cache: 'no-store',
    })
    const elapsed = performance.now() - start

    if (!response.ok) return 'down'
    if (elapsed > 2000) return 'degraded'
    return 'healthy'
  } catch {
    return 'down'
  } finally {
    clearTimeout(timeout)
  }
}

export function useSystemHealth() {
  const [health, setHealth] = useState<SystemHealth>({
    platform: 'down',
    strategy: 'down',
    lastUpdated: 'Checking...',
  })

  const check = useCallback(async () => {
    const [platform, strategy] = await Promise.all([
      checkService(PLATFORM_HEALTH_URL),
      checkService(STRATEGY_HEALTH_URL),
    ])

    setHealth({
      platform,
      strategy,
      lastUpdated: new Date().toLocaleTimeString(),
    })
  }, [])

  useEffect(() => {
    check()
    const interval = setInterval(check, 30_000)
    return () => clearInterval(interval)
  }, [check])

  return health
}

export function SystemStatusDot({ status }: { status: ServiceStatus }) {
  const colorMap: Record<ServiceStatus, string> = {
    healthy: 'bg-emerald-500',
    degraded: 'bg-yellow-500',
    down: 'bg-red-500',
  }

  return (
    <div
      className={`w-1.5 h-1.5 rounded-full ${colorMap[status]} animate-pulse`}
    />
  )
}
