'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Brain, TrendingUp, TrendingDown, Zap, Loader2, Plus } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const API_BASE = 'http://127.0.0.1:5000/api/v1/signals'

interface Signal {
  id: string
  symbol: string
  signal: 'BUY' | 'SELL' | 'HOLD'
  decision?: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  reasoning: string
  timestamp: string
  price: number
  urgency: 'HIGH' | 'MEDIUM' | 'LOW'
}

export function AIFeed() {
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['signals'],
    queryFn: async () => {
      const response = await axios.get(API_BASE)
      return response.data.signals as Signal[]
    },
    refetchInterval: 5000,
  })

  const generateMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`${API_BASE}/generate-mock`)
      return response.data.signal
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signals'] })
    },
  })

  const executeTradeMutation = useMutation({
    mutationFn: async (signal: Signal) => {
      const response = await axios.post('http://127.0.0.1:5000/api/v1/execute-signal', {
        symbol: signal.symbol,
        decision: signal.decision || signal.signal,
        confidence: signal.confidence,
        exchange: 'NSE', // Default for this demo
        quantity: '1'
      })
      return response.data
    },
    onSuccess: (data) => {
      // In a real app, we'd show a success toast here
      console.log('Trade executed successfully:', data)
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
      <Card className="p-6 border-border flex items-center justify-center h-[400px] text-destructive">
        Error loading signals. Is the backend running?
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
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="hover:bg-accent/10 hover:text-accent"
        >
          {generateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
        </Button>
      </div>

      <div className="space-y-4 flex-1 overflow-y-auto max-h-[600px] pr-2 custom-scrollbar">
        <AnimatePresence initial={false}>
          {data?.map((signal) => {
            const decision = signal.decision || signal.signal
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
                    <span className="text-xs font-semibold">${signal.price.toLocaleString()}</span>
                    <span className="text-[10px] text-muted-foreground">Market Price</span>
                  </div>
                  <Button 
                    size="sm" 
                    className="h-8 px-4 text-[10px] font-bold uppercase tracking-wider bg-accent hover:bg-accent/90 text-accent-foreground rounded-lg"
                    onClick={() => executeTradeMutation.mutate(signal)}
                    disabled={executeTradeMutation.isPending}
                  >
                    {executeTradeMutation.isPending ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      `Execute ${decision}`
                    )}
                  </Button>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
        
        {(!data || data.length === 0) && (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Zap className="w-8 h-8 mb-3 opacity-20" />
            <p className="text-sm">No signals detected.</p>
            <p className="text-xs">Click the + icon to generate a signal.</p>
          </div>
        )}
      </div>
    </Card>
  )
}
