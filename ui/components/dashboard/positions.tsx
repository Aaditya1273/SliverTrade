'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import Link from 'next/link'
import { Loader2, X, TrendingUp, TrendingDown, Clock, DollarSign, Wifi, ArrowRight } from 'lucide-react'
import { PLATFORM } from '@/lib/api-config'
import { useAuth } from '@/hooks/useAuth'
import { useState } from 'react'
import { toast } from 'sonner'

interface Position {
  symbol: string
  exchange: string
  product: string
  quantity: string
  average_price: string
  ltp: string
  pnl: string
  pnl_pct?: string
}

export function Positions() {
  const queryClient = useQueryClient()
  const { apiKey } = useAuth()
  const [closeDialogOpen, setCloseDialogOpen] = useState(false)
  const [positionToClose, setPositionToClose] = useState<Position | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['positions', apiKey],
    queryFn: async () => {
      if (!apiKey) return []
      const response = await axios.post(
        PLATFORM('/api/v1/positionbook'),
        { apikey: apiKey },
        { withCredentials: true }
      )
      return response.data.data || response.data.positions || []
    },
    refetchInterval: 5000,
    enabled: !!apiKey,
  })

  const closePositionMutation = useMutation({
    mutationFn: async (position: Position) => {
      const response = await axios.post(
        PLATFORM('/api/v1/closeposition'),
        {
          apikey: apiKey,
          symbol: position.symbol,
          exchange: position.exchange,
          product: position.product,
        },
        { withCredentials: true }
      )
      return response.data
    },
    onSuccess: () => {
      toast.success('Position closed')
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      queryClient.invalidateQueries({ queryKey: ['orderbook'] })
      queryClient.invalidateQueries({ queryKey: ['tradebook'] })
    },
    onError: (error: any) => {
      toast.error(`Failed to close: ${error.response?.data?.message || error.message}`)
    },
  })

  const handleCloseClick = (position: Position) => {
    setPositionToClose(position)
    setCloseDialogOpen(true)
  }

  const confirmClose = () => {
    if (positionToClose) {
      closePositionMutation.mutate(positionToClose)
    }
    setCloseDialogOpen(false)
    setPositionToClose(null)
  }

  const getPnLColor = (pnl: string) => {
    const numPnL = parseFloat(pnl)
    if (numPnL > 0) return 'text-emerald-500'
    if (numPnL < 0) return 'text-rose-500'
    return 'text-foreground'
  }

  const getPnLBg = (pnl: string) => {
    const numPnL = parseFloat(pnl)
    if (numPnL > 0) return 'bg-emerald-500/10'
    if (numPnL < 0) return 'bg-rose-500/10'
    return 'bg-zinc-500/10'
  }

  if (!apiKey) {
    return (
      <Card className="p-6 border-border h-full flex items-center justify-center bg-amber-500/5 border-amber-500/20">
        <div className="text-center max-w-xs">
          <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-amber-500/10 flex items-center justify-center">
            <DollarSign className="w-6 h-6 text-amber-500" />
          </div>
          <p className="text-sm font-medium mb-1">Broker not connected</p>
          <p className="text-xs text-muted-foreground mb-4">Connect a broker to view your open positions and P&L.</p>
          <Link
            href="/setup"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold transition-colors"
          >
            <Wifi className="w-3.5 h-3.5" />
            Connect Broker
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </Card>
    )
  }

  if (isLoading) {
    return (
      <Card className="p-6 border-border h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </Card>
    )
  }

  if (error || !data) {
    return (
      <Card className="p-6 border-border h-full flex items-center justify-center">
        <div className="text-center text-destructive">
          <p className="text-sm">Failed to load positions</p>
        </div>
      </Card>
    )
  }

  const positions = data as Position[]

  return (
    <>
      <Card className="p-6 border-border flex flex-col h-full bg-card/20 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold">Positions</h2>
          <Badge variant="outline" className="text-xs">
            {positions.length} open
          </Badge>
        </div>

        {positions.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <DollarSign className="w-8 h-8 mx-auto mb-2 opacity-20" />
              <p className="text-sm">No open positions</p>
              <p className="text-xs">Execute a signal to open a position</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            <div className="space-y-2">
              {positions.map((position) => {
                const qty = parseFloat(position.quantity)
                const isLong = qty > 0
                const pnl = parseFloat(position.pnl)
                
                return (
                  <div
                    key={`${position.symbol}-${position.exchange}`}
                    className="p-3 rounded-lg border border-border bg-card/30 hover:border-accent/30 hover:bg-card/50 transition-all"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm">{position.symbol}</span>
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                          {position.exchange}
                        </Badge>
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                          {position.product}
                        </Badge>
                        <Badge
                          className={`text-[10px] px-1.5 py-0 border ${
                            isLong
                              ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                              : 'bg-rose-500/10 text-rose-500 border-rose-500/20'
                          }`}
                        >
                          {isLong ? (
                            <TrendingUp className="w-3 h-3 mr-1" />
                          ) : (
                            <TrendingDown className="w-3 h-3 mr-1" />
                          )}
                          {isLong ? 'LONG' : 'SHORT'}
                        </Badge>
                      </div>
                      <Badge className={`text-[10px] px-1.5 py-0 ${getPnLBg(position.pnl)} ${getPnLColor(position.pnl)}`}>
                        {pnl >= 0 ? '+' : ''}{parseFloat(position.pnl).toFixed(2)}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-4 gap-2 text-xs">
                      <div>
                        <div className="text-muted-foreground">Net Qty</div>
                        <div className="font-medium">{position.quantity}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Avg Price</div>
                        <div className="font-medium">₹{parseFloat(position.average_price).toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">LTP</div>
                        <div className="font-medium">₹{parseFloat(position.ltp).toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Day P&L %</div>
                        <div className={`font-medium ${getPnLColor(position.pnl)}`}>
                          {position.pnl_pct ? `${parseFloat(position.pnl_pct).toFixed(2)}%` : '—'}
                        </div>
                      </div>
                    </div>

                    <div className="mt-2">
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-[10px] w-full"
                        onClick={() => handleCloseClick(position)}
                      >
                        <X className="w-3 h-3 mr-1" />
                        Close Position
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </Card>

      <AlertDialog open={closeDialogOpen} onOpenChange={setCloseDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Close Position?</AlertDialogTitle>
            <AlertDialogDescription>
              This will sell {positionToClose?.quantity} {positionToClose?.symbol} at market price. Are you sure?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep Position</AlertDialogCancel>
            <AlertDialogAction onClick={confirmClose}>
              Close Position
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
