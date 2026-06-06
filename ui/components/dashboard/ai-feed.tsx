'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Brain, TrendingUp, TrendingDown, Zap, Loader2, Plus } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

import { STRATEGY } from '@/lib/api-config'

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
}

export function AIFeed() {
  const queryClient = useQueryClient()

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
    mutationFn: async (_signal: Signal) => {
      // TODO: Wire to Platform API POST /api/v1/placeorder in Phase 4
      throw new Error('Trade execution not yet available. Broker connection and order pipeline coming in Phase 4.')
    },
  })

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
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Brain className="w-5 h-5 text-accent" />
          AI Signals
        </h2>
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

      <div className="space-y-4 flex-1 overflow-y-auto max-h-[600px] pr-2 custom-scrollbar">
        <AnimatePresence initial={false}>
          {data?.map((signal) => {
            const decision = signal.decision || signal.signal || 'HOLD'
            return (
              <motion.div
                key={signal.id}
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="p-4 rounded-xl border border-border bg-card/30 hover:border-accent/30 hover:bg-card/50 transition-all group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="text-lg font-bold tracking-tight text-foreground">{signal.symbol}</div>
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
                          <Button 
                            size="sm" 
                            className="h-8 px-4 text-[10px] font-bold uppercase tracking-wider bg-accent hover:bg-accent/90 text-accent-foreground rounded-lg"
                            onClick={() => executeTradeMutation.mutate(signal)}
                            disabled={true}
                          >
                            Execute {decision}
                          </Button>
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Broker connection and order pipeline coming soon</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
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
    </Card>
  )
}
