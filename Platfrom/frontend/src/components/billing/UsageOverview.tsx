import { useEffect, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  Brain,
  ChartLine,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircuitBoard,
  Clock,
  FileCode,
  Globe,
  Infinity,
  LayoutDashboard,
  LineChart,
  MessagesSquare,
  Shield,
  Signal,
  Sparkles,
  Webhook,
  Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import type { PlanLimits, PlanUsage } from '@/api/billing'
import type { SignalUsageRecord } from '@/api/billing'
import { billingApi } from '@/api/billing'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useSubscriptionStore } from '@/stores/subscriptionStore'

// ── Resource definitions ────────────────────────────────────────────

interface UsageResource {
  /** Key in PlanLimits for the cap. */
  limitKey: keyof PlanLimits
  /** Optional key in PlanUsage for the current count (null = no live count). */
  usageKey?: keyof PlanUsage
  /** Display label. */
  label: string
  /** Short description. */
  description: string
  /** Icon component. */
  icon: React.ComponentType<{ className?: string }>
  /** Whether we have actual usage data (vs just the cap). */
  hasUsage: boolean
  /** Group category. */
  group: 'signals' | 'strategies' | 'advanced'
}

const RESOURCES: UsageResource[] = [
  // ── Signals ──
  {
    limitKey: 'signals_per_month',
    usageKey: 'signals_used_this_month',
    label: 'Monthly Signals',
    description: 'Webhook signals processed per billing month',
    icon: Signal,
    hasUsage: true,
    group: 'signals',
  },
  // ── Strategies (now with real counts from API) ──
  {
    limitKey: 'active_strategies',
    usageKey: 'active_strategies_count',
    label: 'Active Strategies',
    description: 'Concurrent webhook-based trading strategies',
    icon: Webhook,
    hasUsage: true,
    group: 'strategies',
  },
  {
    limitKey: 'python_strategies',
    usageKey: 'python_strategies_count',
    label: 'Python Strategies',
    description: 'Custom Python trading scripts you can run',
    icon: FileCode,
    hasUsage: true,
    group: 'strategies',
  },
  {
    limitKey: 'chartink_strategies',
    usageKey: 'chartink_strategies_count',
    label: 'Chartink Strategies',
    description: 'Strategies powered by Chartink screener alerts',
    icon: ChartLine,
    hasUsage: true,
    group: 'strategies',
  },
  {
    limitKey: 'flow_workflows',
    usageKey: 'flow_workflows_count',
    label: 'Flow Workflows',
    description: 'Visual workflow automation sequences',
    icon: CircuitBoard,
    hasUsage: true,
    group: 'strategies',
  },
  // ── Advanced features ──
  {
    limitKey: 'has_telegram_charts',
    label: 'Telegram Charts',
    description: 'Send charts and analytics to Telegram',
    icon: MessagesSquare,
    hasUsage: false,
    group: 'advanced',
  },
  {
    limitKey: 'has_option_chain',
    label: 'Option Chain',
    description: 'Access option chain data and Greeks',
    icon: LineChart,
    hasUsage: false,
    group: 'advanced',
  },
  {
    limitKey: 'has_python_engine',
    label: 'Python Engine',
    description: 'Run Python trading scripts on our servers',
    icon: Brain,
    hasUsage: false,
    group: 'advanced',
  },
  {
    limitKey: 'has_flow_editor',
    label: 'Flow Editor',
    description: 'Visual drag-and-drop workflow builder',
    icon: LayoutDashboard,
    hasUsage: false,
    group: 'advanced',
  },
  {
    limitKey: 'has_multiple_brokers',
    label: 'Multi-Broker',
    description: 'Connect multiple broker accounts simultaneously',
    icon: Globe,
    hasUsage: false,
    group: 'advanced',
  },
  {
    limitKey: 'has_advanced_analytics',
    label: 'Advanced Analytics',
    description: 'In-depth performance and risk analytics',
    icon: Activity,
    hasUsage: false,
    group: 'advanced',
  },
  {
    limitKey: 'has_dedicated_support',
    label: 'Dedicated Support',
    description: 'Priority support with dedicated account management',
    icon: Shield,
    hasUsage: false,
    group: 'advanced',
  },
]

// ── Component ───────────────────────────────────────────────────────

interface UsageOverviewProps {
  className?: string
}

/** Format a "YYYY-MM" string into "May 2026". */
function formatMonthYear(monthYear: string): string {
  try {
    const [y, m] = monthYear.split('-')
    const d = new Date(Number(y), Number(m) - 1, 1)
    return d.toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
  } catch {
    return monthYear
  }
}

/** Format an ISO timestamp into a relative, human-friendly string. */
function formatResetTime(iso: string): string {
  try {
    const d = new Date(iso)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays < 1) {
      return `today at ${d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}`
    }
    if (diffDays === 1) return 'yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
    return `on ${d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}`
  } catch {
    return iso
  }
}

export function UsageOverview({ className }: UsageOverviewProps) {
  const plan = useSubscriptionStore((s) => s.plan())
  const limits = useSubscriptionStore((s) => s.getLimits())
  const usage = useSubscriptionStore((s) => s.getUsage())
  const isPaid = useSubscriptionStore((s) => s.isPaid())
  const loading = useSubscriptionStore((s) => s.loading)

  // ── Usage history ──
  const [history, setHistory] = useState<SignalUsageRecord[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  useEffect(() => {
    let cancelled = false
    const fetchHistory = async () => {
      setHistoryLoading(true)
      try {
        const resp = await billingApi.getUsageHistory()
        if (!cancelled && resp.status === 'success' && resp.history) {
          setHistory(resp.history)
        }
      } catch {
        // Silently fail — history is non-critical
      } finally {
        if (!cancelled) setHistoryLoading(false)
      }
    }
    fetchHistory()
    return () => { cancelled = true }
  }, [])

  const renderCap = (resource: UsageResource) => {
    const cap = limits[resource.limitKey]

    // Handle boolean feature flags
    if (typeof cap === 'boolean') {
      return cap ? (
        <span className="flex items-center gap-1 text-xs font-medium text-green-600 dark:text-green-400">
          <CheckCircle2 className="h-3 w-3" />
          Enabled
        </span>
      ) : (
        <span className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
          Not available on {plan === 'free' ? 'Free' : 'current'} plan
        </span>
      )
    }

    // Handle null = unlimited
    if (cap === null) {
      return (
        <span className="flex items-center gap-1 text-xs font-medium text-primary">
          <Infinity className="h-3 w-3" />
          Unlimited
        </span>
      )
    }

    // Handle 0 = disabled
    if (cap === 0) {
      return (
        <span className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
          Not available on {plan === 'free' ? 'Free' : 'current'} plan
        </span>
      )
    }

    // Numeric cap — show count/limit with real usage when available
    const used = resource.hasUsage && resource.usageKey
      ? (usage[resource.usageKey] ?? null)
      : null

    return (
      <span className="text-xs font-medium">
        {used !== null ? (
          <>
            {used} / {cap} used
          </>
        ) : (
          <>{cap} available on {plan === 'free' ? 'Free' : 'current'} plan</>
        )}
      </span>
    )
  }

  const renderProgress = (resource: UsageResource) => {
    const cap = limits[resource.limitKey]

    // Only show progress for numeric caps with actual usage data
    if (typeof cap !== 'number' || cap === null || cap <= 0) return null
    if (!resource.hasUsage || !resource.usageKey) return null

    const used = usage[resource.usageKey] ?? 0
    const pct = Math.min(100, Math.round((used / cap) * 100))
    const isNearLimit = pct >= 80 && pct < 100
    const isAtLimit = pct >= 100

    return (
      <div className="mt-1.5 space-y-0.5">
        <Progress
          value={pct}
          className={`h-1.5 ${
            isAtLimit
              ? '[&>div]:bg-red-500'
              : isNearLimit
                ? '[&>div]:bg-amber-500'
                : ''
          }`}
        />
        <div className="flex justify-between text-[10px] text-muted-foreground">
          <span>
            {pct}% used
          </span>
          {isAtLimit && (
            <span className="text-red-500 font-medium flex items-center gap-0.5">
              <AlertTriangle className="h-3 w-3" />
              Limit reached
            </span>
          )}
          {isNearLimit && !isAtLimit && (
            <span className="text-amber-500 font-medium">Nearing limit</span>
          )}
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-lg">Usage This Billing Period</CardTitle>
          <CardDescription>Loading usage data...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const groups: { key: string; label: string; resources: UsageResource[] }[] = [
    {
      key: 'signals',
      label: 'Signals & Processing',
      resources: RESOURCES.filter((r) => r.group === 'signals'),
    },
    {
      key: 'strategies',
      label: 'Strategies & Automation',
      resources: RESOURCES.filter((r) => r.group === 'strategies'),
    },
    {
      key: 'advanced',
      label: 'Advanced Features',
      resources: RESOURCES.filter((r) => r.group === 'advanced'),
    },
  ]

  return (
    <Card className={className}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              Usage This Billing Period
            </CardTitle>
            <CardDescription>
              Your {plan === 'free' ? 'Free' : plan === 'pro' ? 'Pro' : 'Enterprise'} plan limits
              {plan === 'free' && (
                <>
                  {' — '}
                  <Link to="/pricing" className="text-primary font-medium hover:underline">
                    Upgrade for higher limits
                  </Link>
                </>
              )}
            </CardDescription>
          </div>
          <Badge
            variant={isPaid ? 'default' : 'secondary'}
            className={`text-xs gap-1 ${isPaid ? 'bg-green-600 hover:bg-green-700' : ''}`}
          >
            {isPaid ? (
              <Zap className="h-3 w-3" />
            ) : (
              <Sparkles className="h-3 w-3" />
            )}
            {plan === 'free' ? 'Free' : plan === 'pro' ? 'Pro' : 'Enterprise'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {groups.map((group) => (
          <div key={group.key}>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-2">
              {group.label}
            </h4>
            <div className="grid gap-3 sm:grid-cols-2">
              {group.resources.map((resource) => {
                const cap = limits[resource.limitKey]
                const Icon = resource.icon

                // Determine if this feature is available
                const isAvailable =
                  cap === true || cap === null || (typeof cap === 'number' && cap > 0)

                return (
                <Tooltip key={resource.limitKey}>
                  <TooltipTrigger asChild>
                    <div
                      className={`rounded-lg border p-3 transition-colors cursor-default ${
                        isAvailable
                          ? 'bg-card hover:bg-accent/50'
                          : 'bg-muted/30 border-dashed'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <div className="flex items-center gap-2 min-w-0">
                          <Icon
                            className={`h-4 w-4 shrink-0 ${
                              isAvailable ? 'text-primary' : 'text-muted-foreground'
                            }`}
                          />
                          <span
                            className={`text-sm font-medium truncate ${
                              !isAvailable ? 'text-muted-foreground' : ''
                            }`}
                          >
                            {resource.label}
                          </span>
                        </div>
                        {renderCap(resource)}
                      </div>
                      {renderProgress(resource)}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="top" align="start" className="max-w-56">
                    <p className="font-medium mb-1">{resource.label}</p>
                    <p className="text-xs text-muted-foreground">{resource.description}</p>
                  </TooltipContent>
                </Tooltip>
                )
              })}
            </div>
          </div>
        ))}

        {/* Last reset indicator */}
        {usage.last_signal_reset_at && (
          <div className="pt-2 border-t border-border/60">
            <p className="text-[11px] text-muted-foreground">
              Signal counters last reset{' '}
              {formatResetTime(usage.last_signal_reset_at)}
            </p>
          </div>
        )}

        {/* ── Monthly usage history ── */}
        <div className="pt-3 border-t border-border/60">
          <button
            type="button"
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors w-full text-left"
          >
            {showHistory ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
            <Clock className="h-3.5 w-3.5" />
            Monthly Usage History
            {history.length > 0 && !showHistory && (
              <span className="text-muted-foreground/60">
                ({history.length} month{history.length !== 1 ? 's' : ''})
              </span>
            )}
          </button>

          {showHistory && (
            <div className="mt-3">
              {historyLoading ? (
                <p className="text-xs text-muted-foreground">Loading history...</p>
              ) : history.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No archived history yet. Data will appear after the first monthly reset.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border/40 text-muted-foreground">
                        <th className="text-left font-medium pb-1.5 pr-3">Month</th>
                        <th className="text-right font-medium pb-1.5 pr-3">Signals</th>
                        <th className="text-right font-medium pb-1.5 pr-3">Limit</th>
                        <th className="text-right font-medium pb-1.5">%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((rec) => {
                        const pct =
                          rec.signals_limit && rec.signals_limit > 0
                            ? Math.round((rec.signals_used / rec.signals_limit) * 100)
                            : null
                        return (
                          <tr
                            key={rec.month_year}
                            className="border-b border-border/20 hover:bg-accent/30 transition-colors"
                          >
                            <td className="py-1.5 pr-3 font-medium">
                              {formatMonthYear(rec.month_year)}
                              {rec.plan_at_time && rec.plan_at_time !== 'free' && (
                                <Badge
                                  variant="outline"
                                  className="ml-1.5 text-[10px] px-1 py-0 leading-none"
                                >
                                  {rec.plan_at_time}
                                </Badge>
                              )}
                            </td>
                            <td className="py-1.5 pr-3 text-right tabular-nums">
                              {rec.signals_used.toLocaleString()}
                            </td>
                            <td className="py-1.5 pr-3 text-right tabular-nums text-muted-foreground">
                              {rec.signals_limit?.toLocaleString() ?? '∞'}
                            </td>
                            <td className="py-1.5 text-right tabular-nums">
                              {pct !== null ? (
                                <span
                                  className={`${
                                    pct >= 100
                                      ? 'text-red-500 font-medium'
                                      : pct >= 80
                                        ? 'text-amber-500'
                                        : 'text-muted-foreground'
                                  }`}
                                >
                                  {pct}%
                                </span>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
