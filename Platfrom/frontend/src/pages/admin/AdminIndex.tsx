import {
  Activity,
  ArrowRight,
  Calendar,
  Clock,
  Loader2,
  RefreshCw,
  Settings,
  Shield,
  Snowflake,
  Zap,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminApi } from '@/api/admin'
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
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { showToast } from '@/utils/toast'
import type { AdminStats } from '@/types/admin'

function formatResetTime(isoString: string): string {
  try {
    const d = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

    if (diffHours < 1) return 'Less than an hour ago'
    if (diffHours < 24) return `${diffHours}h ago at ${timeStr}`
    if (diffDays === 1) return `Yesterday at ${timeStr}`
    if (diffDays < 7) return `${diffDays} days ago at ${timeStr}`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
    return d.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' })
  } catch {
    return isoString
  }
}

export default function AdminIndex() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [resetDialogOpen, setResetDialogOpen] = useState(false)
  const [isResetting, setIsResetting] = useState(false)

  const fetchStats = async () => {
    try {
      const data = await adminApi.getStats()
      setStats(data)
    } catch (error) {
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
  }, [])

  const handleReset = async () => {
    setIsResetting(true)
    try {
      const result = await adminApi.triggerSignalReset()
      if (result.status === 'success') {
        showToast.success('Signal counters reset successfully')
      } else {
        showToast.error(result.message || 'Failed to reset signal counters')
        return
      }
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : 'An unexpected error occurred'
      showToast.error(message)
      return
    } finally {
      setIsResetting(false)
      setResetDialogOpen(false)
    }
    // Refresh stats after successful reset (separate from reset error handling)
    fetchStats()
  }

  const adminCards = [
    {
      title: 'Freeze Quantity',
      description: 'Manage F&O freeze quantity limits for order splitting',
      icon: Snowflake,
      href: '/admin/freeze',
      count: stats?.freeze_count,
      countLabel: 'entries',
      color: 'bg-blue-500',
    },
    {
      title: 'Market Holidays',
      description: 'View and manage market holidays for all exchanges',
      icon: Calendar,
      href: '/admin/holidays',
      count: stats?.holiday_count,
      countLabel: 'holidays',
      color: 'bg-green-500',
    },
    {
      title: 'Market Timings',
      description: 'Configure trading session timings for each exchange',
      icon: Clock,
      href: '/admin/timings',
      count: 7,
      countLabel: 'exchanges',
      color: 'bg-purple-500',
    },
    {
      title: 'Security Dashboard',
      description: 'Monitor IP bans, API abuse, and security threats',
      icon: Shield,
      href: '/logs/security',
      countLabel: 'monitoring',
      color: 'bg-red-500',
    },
    {
      title: 'Traffic Dashboard',
      description: 'Monitor HTTP traffic and API request logs',
      icon: Activity,
      href: '/logs/traffic',
      countLabel: 'monitoring',
      color: 'bg-cyan-500',
    },
    {
      title: 'Latency Dashboard',
      description: 'Monitor order execution and API latency',
      icon: Zap,
      href: '/logs/latency',
      countLabel: 'monitoring',
      color: 'bg-orange-500',
    },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="py-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="h-6 w-6" />
          Admin Dashboard
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage system settings, market data, and configurations
        </p>
      </div>

      {/* Admin Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {adminCards.map((card) => (
          <Link key={card.href} to={card.href}>
            <Card className="h-full hover:shadow-lg transition-shadow cursor-pointer group">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div
                    className={`w-10 h-10 rounded-lg ${card.color} flex items-center justify-center`}
                  >
                    <card.icon className="h-5 w-5 text-white" />
                  </div>
                  {card.count !== undefined && (
                    <Badge variant="secondary">
                      {card.count} {card.countLabel}
                    </Badge>
                  )}
                </div>
                <CardTitle className="flex items-center gap-2 group-hover:text-primary transition-colors">
                  {card.title}
                  <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                </CardTitle>
                <CardDescription>{card.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-muted-foreground">
                  Click to manage {card.title.toLowerCase()}
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Signal Reset Section */}
      <Card className="border-amber-200 dark:border-amber-900">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <RefreshCw className="h-5 w-5 text-amber-500" />
                Signal Counter Reset
              </CardTitle>
              <CardDescription>
                Manually trigger the monthly signal counter reset. This archives current usage
                into the history table and zeros out all user signal counters.
              </CardDescription>
            </div>
            <Button
              variant="outline"
              className="border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950"
              onClick={() => setResetDialogOpen(true)}
              disabled={isResetting}
            >
              {isResetting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Resetting…
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Reset Signal Counters
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            This will snapshot each user{"'"}s current signal usage into the monthly history and set
            all <code className="text-xs bg-muted px-1 py-0.5 rounded">signals_used_this_month</code>{' '}
            counters back to <strong>0</strong>. Use this for testing the monthly reset cycle or
            correcting stale counters.
          </p>
          {stats?.last_signal_reset_at && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground border-t border-amber-200 dark:border-amber-800 pt-3">
              <span className="font-medium">Last reset:</span>
              <span>{formatResetTime(stats.last_signal_reset_at)}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Confirmation Dialog */}
      <AlertDialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5 text-amber-500" />
              Reset All Signal Counters?
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-2">
                <p>
                  This will immediately:
                </p>
                <ol className="list-decimal list-inside space-y-1 text-sm">
                  <li>Archive each user{"'"}s current signal usage to the history table</li>
                  <li>Zero out all <code className="text-xs bg-muted px-1 py-0.5 rounded">signals_used_this_month</code> counters</li>
                  <li>Update the <code className="text-xs bg-muted px-1 py-0.5 rounded">last_signal_reset_at</code> timestamp</li>
                </ol>
                <p className="font-medium text-amber-600 dark:text-amber-400">
                  This action cannot be undone. Are you sure?
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isResetting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleReset}
              disabled={isResetting}
              className="bg-amber-500 hover:bg-amber-600 text-white"
            >
              {isResetting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Resetting…
                </>
              ) : (
                'Yes, Reset Counters'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Info Section */}
      <Card>
        <CardHeader>
          <CardTitle>About Admin Settings</CardTitle>
        </CardHeader>
        <CardContent className="prose prose-sm dark:prose-invert max-w-none">
          <p className="text-muted-foreground">
            The admin dashboard provides tools to manage critical system configurations:
          </p>
          <ul className="text-muted-foreground space-y-2 list-disc list-inside">
            <li>
              <strong>Freeze Quantity:</strong> Set maximum order quantities for F&O instruments.
              Orders exceeding these limits will be automatically split.
            </li>
            <li>
              <strong>Market Holidays:</strong> Maintain the holiday calendar for all supported
              exchanges (NSE, BSE, NFO, BFO, MCX, CDS, BCD).
            </li>
            <li>
              <strong>Market Timings:</strong> Configure trading session timings for each exchange,
              including special sessions like Muhurat trading.
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
