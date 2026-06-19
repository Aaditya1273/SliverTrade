'use client'

import { useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Slider } from '@/components/ui/slider'
import Link from 'next/link'
import { Shield, TrendingUp, TrendingDown, AlertCircle, Loader2, Wifi, WifiOff, ArrowRight } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useLivePrice } from '@/hooks/useLivePrice'
import { useAuth } from '@/hooks/useAuth'
import { PriceChartLive } from '@/components/dashboard/price-chart-live'
import { SymbolSearch, type SymbolResult } from '@/components/dashboard/symbol-search'
import { OrderConfirmDialog } from '@/components/trading/order-confirm-dialog'
import { PLATFORM } from '@/lib/api-config'
import { toast } from 'sonner'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'

function symbolDisplay(symbol: string): string {
  return symbol.split('/')[0]
}

export default function TradePage() {
  const { apiKey, authenticated, loading: authLoading } = useAuth()

  // ── Symbol state ──
  const [selectedSymbol, setSelectedSymbol] = useState('BTC/USDT')
  const [selectedExchange, setSelectedExchange] = useState('CRYPTO')
  const displaySymbol = symbolDisplay(selectedSymbol)

  const { tick, connected } = useLivePrice({
    symbol: selectedSymbol,
    exchange: selectedExchange,
    enabled: true,
  })

  // ── Order form state ──
  const [orderType, setOrderType] = useState<'buy' | 'sell'>('buy')
  const [tradeType, setTradeType] = useState<'market' | 'limit'>('market')
  const [amount, setAmount] = useState('1')
  const [price, setPrice] = useState('')
  const [leverage, setLeverage] = useState([1])
  const [stopLoss, setStopLoss] = useState('')
  const [takeProfit, setTakeProfit] = useState('')
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const queryClient = useQueryClient()

  // ── Execute trade mutation ──
  const executeTradeMutation = useMutation({
    mutationFn: async () => {
      if (!apiKey) throw new Error('NO_BROKER: Connect a broker first')

      const response = await axios.post(
        PLATFORM('/api/v1/execute-signal'),
        {
          apikey: apiKey,
          symbol: selectedSymbol,
          exchange: selectedExchange,
          decision: orderType === 'buy' ? 'BUY' : 'SELL',
          confidence: 90,
          quantity: amount,
          price_type: tradeType === 'limit' ? 'LIMIT' : 'MARKET',
          price: tradeType === 'limit' ? price : undefined,
          stop_loss: stopLoss || undefined,
          take_profit: takeProfit || undefined,
        },
        { withCredentials: true }
      )

      if (response.data.status === 'error' || response.data.status === 'rejected') {
        throw new Error(response.data.message || 'Order failed')
      }

      return response.data
    },
    onSuccess: (data) => {
      toast.success(`Order placed: ${data.orderid || 'Success'}`)
      queryClient.invalidateQueries({ queryKey: ['orderbook'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      setAmount('1')
      setStopLoss('')
      setTakeProfit('')
    },
    onError: (error: Error) => {
      if (error.message.startsWith('NO_BROKER')) {
        toast.error('Connect a broker first', {
          action: { label: 'Setup', onClick: () => window.location.href = '/setup' }
        })
      } else {
        toast.error(`Order failed: ${error.message}`)
      }
    }
  })

  // ── Handlers ──
  const handleSymbolSelect = useCallback((result: SymbolResult) => {
    setSelectedSymbol(result.symbol)
    setSelectedExchange(result.exchange)
    setAmount('1')
    setStopLoss('')
    setTakeProfit('')
  }, [])

  const currentPrice = tick?.ltp ?? null
  const usePrice = tradeType === 'limit' ? parseFloat(price || '0') || currentPrice || 0 : currentPrice || 0
  const totalCost = parseFloat(amount || '0') * usePrice
  const fee = totalCost * 0.001
  const finalCost = totalCost + fee

  const isWalletConnected = !!apiKey
  const brokerConnected = authenticated && isWalletConnected

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold mb-1">Trade {displaySymbol}</h1>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                {currentPrice !== null ? (
                  <>
                    <span className="text-foreground font-semibold">${currentPrice.toLocaleString()}</span>
                    <span className="flex items-center gap-1">
                      {connected ? <Wifi className="w-3 h-3 text-emerald-500" /> : <WifiOff className="w-3 h-3 text-yellow-500" />}
                      {connected ? 'Live' : 'Reconnecting...'}
                    </span>
                    <Badge variant="outline" className="text-[10px] border-border/50">{selectedExchange}</Badge>
                  </>
                ) : (
                  <><Loader2 className="w-4 h-4 animate-spin" /><span>Loading price...</span></>
                )}
              </div>
            </div>
            <div className="w-full sm:w-72">
              <SymbolSearch onSelect={handleSymbolSelect} placeholder="Search symbols..." defaultExchange={selectedExchange} />
            </div>
          </div>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-6">
            <PriceChartLive symbol={selectedSymbol} exchange={selectedExchange} height={360} />

            <Card className="p-6 border-border">
              {/* Buy/Sell Toggle */}
              <div className="grid grid-cols-2 gap-3 mb-6">
                <button
                  onClick={() => setOrderType('buy')}
                  className={`py-3 px-4 rounded-lg font-medium transition-all ${
                    orderType === 'buy'
                      ? 'bg-accent text-accent-foreground'
                      : 'bg-card/50 border border-border text-muted-foreground hover:border-accent/30'
                  }`}
                >
                  <TrendingUp className="w-4 h-4 inline mr-2" /> Buy {displaySymbol}
                </button>
                <button
                  onClick={() => setOrderType('sell')}
                  className={`py-3 px-4 rounded-lg font-medium transition-all ${
                    orderType === 'sell'
                      ? 'bg-destructive text-destructive-foreground'
                      : 'bg-card/50 border border-border text-muted-foreground hover:border-accent/30'
                  }`}
                >
                  <TrendingDown className="w-4 h-4 inline mr-2" /> Sell {displaySymbol}
                </button>
              </div>

              {/* Order Type */}
              <div className="mb-6 p-4 rounded-lg bg-card/30 border border-border">
                <Label className="text-sm font-medium mb-3 block">Order Type</Label>
                <Tabs value={tradeType} onValueChange={(v) => setTradeType(v as 'market' | 'limit')}>
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="market">Market Order</TabsTrigger>
                    <TabsTrigger value="limit">Limit Order</TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>

              {/* Amount */}
              <div className="space-y-2 mb-6">
                <Label className="text-sm font-medium">Amount ({displaySymbol})</Label>
                <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} step="0.01"
                  className="bg-card/50 border-border focus:border-accent/50" />
                <div className="flex gap-2 mt-2">
                  {[0.1, 0.25, 0.5, 1.0].map((val) => (
                    <button key={val} onClick={() => setAmount(val.toString())}
                      className="px-3 py-1 text-xs rounded-lg bg-card/50 border border-border text-muted-foreground hover:border-accent/30 transition-colors">{val}</button>
                  ))}
                </div>
              </div>

              {/* Price Input */}
              {tradeType === 'limit' && (
                <div className="space-y-2 mb-6">
                  <Label className="text-sm font-medium">Limit Price (USD)</Label>
                  <Input type="number" value={price} onChange={(e) => setPrice(e.target.value)}
                    placeholder={currentPrice ? `${currentPrice}` : 'Enter price'}
                    className="bg-card/50 border-border focus:border-accent/50" />
                </div>
              )}

              {/* Leverage */}
              <div className="space-y-2 mb-6">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-medium">Leverage</Label>
                  <Badge variant="outline" className="border-accent text-accent">{leverage[0]}x</Badge>
                </div>
                <Slider min={1} max={10} step={1} value={leverage} onValueChange={setLeverage} />
              </div>

              {/* SL/TP */}
              <div className="grid grid-cols-2 gap-4 mb-6 p-4 rounded-lg bg-card/30 border border-border">
                <div>
                  <Label className="text-sm font-medium block mb-2">Stop Loss</Label>
                  <Input type="number" value={stopLoss} onChange={(e) => setStopLoss(e.target.value)} placeholder="Optional"
                    className="bg-card/50 border-border focus:border-accent/50" />
                </div>
                <div>
                  <Label className="text-sm font-medium block mb-2">Take Profit</Label>
                  <Input type="number" value={takeProfit} onChange={(e) => setTakeProfit(e.target.value)} placeholder="Optional"
                    className="bg-card/50 border-border focus:border-accent/50" />
                </div>
              </div>
            </Card>
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            <Card className="p-6 border-border space-y-4">
              <h3 className="font-semibold text-lg">Order Summary</h3>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Amount</span>
                  <span className="font-medium">{amount || '0'} {displaySymbol}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Price</span>
                  <span className="font-medium">{currentPrice !== null ? `$${usePrice.toLocaleString()}` : '—'}</span>
                </div>
                <div className="border-t border-border pt-3 flex justify-between text-sm">
                  <span className="text-muted-foreground">Subtotal</span>
                  <span className="font-medium">${totalCost.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Trading Fee (0.1%)</span>
                  <span className="font-medium text-destructive">${fee.toLocaleString()}</span>
                </div>
                <div className="border-t border-border pt-3 flex justify-between">
                  <span className="font-medium">Total Cost</span>
                  <span className="font-bold text-lg">${finalCost.toLocaleString()}</span>
                </div>
              </div>

              {/* Connection Status */}
              <div className={`p-4 rounded-lg flex gap-3 ${
                brokerConnected ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-amber-500/10 border border-amber-500/20'
              }`}>
                {brokerConnected ? (
                  <><Wifi className="w-5 h-5 text-emerald-500 flex-shrink-0" /><p className="text-sm text-emerald-500">Broker connected. Ready to trade.</p></>
                ) : (
                  <><AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0" /><p className="text-sm text-amber-500">Connect a broker to enable trading.</p></>
                )}
              </div>

              {/* Execute */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span tabIndex={0}>
                      <Button onClick={() => setConfirmDialogOpen(true)}
                        disabled={executeTradeMutation.isPending || !brokerConnected || currentPrice === null}
                        className="w-full gap-2 py-6 text-base font-semibold">
                        {executeTradeMutation.isPending ? (
                          <><Loader2 className="w-4 h-4 animate-spin" />Executing...</>
                        ) : (
                          <>{orderType === 'buy' ? 'Buy' : 'Sell'} {displaySymbol}<ArrowRight className="w-5 h-5" /></>
                        )}
                      </Button>
                    </span>
                  </TooltipTrigger>
                  {!brokerConnected && <TooltipContent><p>Connect a broker via Setup to enable order execution.</p></TooltipContent>}
                </Tooltip>
              </TooltipProvider>
            </Card>

            {/* Risk Warning */}
            <Card className="p-4 border-destructive/20 bg-destructive/5 border">
              <div className="flex gap-3">
                <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0" />
                <div className="text-sm">
                  <p className="font-medium text-destructive mb-1">High Risk Notice</p>
                  <p className="text-xs text-muted-foreground">Leverage trading can result in rapid losses.</p>
                </div>
              </div>
            </Card>

            {/* Risk Review */}
            <Button variant="outline" className="w-full gap-2" onClick={() => setConfirmDialogOpen(true)}
              disabled={!brokerConnected || currentPrice === null}>
              <Shield className="w-4 h-4" /> Review Risk Details
            </Button>
          </div>
        </div>
      </div>

      <OrderConfirmDialog
        open={confirmDialogOpen}
        onOpenChange={setConfirmDialogOpen}
        orderDetails={{
          action: orderType,
          symbol: selectedSymbol,
          displaySymbol,
          exchange: selectedExchange,
          amount,
          price: currentPrice,
          orderType: tradeType,
          stopLoss,
          takeProfit,
          leverage: leverage[0],
        }}
        onConfirm={() => executeTradeMutation.mutate(undefined, { onSettled: () => setConfirmDialogOpen(false) })}
        isPending={executeTradeMutation.isPending}
      />
    </div>
  )
}
