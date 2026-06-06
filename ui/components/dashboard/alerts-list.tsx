'use client'

import Link from 'next/link'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Bell, AlertCircle, CheckCircle2, TrendingUp, Wifi, ArrowRight } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'

export function AlertsList() {
  const { apiKey, authenticated, loading: authLoading } = useAuth()
  const needsBroker = authenticated && !apiKey && !authLoading

  if (needsBroker) {
    return (
      <Card className="p-6 border-border h-full flex items-center justify-center bg-amber-500/5 border-amber-500/20">
        <div className="text-center max-w-xs">
          <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-amber-500/10 flex items-center justify-center">
            <Bell className="w-6 h-6 text-amber-500" />
          </div>
          <p className="text-sm font-medium mb-1">Broker not connected</p>
          <p className="text-xs text-muted-foreground mb-4">Connect a broker to receive real-time trading alerts and notifications.</p>
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
