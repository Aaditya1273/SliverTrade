import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp } from 'lucide-react'

interface PortfolioCardProps {
  hideBalances: boolean
}

export function PortfolioCard({ hideBalances }: PortfolioCardProps) {
  return (
    <Card className="p-6 md:p-8 border-border bg-gradient-to-br from-card/80 to-card/40 relative overflow-hidden">
      {/* Background accent */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-accent/5 rounded-full blur-3xl -z-10" />
      
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Total Portfolio Value</p>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
              {hideBalances ? '••••••' : '$187,456.89'}
            </h1>
          </div>
          <Badge className="bg-accent/10 text-accent border-0">
            <TrendingUp className="w-4 h-4 mr-1" />
            +18.4% (30d)
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-border/50">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Available Balance</p>
            <p className="text-lg font-semibold">{hideBalances ? '••••' : '$45,230'}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">24h Profit</p>
            <p className="text-lg font-semibold text-accent">+$3,450</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Win Rate</p>
            <p className="text-lg font-semibold">78%</p>
          </div>
        </div>
      </div>
    </Card>
  )
}
