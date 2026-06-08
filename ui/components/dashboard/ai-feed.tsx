'use client'

import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Brain, TrendingUp, TrendingDown, Zap, Loader2, Plus, Check, AlertTriangle, Wifi, Activity } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { toast } from 'sonner'

import { STRATEGY, PLATFORM } from '@/lib/api-config'
import { useAuth } from '@/hooks/useAuth'
import { useSettings, type TradingSettings } from '@/hooks/useSettings'
import { SignalDisclaimer } from '@/components/legal/signal-disclaimer'

const STRATEGY_BASE = STRATEGY('/api/v1')

interface Signal {
  id: string
  symbol: string
  signal?: 'BUY' | 'SELL' | 'HOLD'
  decision?: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  reasoning: string
  timestamp: string
  price: number
  mock_data?: boolean
  exchange?: string
}

export function AIFeed() {
  const queryClient = useQueryClient()
  const { apiKey, authenticated } = useAuth()
  const { data: settings } = useSettings()

  const [executedSignals, setExecutedSignals] = useState<Set<string>>(new Set())
  const [autoExecutingSignals, setAutoExecutingSignals] = useState<Set<string>>(new Set())
  const [seenSignalIds, setSeenSignalIds] = useState<Set<string>>(new Set())
  // Track which signals have been attempted for auto-execute (to avoid retries)
  const autoExecutionAttempted = useRef<Set<string>>(new Set())

  const { data, isLoading, error } = useQuery({
    queryKey: ['signals'],
    queryFn: async () => {
      const response = await axios.get(`${STRATEGY_BASE}/signals`)
      return response.data.signals as Signal[]
    },
    refetchInterval: 5000,
  })

  const generateSignalMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`${STRATEGY_BASE}/signal`, {
        symbol: 'BTC/USDT',
        exchange: 'CRYPTO',
      })
      return response.data.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signals'] })
    },
  })

  const executeTradeMutation = useMutation({
    mutationFn: async (signal: Signal) => {
      if (!apiKey) {
        throw new Error('NO_BROKER: Connect a broker first')
      }

      const response = await axios.post(
        PLATFORM('/api/v1/execute-signal'),
        {
          apikey: apiKey,
          signal_id: signal.id,
          symbol: signal.symbol,
          exchange: signal.exchange ?? 'NSE',
          decision: signal.decision || signal.signal,
          confidence: signal.confidence,
        },
        { withCredentials: true }
      )

      if (response.data.status === 'error' || response.data.status === 'rejected') {
        throw new Error(response.data.message || 'Order failed')
      }

      return response.data
    },
    onSuccess: (data, signal) => {
      const isAuto = autoExecutionAttempted.current.has(signal.id)
      if (!isAuto) {
        toast.success(`Order placed: ${data.orderid || 'Success'}`)
      }
      setExecutedSignals((prev: Set<string>) => new Set(prev).add(signal.id))
      setAutoExecutingSignals((prev: Set<string>) => {
        const next = new Set(prev)
        next.delete(signal.id)
        return next
      })
      queryClient.invalidateQueries({ queryKey: ['orderbook'] })
    },
    onError: (error: Error, signal) => {
      setAutoExecutingSignals((prev: Set<string>) => {
        const next = new Set(prev)
        next.delete(signal.id)
        return next
      })
      // For auto-execute errors, only show a toast if not already shown per batch
      const isAuto = autoExecutionAttempted.current.has(signal.id)
      if (isAuto) {
        // For auto-execute, show concise error without action button
        if (!error.message.startsWith('NO_BROKER')) {
          toast.error(`Auto-execute failed: ${error.message}`, { duration: 4000 })
        }
      } else {
        if (error.message.startsWith('NO_BROKER')) {
          toast.error('Connect a broker first', {
            action: { label: 'Setup', onClick: () => window.location.href = '/setup' }
          })
        } else {
          toast.error(`Order failed: ${error.message}`)
        }
      }
    }
  })

  // ── Auto-execute logic: runs when signals or settings change ──
  useEffect(() => {
    if (!data || !settings || !apiKey || !settings.auto_execute) return

    const signals = data as Signal[]
    const minConfidence = settings.min_signal_confidence

    for (const signal of signals) {
      const decision = signal.decision || signal.signal || 'HOLD'

      // Skip if already executed or already being auto-executed
      if (executedSignals.has(signal.id)) continue
      if (autoExecutingSignals.has(signal.id)) continue
      if (autoExecutionAttempted.current.has(signal.id)) continue

      // Skip if signal doesn't meet criteria
      if (decision === 'HOLD') continue
      if (signal.confidence < minConfidence) continue

      // Mark as attempted immediately (prevent re-triggering on next poll)
      autoExecutionAttempted.current = new Set(autoExecutionAttempted.current).add(signal.id)
      setAutoExecutingSignals((prev: Set<string>) => new Set(prev).add(signal.id))

      // Fire the mutation (no toast for auto-execute)
      executeTradeMutation.mutate(signal)
    }
  }, [data, settings, apiKey, executedSignals, autoExecutingSignals, executeTradeMutation])

  // Track seen signal IDs for the "New" indicator
  useEffect(() => {
    if (data) {
      const ids = new Set(data.map(s => s.id))
      setSeenSignalIds(prev => {
        const merged = new Set(prev)
        ids.forEach(id => merged.add(id))
        return merged
      })
    }
  }, [data])

  const autoExecuteActive = settings?.auto_execute === true && !!apiKey
  const autoExecuteCount = autoExecutingSignals.size

  if (isLoading) {
    return (
      <Card className="p-6 border-border flex items-center justify-center h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="p-6 border-border flex items-center justify-center h-[400px]">
        <div className="text-center">
          <Zap className="w-8 h-8 text-destructive mx-auto mb-3 opacity-50" />
          <p className="text-sm text-destructive">Strategy Engine unreachable</p>
          <p className="text-xs text-muted-foreground mt-1">Ensure Trade Strategies service is running on port 5007</p>
        </div>
      </Card>
    )
  }

  return (
    <Card className="p-6 border-border flex flex-col h-full bg-card/20 backdrop-blur-sm">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Brain className="w-5 h-5 text-accent" />
            AI Signals
          </h2>
          {autoExecuteActive && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge className="bg-rose-500 hover:bg-rose-600 text-white border-0 cursor-default text-[10px] px-2 py-0.5">
                    <Activity className="w-3 h-3 mr-1 animate-pulse" />
                    AUTO
                  </Badge>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <p>Auto-execute mode active — signals above {settings?.min_signal_confidence}% confidence are executed automatically</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
        <div className="flex items-center gap-2">
          {autoExecuteCount > 0 && (
            <div className="flex items-center gap-1 text-[10px] text-rose-400">
              <Loader2 className="w-3 h-3 animate-spin" />
              Executing {autoExecuteCount}...
            </div>
          )}
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => generateSignalMutation.mutate()}
            disabled={generateSignalMutation.isPending}
            className="hover:bg-accent/10 hover:text-accent"
            title="Generate new signal for BTC/USDT"
          >
            {generateSignalMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      <div className="space-y-4 flex-1 overflow-y-auto max-h-[600px] pr-2 custom-scrollbar">
        <AnimatePresence initial={false}>
          {data?.map((signal) => {
            const decision = signal.decision || signal.signal || 'HOLD'
            const isExecuting = executeTradeMutation.isPending && autoExecutingSignals.has(signal.id)
            const isExecuted = executedSignals.has(signal.id)
            const autoExecuted = autoExecutionAttempted.current.has(signal.id) && isExecuted
            const isNew = !seenSignalIds.has(signal.id)

            return (
              <motion.div
                key={signal.id}
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className={`p-4 rounded-xl border transition-all group ${
                  isExecuted && autoExecuted
                    ? 'border-emerald-500/20 bg-emerald-500/5'
                    : 'border-border bg-card/30 hover:border-accent/30 hover:bg-card/50'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="text-lg font-bold tracking-tight text-foreground">{signal.symbol}</div>
                    {isNew && (
                      <Badge variant="outline" className="text-[10px] px-1 py-0 border-accent/50 text-accent">
                        NEW
                      </Badge>
                    )}
                    <Badge
                      variant="outline"
                      className={`border-0 text-[10px] font-black uppercase tracking-widest px-2 py-0.5 ${
                        decision === 'BUY'
                          ? 'bg-emerald-500/10 text-emerald-500'
                          : decision === 'SELL'
                            ? 'bg-rose-500/10 text-rose-500'
                            : 'bg-zinc-500/10 text-zinc-400'
                      }`}
                    >
                      {decision === 'BUY' && <TrendingUp className="w-3 h-3 mr-1" />}
                      {decision === 'SELL' && <TrendingDown className="w-3 h-3 mr-1" />}
                      {decision === 'HOLD' && <Zap className="w-3 h-3 mr-1" />}
                      {decision}
                    </Badge>
                    {autoExecuted && (
                      <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px] px-1.5 py-0">
                        <Check className="w-3 h-3 mr-1" />
                        Auto
                      </Badge>
                    )}
                    {isExecuting && (
                      <Badge className="bg-rose-500/10 text-rose-500 border-rose-500/20 text-[10px] px-1.5 py-0 animate-pulse">
                        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                        Auto-Executing
                      </Badge>
                    )}
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="text-xs font-medium text-accent">{signal.confidence}%</span>
                    <span className="text-[10px] text-muted-foreground uppercase tracking-tighter">Confidence</span>
                  </div>
                </div>

                <p className="text-xs text-muted-foreground mb-4 leading-relaxed line-clamp-2 group-hover:line-clamp-none transition-all">
                  {signal.reasoning}
                </p>

                <div className="flex items-center justify-between mt-auto">
                  <div className="flex flex-col">
                    <span className="text-xs font-semibold">${signal.price?.toLocaleString() ?? '—'}</span>
                    <span className="text-[10px] text-muted-foreground">Market Price</span>
                  </div>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span>
                          {isExecuted ? (
                            <Button 
                              size="sm" 
                              variant="outline"
                              className="h-8 px-4 text-[10px] font-bold uppercase tracking-wider rounded-lg cursor-not-allowed opacity-50"
                              disabled
                            >
                              <Check className="w-3 h-3 mr-1" />
                              Executed
                            </Button>
                          ) : !apiKey ? (
                            <Button 
                              size="sm" 
                              variant="outline"
                              className="h-8 px-4 text-[10px] font-bold uppercase tracking-wider rounded-lg cursor-not-allowed"
                              disabled
                            >
                              Connect Broker
                            </Button>
                          ) : executeTradeMutation.isPending && autoExecutingSignals.has(signal.id) ? (
                            <Button 
                              size="sm" 
                              className="h-8 px-4 text-[10px] font-bold uppercase tracking-wider bg-accent hover:bg-accent/90 text-accent-foreground rounded-lg"
                              disabled
                            >
                              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                              Placing...
                            </Button>
                          ) : decision === 'HOLD' ? (
                            <Button 
                              size="sm" 
                              variant="outline"
                              className="h-8 px-4 text-[10px] font-bold uppercase tracking-wider rounded-lg cursor-not-allowed"
                              disabled
                            >
                              HOLD
                            </Button>
                          ) : (
                            <Button 
                              size="sm" 
                              className={`h-8 px-4 text-[10px] font-bold uppercase tracking-wider rounded-lg ${
                                decision === 'BUY' 
                                  ? 'bg-emerald-500 hover:bg-emerald-600 text-white' 
                                  : 'bg-rose-500 hover:bg-rose-600 text-white'
                              }`}
                              onClick={() => executeTradeMutation.mutate(signal)}
                            >
                              Execute {decision}
                            </Button>
                          )}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>
                        {!apiKey ? 'Connect a broker to execute signals' : decision === 'HOLD' ? 'Cannot execute HOLD signals' : ''}
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                {autoExecuteActive && !isExecuted && decision !== 'HOLD' && signal.confidence >= (settings?.min_signal_confidence ?? 60) && (
                  <div className="mt-2 text-[10px] text-rose-400 flex items-center gap-1">
                    <Activity className="w-3 h-3" />
                    Will auto-execute on next poll
                  </div>
                )}
                {signal.mock_data && (
                  <div className="mt-2 text-[10px] text-yellow-500 uppercase tracking-wider">
                    ⚡ Using simulated data — connect broker for live signals
                  </div>
                )}
              </motion.div>
            )
          })}
        </AnimatePresence>
        
        {(!data || data.length === 0) && (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Zap className="w-8 h-8 mb-3 opacity-20" />
            <p className="text-sm">No signals generated yet.</p>
            <p className="text-xs">Click the + icon to generate a signal for BTC/USDT.</p>
          </div>
        )}
      </div>

      {/* Risk Disclaimer — cannot be hidden or minimized */}
      <SignalDisclaimer />
    </Card>
  )
}
