import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Wallet, TrendingUp, TrendingDown, Loader2, Info } from 'lucide-react'
import Link from 'next/link'
import { usePortfolio } from '@/hooks/usePortfolio'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { STRATEGY } from '@/lib/api-config'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

const STRATEGY_BASE = STRATEGY('/api/v1')

interface PortfolioCardProps {
  hideBalances: boolean
  apiKey?: string | null
}

export function PortfolioCard({ hideBalances, apiKey }: PortfolioCardProps) {
  const { funds, totalValue, dayPnL, isLoading, error } = usePortfolio(apiKey ?? null)

  const { data: accuracy } = useQuery({
    queryKey: ['user-accuracy'],
    queryFn: async () => {
      const response = await axios.get(`${STRATEGY_BASE}/user-accuracy`)
      return response.data.data
    },
    refetchInterval: 300000,
  })

  // No broker connected — show connect prompt
  if (!apiKey) {
    return (
      <Card className="p-6 md:p-8 border-border bg-gradient-to-br from-card/80 to-card/40 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-accent/5 rounded-full blur-3xl -z-10" />
        
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-4">
            <Wallet className="w-8 h-8 text-accent" />
          </div>
          <h2 className="text-xl font-semibold mb-2">Connect Your Broker</h2>
          <p className="text-sm text-muted-foreground mb-6 max-w-md">
            Link your broker account to see your portfolio, balances, and trading data in real-time.
          </p>
          <Button asChild>
            <Link href="/setup/wallet">Connect Broker</Link>
          </Button>
        </div>
      </Card>
    )
  }

  // Loading state
  if (isLoading && !funds) {
    return (
      <Card className="p-6 md:p-8 border-border bg-gradient-to-br from-card/80 to-card/40 relative overflow-hidden flex items-center justify-center h-48">
        <Loader2 className="w-6 h-6 animate-spin text-accent" />
      </Card>
    )
  }

  // Error state
  if (error) {
    return (
      <Card className="p-6 md:p-8 border-border bg-gradient-to-br from-card/80 to-card/40 relative overflow-hidden">
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mb-3">
            <TrendingDown className="w-6 h-6 text-destructive" />
          </div>
          <p className="text-sm font-medium text-destructive mb-1">Unable to fetch portfolio</p>
          <p className="text-xs text-muted-foreground">Check your broker connection and try again.</p>
        </div>
      </Card>
    )
  }

  // Connected — show real data
  const pnlPositive = dayPnL >= 0
  const totalDisplay = hideBalances ? '••••••' : `$${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  const availableDisplay = hideBalances ? '••••' : `$${(funds?.available_balance ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  return (
    <Card className="p-6 md:p-8 border-border bg-gradient-to-br from-card/80 to-card/40 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-96 h-96 bg-accent/5 rounded-full blur-3xl -z-10" />
      
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Total Portfolio Value</p>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
              {totalDisplay}
            </h1>
          </div>
          <Badge className={`${pnlPositive ? 'bg-accent/10 text-accent' : 'bg-destructive/10 text-destructive'} border-0`}>
            {pnlPositive ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
            {pnlPositive ? '+' : ''}{dayPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Unrealized
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-border/50">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Available Balance</p>
            <p className="text-lg font-semibold">{availableDisplay}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Used Margin</p>
            <p className="text-lg font-semibold">{hideBalances ? '••••' : `$${(funds?.used_margin ?? 0).toLocaleString()}`}</p>
          </div>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Win Rate</p>
                  <p className="text-lg font-semibold">
                    {accuracy?.trades_evaluated >= 10
                      ? `${(accuracy.win_rate * 100).toFixed(1)}%`
                      : '—'
                    }
                  </p>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>Win rate based on your executed signals</p>
                {accuracy?.trades_evaluated < 10 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Needs {10 - (accuracy.trades_evaluated || 0)} more evaluated trades
                  </p>
                )}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>
    </Card>
  )
}
