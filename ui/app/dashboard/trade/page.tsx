'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Slider } from '@/components/ui/slider'
import { TrendingUp, TrendingDown, AlertCircle, Loader2, Wifi, WifiOff, ArrowRight } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useLivePrice } from '@/hooks/useLivePrice'
import { useAuth } from '@/hooks/useAuth'

export default function TradePage() {
  const { apiKey, authenticated } = useAuth()
  const { tick, connected } = useLivePrice({ symbol: 'BTC', exchange: 'CRYPTO', enabled: true })

  const [orderType, setOrderType] = useState<'buy' | 'sell'>('buy')
  const [tradeType, setTradeType] = useState<'market' | 'limit'>('market')
  const [amount, setAmount] = useState('1')
  const [price, setPrice] = useState('')
  const [leverage, setLeverage] = useState([1])
  const [stopLoss, setStopLoss] = useState('')
  const [takeProfit, setTakeProfit] = useState('')
  const [executing, setExecuting] = useState(false)

  const currentPrice = tick?.ltp ?? null
  const usePrice = tradeType === 'limit' ? parseFloat(price || '0') || currentPrice || 0 : currentPrice || 0
  const totalCost = parseFloat(amount || '0') * usePrice
  const fee = totalCost * 0.001
  const finalCost = totalCost + fee

  const isWalletConnected = !!apiKey
  const brokerConnected = authenticated && isWalletConnected

  const handleExecuteTrade = async () => {
    if (!brokerConnected) {
      return
    }
    setExecuting(true)
    // Real execution will be wired in Phase 4
    setTimeout(() => {
      setExecuting(false)
    }, 2000)
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Trade Bitcoin</h1>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {currentPrice !== null ? (
              <>
                <span className="text-foreground font-semibold">${currentPrice.toLocaleString()}</span>
                <span className="flex items-center gap-1">
                  {connected ? (
                    <Wifi className="w-3 h-3 text-emerald-500" />
                  ) : (
                    <WifiOff className="w-3 h-3 text-yellow-500" />
                  )}
                  {connected ? 'Live' : 'Reconnecting...'}
                </span>
              </>
            ) : (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Loading price...</span>
              </>
            )}
          </div>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Order Form */}
          <div className="lg:col-span-2 space-y-6">
            {/* Price Display Card */}
            <Card className="p-8 border-border h-80 flex items-center justify-center bg-card/30 relative overflow-hidden">
              {currentPrice !== null ? (
                <div className="text-center z-10">
                  <div className="text-5xl font-bold text-accent mb-2">${currentPrice.toLocaleString()}</div>
                  <div className="flex items-center gap-2 justify-center">
                    <div className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-yellow-500'} animate-pulse`} />
                    <p className="text-muted-foreground text-sm">
                      {connected ? 'Streaming live from exchange' : 'Reconnecting to data feed...'}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center">
                  <Loader2 className="w-8 h-8 animate-spin text-accent mx-auto mb-4" />
                  <p className="text-muted-foreground">Connecting to market data feed...</p>
                </div>
              )}
              {/* Decorative background */}
              <div className="absolute top-0 right-0 w-96 h-96 bg-accent/5 rounded-full blur-3xl" />
            </Card>

            {/* Order Entry Form */}
            <Card className="p-6 border-border">
              {/* Buy/Sell Tabs */}
              <div className="grid grid-cols-2 gap-3 mb-6">
                <button
                  onClick={() => setOrderType('buy')}
                  className={`py-3 px-4 rounded-lg font-medium transition-all ${
                    orderType === 'buy'
                      ? 'bg-accent text-accent-foreground'
                      : 'bg-card/50 border border-border text-muted-foreground hover:border-accent/30'
                  }`}
                >
                  <TrendingUp className="w-4 h-4 inline mr-2" />
                  Buy BTC
                </button>
                <button
                  onClick={() => setOrderType('sell')}
                  className={`py-3 px-4 rounded-lg font-medium transition-all ${
                    orderType === 'sell'
                      ? 'bg-destructive text-destructive-foreground'
                      : 'bg-card/50 border border-border text-muted-foreground hover:border-accent/30'
                  }`}
                >
                  <TrendingDown className="w-4 h-4 inline mr-2" />
                  Sell BTC
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

              {/* Amount Input */}
              <div className="space-y-2 mb-6">
                <Label htmlFor="amount" className="text-sm font-medium">Amount (BTC)</Label>
                <Input
                  id="amount"
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  step="0.01"
                  className="bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                />
                <div className="flex gap-2 mt-2">
                  {[0.1, 0.25, 0.5, 1.0].map((val) => (
                    <button
                      key={val}
                      onClick={() => setAmount(val.toString())}
                      className="px-3 py-1 text-xs rounded-lg bg-card/50 border border-border text-muted-foreground hover:border-accent/30 hover:text-foreground transition-colors"
                    >
                      {val}
                    </button>
                  ))}
                </div>
              </div>

              {/* Price Input (for limit orders) */}
              {tradeType === 'limit' && (
                <div className="space-y-2 mb-6">
                  <Label htmlFor="price" className="text-sm font-medium">Limit Price (USD)</Label>
                  <Input
                    id="price"
                    type="number"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder={currentPrice ? `${currentPrice}` : 'Enter price'}
                    className="bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                  />
                </div>
              )}

              {/* Leverage Slider */}
              <div className="space-y-2 mb-6">
                <div className="flex items-center justify-between">
                  <Label htmlFor="leverage" className="text-sm font-medium">Leverage</Label>
                  <Badge variant="outline" className="border-accent text-accent">{leverage[0]}x</Badge>
                </div>
                <Slider
                  min={1}
                  max={10}
                  step={1}
                  value={leverage}
                  onValueChange={setLeverage}
                  className="cursor-pointer"
                />
              </div>

              {/* Risk Management */}
              <div className="grid grid-cols-2 gap-4 mb-6 p-4 rounded-lg bg-card/30 border border-border">
                <div>
                  <Label htmlFor="stopLoss" className="text-sm font-medium block mb-2">Stop Loss</Label>
                  <Input
                    id="stopLoss"
                    type="number"
                    value={stopLoss}
                    onChange={(e) => setStopLoss(e.target.value)}
                    placeholder="Optional"
                    className="bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                  />
                </div>
                <div>
                  <Label htmlFor="takeProfit" className="text-sm font-medium block mb-2">Take Profit</Label>
                  <Input
                    id="takeProfit"
                    type="number"
                    value={takeProfit}
                    onChange={(e) => setTakeProfit(e.target.value)}
                    placeholder="Optional"
                    className="bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                  />
                </div>
              </div>
            </Card>
          </div>

          {/* Right Column - Order Summary & Execution */}
          <div className="space-y-6">
            {/* Order Summary */}
            <Card className="p-6 border-border space-y-4">
              <h3 className="font-semibold text-lg">Order Summary</h3>

              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Amount</span>
                  <span className="font-medium">{amount || '0'} BTC</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Price</span>
                  <span className="font-medium">
                    {currentPrice !== null ? `$${usePrice.toLocaleString()}` : '—'}
                  </span>
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

              {/* Connector Status */}
              <div className={`p-4 rounded-lg flex gap-3 ${
                brokerConnected
                  ? 'bg-emerald-500/10 border border-emerald-500/20'
                  : 'bg-amber-500/10 border border-amber-500/20'
              }`}>
                {brokerConnected ? (
                  <>
                    <Wifi className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                    <p className="text-sm text-emerald-500">Broker connected. Ready to trade.</p>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0" />
                    <p className="text-sm text-amber-500">
                      {authenticated
                        ? 'Connect a broker to enable trading. Go to Setup.'
                        : 'Sign in and connect a broker to start trading.'}
                    </p>
                  </>
                )}
              </div>

              {/* Execute Button */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span tabIndex={0}>
                      <Button
                        onClick={handleExecuteTrade}
                        disabled={executing || !brokerConnected || currentPrice === null}
                        className="w-full gap-2 py-6 text-base font-semibold"
                      >
                        {executing ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Executing...
                          </>
                        ) : (
                          <>
                            {orderType === 'buy' ? 'Buy' : 'Sell'} BTC
                            <ArrowRight className="w-5 h-5" />
                          </>
                        )}
                      </Button>
                    </span>
                  </TooltipTrigger>
                  {!brokerConnected && (
                    <TooltipContent side="bottom" className="max-w-xs">
                      <p>Connect a broker via Setup to enable order execution. Order placement (Phase 4) bridges signals to your broker.</p>
                    </TooltipContent>
                  )}
                </Tooltip>
              </TooltipProvider>
            </Card>

            {/* Risk Warning */}
            <Card className="p-4 border-border border-destructive/20 bg-destructive/5">
              <div className="flex gap-3">
                <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0" />
                <div className="text-sm">
                  <p className="font-medium text-destructive mb-1">High Risk Notice</p>
                  <p className="text-xs text-muted-foreground">
                    Leverage trading can result in rapid losses. Only trade with capital you can afford to lose.
                  </p>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </main>
  )
}
