import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Brain, TrendingUp, TrendingDown, Zap } from 'lucide-react'

export function AIFeed() {
  const signals = [
    {
      id: 1,
      symbol: 'BTC',
      signal: 'BUY',
      confidence: 94,
      reason: 'Golden crossover detected with 87% historical accuracy',
      timestamp: '2 min ago',
      price: 67430,
    },
    {
      id: 2,
      symbol: 'ETH',
      signal: 'HOLD',
      confidence: 71,
      reason: 'Consolidation pattern forming',
      timestamp: '8 min ago',
      price: 3850,
    },
    {
      id: 3,
      symbol: 'SOL',
      signal: 'SELL',
      confidence: 88,
      reason: 'Volume divergence with resistance breach',
      timestamp: '15 min ago',
      price: 198,
    },
  ]

  return (
    <Card className="p-6 border-border flex flex-col h-full">
      <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <Brain className="w-5 h-5 text-accent" />
        AI Signals
      </h2>

      <div className="space-y-3 flex-1">
        {signals.map((signal) => (
          <div
            key={signal.id}
            className="p-4 rounded-lg border border-border bg-card/30 hover:border-accent/30 hover:bg-card/50 transition-all group cursor-pointer"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-3">
                <div className="text-lg font-bold text-muted-foreground">{signal.symbol}</div>
                <Badge
                  variant="outline"
                  className={`border-0 text-xs font-bold ${
                    signal.signal === 'BUY'
                      ? 'bg-accent/10 text-accent'
                      : signal.signal === 'SELL'
                        ? 'bg-destructive/10 text-destructive'
                        : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {signal.signal === 'BUY' && <TrendingUp className="w-3 h-3 mr-1" />}
                  {signal.signal === 'SELL' && <TrendingDown className="w-3 h-3 mr-1" />}
                  {signal.signal === 'HOLD' && <Zap className="w-3 h-3 mr-1" />}
                  {signal.signal}
                </Badge>
              </div>
              <span className="text-xs text-muted-foreground">{signal.confidence}%</span>
            </div>

            <p className="text-xs text-muted-foreground mb-3 group-hover:text-foreground transition-colors">
              {signal.reason}
            </p>

            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">${signal.price.toLocaleString()}</span>
              <span className="text-muted-foreground">{signal.timestamp}</span>
            </div>
          </div>
        ))}
      </div>

      <Button variant="outline" className="w-full mt-4 border-border hover:bg-card/50">
        View All Signals
      </Button>
    </Card>
  )
}
