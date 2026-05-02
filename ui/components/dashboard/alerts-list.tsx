import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Bell, AlertCircle, CheckCircle2, TrendingUp } from 'lucide-react'

export function AlertsList() {
  const alerts = [
    {
      id: 1,
      type: 'milestone',
      title: 'Profit Target Reached',
      description: 'BTC position hit +15% target',
      timestamp: '5 min ago',
      icon: CheckCircle2,
      color: 'text-accent',
    },
    {
      id: 2,
      type: 'warning',
      title: 'Risk Alert',
      description: 'Portfolio volatility increasing',
      timestamp: '22 min ago',
      icon: AlertCircle,
      color: 'text-destructive',
    },
    {
      id: 3,
      type: 'opportunity',
      title: 'New Opportunity',
      description: 'Low-risk entry point identified',
      timestamp: '1 hour ago',
      icon: TrendingUp,
      color: 'text-accent',
    },
  ]

  return (
    <Card className="p-6 border-border flex flex-col h-full">
      <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <Bell className="w-5 h-5 text-accent" />
        Alerts
      </h2>

      <div className="space-y-3 flex-1">
        {alerts.map((alert) => {
          const Icon = alert.icon
          return (
            <div
              key={alert.id}
              className="p-4 rounded-lg border border-border bg-card/30 hover:border-accent/30 hover:bg-card/50 transition-all"
            >
              <div className="flex items-start gap-3">
                <Icon className={`w-5 h-5 flex-shrink-0 ${alert.color} mt-0.5`} />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm">{alert.title}</p>
                  <p className="text-xs text-muted-foreground mt-1">{alert.description}</p>
                  <p className="text-xs text-muted-foreground mt-2">{alert.timestamp}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <Button variant="outline" className="w-full mt-4 border-border hover:bg-card/50">
        View All Alerts
      </Button>
    </Card>
  )
}
