'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import Link from 'next/link'
import { Loader2, X, TrendingUp, TrendingDown, Clock, Wifi, ArrowRight } from 'lucide-react'
import { PLATFORM } from '@/lib/api-config'
import { useAuth } from '@/hooks/useAuth'
import { useState } from 'react'
import { toast } from 'sonner'

interface Order {
  orderid: string
  symbol: string
  exchange: string
  action: 'BUY' | 'SELL'
  quantity: string
  price: string
  pricetype: string
  product: string
  order_status: string
  timestamp: string
  source?: string
}

export function Orderbook() {
  const queryClient = useQueryClient()
  const { apiKey } = useAuth()
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false)
  const [orderToCancel, setOrderToCancel] = useState<Order | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['orderbook', apiKey],
    queryFn: async () => {
      if (!apiKey) return []
      const response = await axios.post(
        PLATFORM('/api/v1/orderbook'),
        { apikey: apiKey },
        { withCredentials: true }
      )
      return response.data.data?.orders || response.data.orders || []
    },
    refetchInterval: 5000,
    enabled: !!apiKey,
  })

  const cancelOrderMutation = useMutation({
    mutationFn: async (orderId: string) => {
      const response = await axios.post(
        PLATFORM('/api/v1/cancelorder'),
        { apikey: apiKey, orderid: orderId },
        { withCredentials: true }
      )
      return response.data
    },
    onSuccess: () => {
      toast.success('Order cancelled')
      queryClient.invalidateQueries({ queryKey: ['orderbook'] })
    },
    onError: (error: any) => {
      toast.error(`Failed to cancel: ${error.response?.data?.message || error.message}`)
    },
  })

  const handleCancelClick = (order: Order) => {
    setOrderToCancel(order)
    setCancelDialogOpen(true)
  }

  const confirmCancel = () => {
    if (orderToCancel) {
      cancelOrderMutation.mutate(orderToCancel.orderid)
    }
    setCancelDialogOpen(false)
    setOrderToCancel(null)
  }

  const getStatusColor = (status: string) => {
    switch (status.toUpperCase()) {
      case 'OPEN':
      case 'PENDING':
        return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
      case 'COMPLETE':
      case 'FILLED':
        return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
      case 'REJECTED':
      case 'CANCELLED':
        return 'bg-rose-500/10 text-rose-500 border-rose-500/20'
      default:
        return 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20'
    }
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  }

  if (!apiKey) {
    return (
      <Card className="p-6 border-border h-full flex items-center justify-center bg-amber-500/5 border-amber-500/20">
        <div className="text-center max-w-xs">
          <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-amber-500/10 flex items-center justify-center">
            <Clock className="w-6 h-6 text-amber-500" />
          </div>
          <p className="text-sm font-medium mb-1">Broker not connected</p>
          <p className="text-xs text-muted-foreground mb-4">Connect a broker to view your orders and trade history.</p>
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
          <p className="text-sm">Failed to load orders</p>
        </div>
      </Card>
    )
  }

  const orders = data as Order[]

  return (
    <>
      <Card className="p-6 border-border flex flex-col h-full bg-card/20 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold">Order Book</h2>
          <Badge variant="outline" className="text-xs">
            {orders.length} orders
          </Badge>
        </div>

        {orders.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <Clock className="w-8 h-8 mx-auto mb-2 opacity-20" />
              <p className="text-sm">No orders today</p>
              <p className="text-xs">Place your first trade</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            <div className="space-y-2">
              {orders.map((order) => (
                <div
                  key={order.orderid}
                  className="p-3 rounded-lg border border-border bg-card/30 hover:border-accent/30 hover:bg-card/50 transition-all"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm">{order.symbol}</span>
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                        {order.exchange}
                      </Badge>
                      <Badge
                        className={`text-[10px] px-1.5 py-0 border ${
                          order.action === 'BUY'
                            ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-500 border-rose-500/20'
                        }`}
                      >
                        {order.action === 'BUY' ? (
                          <TrendingUp className="w-3 h-3 mr-1" />
                        ) : (
                          <TrendingDown className="w-3 h-3 mr-1" />
                        )}
                        {order.action}
                      </Badge>
                    </div>
                    <Badge className={`text-[10px] px-1.5 py-0 ${getStatusColor(order.order_status)}`}>
                      {order.order_status}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-4 gap-2 text-xs">
                    <div>
                      <div className="text-muted-foreground">Qty</div>
                      <div className="font-medium">{order.quantity}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Price</div>
                      <div className="font-medium">{order.pricetype === 'MARKET' ? 'MKT' : order.price}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Type</div>
                      <div className="font-medium">{order.pricetype}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Time</div>
                      <div className="font-medium">{formatTime(order.timestamp)}</div>
                    </div>
                  </div>

                  {order.source === 'SilverTrade AI Signal' && (
                    <div className="mt-2 text-[10px] text-accent">
                      AI Signal
                    </div>
                  )}

                  {(order.order_status === 'OPEN' || order.order_status === 'PENDING') && (
                    <div className="mt-2">
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-[10px] w-full"
                        onClick={() => handleCancelClick(order)}
                      >
                        <X className="w-3 h-3 mr-1" />
                        Cancel
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      <AlertDialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel Order?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to cancel the {orderToCancel?.action} order for {orderToCancel?.quantity} {orderToCancel?.symbol}?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep Order</AlertDialogCancel>
            <AlertDialogAction onClick={confirmCancel}>
              Cancel Order
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
