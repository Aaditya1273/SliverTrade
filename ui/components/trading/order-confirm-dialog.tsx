'use client'

import { useState, useEffect, useRef } from 'react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Shield,
  Clock,
  Loader2,
  DollarSign,
  Activity,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface OrderConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  orderDetails: {
    action: 'buy' | 'sell'
    symbol: string
    displaySymbol: string
    exchange: string
    amount: string
    price: number | null
    orderType: 'market' | 'limit'
    stopLoss: string
    takeProfit: string
    leverage: number
  }
  onConfirm: () => void
  isPending: boolean
}

interface RiskMetric {
  label: string
  value: string
  severity: 'ok' | 'warn' | 'block'
}

function formatUSD(v: number): string {
  return `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function OrderConfirmDialog({
  open,
  onOpenChange,
  orderDetails,
  onConfirm,
  isPending,
}: OrderConfirmDialogProps) {
  const [confirmEnabled, setConfirmEnabled] = useState(false)
  const [countdown, setCountdown] = useState(2)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Reset state when dialog opens
  useEffect(() => {
    if (!open) {
      setConfirmEnabled(false)
      setCountdown(2)
      if (timerRef.current) clearInterval(timerRef.current)
      return
    }

    // Check for blocking violations
    const hasBlocks = riskMetrics.some(m => m.severity === 'block')
    if (hasBlocks) {
      setConfirmEnabled(false)
      return
    }

    // Check for warnings — require 2-second delay
    const hasWarnings = riskMetrics.some(m => m.severity === 'warn')
    if (hasWarnings) {
      setConfirmEnabled(false)
      setCountdown(2)
      timerRef.current = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            if (timerRef.current) clearInterval(timerRef.current)
            setConfirmEnabled(true)
            return 0
          }
          return prev - 1
        })
      }, 1000)
    } else {
      // No warnings, no blocks — still 2-second delay for safety
      setConfirmEnabled(false)
      setCountdown(2)
      timerRef.current = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            if (timerRef.current) clearInterval(timerRef.current)
            setConfirmEnabled(true)
            return 0
          }
          return prev - 1
        })
      }, 1000)
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [open])

  const { action, symbol, displaySymbol, amount, price, orderType, stopLoss, takeProfit, leverage } = orderDetails
  const isBuy = action === 'buy'
  const currentPrice = price ?? 0
  const totalCost = parseFloat(amount || '0') * currentPrice
  const fee = totalCost * 0.001

  // Risk calculations
  const entryPrice = orderType === 'limit' && price ? price : currentPrice
  const stopPrice = stopLoss ? parseFloat(stopLoss) : entryPrice * (isBuy ? 0.98 : 1.02)
  const takeProfitPrice = takeProfit ? parseFloat(takeProfit) : entryPrice * (isBuy ? 1.05 : 0.95)
  const maxLoss = Math.abs(entryPrice - stopPrice) * parseFloat(amount || '0')
  const maxProfit = Math.abs(takeProfitPrice - entryPrice) * parseFloat(amount || '0')
  const riskRewardRatio = maxProfit / (maxLoss || 1)
  const maxLossPct = entryPrice > 0 ? (maxLoss / (totalCost || 1)) * 100 : 0

  // Risk metrics
  const riskMetrics: RiskMetric[] = [
    {
      label: 'Max Loss',
      value: `${formatUSD(maxLoss)} (${maxLossPct.toFixed(1)}%)`,
      severity: maxLossPct > 5 ? 'warn' : maxLossPct > 10 ? 'block' : 'ok',
    },
    {
      label: 'Risk:Reward',
      value: `1:${riskRewardRatio.toFixed(2)}`,
      severity: riskRewardRatio < 1 ? 'warn' : 'ok',
    },
    {
      label: 'Leverage',
      value: `${leverage}x`,
      severity: leverage > 5 ? 'warn' : leverage > 8 ? 'block' : 'ok',
    },
    {
      label: 'Trading Fee',
      value: formatUSD(fee),
      severity: 'ok',
    },
  ]

  const hasBlocks = riskMetrics.some(m => m.severity === 'block')
  const hasWarnings = riskMetrics.some(m => m.severity === 'warn')
  const warnings = riskMetrics.filter(m => m.severity === 'warn')
  const blocks = riskMetrics.filter(m => m.severity === 'block')

  return (
    <AlertDialog open={open} onOpenChange={(val) => { if (!isPending) onOpenChange(val) }}>
      <AlertDialogContent className="max-w-lg">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-accent" />
            Confirm Order
          </AlertDialogTitle>
          <AlertDialogDescription>
            Review the order details and risk summary before confirming.
          </AlertDialogDescription>
        </AlertDialogHeader>

        {/* Order Summary */}
        <div className="rounded-lg border border-border bg-card/30 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold">{symbol}</span>
              <Badge variant="outline" className="text-[10px]">{orderDetails.exchange}</Badge>
              <Badge className={cn(
                'text-xs border-0',
                isBuy ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'
              )}>
                {isBuy ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingDown className="w-3 h-3 mr-1" />}
                {action.toUpperCase()}
              </Badge>
            </div>
            <span className="text-xs text-muted-foreground uppercase tracking-wider">
              {orderType}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-muted-foreground">Quantity</span>
              <p className="font-medium">{amount} {displaySymbol}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Est. Price</span>
              <p className="font-medium">{currentPrice > 0 ? formatUSD(currentPrice) : '—'}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Subtotal</span>
              <p className="font-medium">{formatUSD(totalCost)}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Total Cost</span>
              <p className="font-medium">{formatUSD(totalCost + fee)}</p>
            </div>
          </div>

          {(stopLoss || takeProfit) && (
            <div className="grid grid-cols-2 gap-3 text-sm pt-3 border-t border-border/50">
              {stopLoss && (
                <div>
                  <span className="text-muted-foreground">Stop Loss</span>
                  <p className="font-medium text-rose-500">{formatUSD(parseFloat(stopLoss))}</p>
                </div>
              )}
              {takeProfit && (
                <div>
                  <span className="text-muted-foreground">Take Profit</span>
                  <p className="font-medium text-emerald-500">{formatUSD(parseFloat(takeProfit))}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Risk Summary */}
        <div className="rounded-lg border border-border bg-card/30 p-4">
          <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-accent" />
            Risk Summary
          </h4>
          <div className="space-y-2">
            {riskMetrics.map((metric) => (
              <div key={metric.label} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  {metric.severity === 'block' && (
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
                  )}
                  {metric.severity === 'warn' && (
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                  )}
                  {metric.severity === 'ok' && (
                    <Shield className="w-3.5 h-3.5 text-emerald-500" />
                  )}
                  <span className="text-muted-foreground">{metric.label}</span>
                </div>
                <span className={cn(
                  'font-medium',
                  metric.severity === 'block' && 'text-rose-500',
                  metric.severity === 'warn' && 'text-amber-500',
                  metric.severity === 'ok' && 'text-emerald-500',
                )}>
                  {metric.value}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Warnings / Blocks */}
        {hasBlocks && (
          <div className="rounded-lg bg-rose-500/10 border border-rose-500/20 p-3 space-y-1">
            {blocks.map((block, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-rose-500">
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <p className="font-medium">{block.label}: {block.value}</p>
              </div>
            ))}
          </div>
        )}

        {hasWarnings && !hasBlocks && (
          <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-3">
            <div className="flex items-start gap-2 text-sm text-amber-500">
              <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium mb-1">Risk Warnings</p>
                <ul className="space-y-0.5">
                  {warnings.map((w, i) => (
                    <li key={i} className="text-xs">{w.label}: {w.value}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* High Risk Notice */}
        <div className="rounded-lg bg-destructive/5 border border-destructive/20 p-3 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-destructive mt-0.5 flex-shrink-0" />
          <p className="text-xs text-muted-foreground">
            Leverage trading involves substantial risk of loss. Only trade with capital you can afford to lose.
            Past performance does not guarantee future results.
          </p>
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault()
              if (confirmEnabled && !isPending) {
                onConfirm()
              }
            }}
            disabled={!confirmEnabled || isPending || hasBlocks}
            className={cn(
              isBuy
                ? 'bg-emerald-500 hover:bg-emerald-600'
                : 'bg-rose-500 hover:bg-rose-600',
              (!confirmEnabled || isPending) && 'opacity-50 cursor-not-allowed'
            )}
          >
            {isPending ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Placing Order...
              </>
            ) : hasBlocks ? (
              'Order Blocked'
            ) : !confirmEnabled ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-3 h-3 animate-spin" />
                Confirm in {countdown}s
              </span>
            ) : (
              <span className="flex items-center gap-2">
                Confirm {action.toUpperCase()}
              </span>
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
