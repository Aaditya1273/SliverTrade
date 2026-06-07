import {
  ChevronRight,
  Crown,
  Infinity,
  Sparkles,
  Zap,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { useSubscriptionStore } from '@/stores/subscriptionStore'

/**
 * A compact plan badge for the Navbar that shows the current plan name
 * with color coding and a signal-usage progress indicator on hover/focus.
 */
export function PlanBadge({ className }: { className?: string }) {
  const plan = useSubscriptionStore((s) => s.plan())
  const isPaid = useSubscriptionStore((s) => s.isPaid())
  const usage = useSubscriptionStore((s) => s.getUsage())
  const hasFetched = useSubscriptionStore((s) => s.lastFetched !== null)
  const fetchSubscription = useSubscriptionStore((s) => s.fetchSubscription)
  const [showDetail, setShowDetail] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  // Fetch subscription on first mount if not already cached
  useEffect(() => {
    if (!hasFetched) {
      fetchSubscription()
    }
    // Cleanup hover timer on unmount
    return () => clearTimeout(timerRef.current)
  }, [hasFetched, fetchSubscription])

  const signalsLimit = usage.signals_limit
  const signalsUsed = usage.signals_used_this_month
  const isUnlimited = signalsLimit === null
  const usagePercent = isUnlimited
    ? 0
    : signalsLimit > 0
      ? Math.min(100, Math.round((signalsUsed / signalsLimit) * 100))
      : 0

  const nearingLimit = !isUnlimited && usagePercent > 80

  const planConfig = {
    free: {
      label: 'Free',
      color: 'bg-muted text-muted-foreground hover:bg-muted/80 border-muted-foreground/20',
      icon: Sparkles,
    },
    pro: {
      label: 'Pro',
      color: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 hover:bg-blue-500/20 border-blue-500/30',
      icon: Zap,
    },
    enterprise: {
      label: 'Enterprise',
      color: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 hover:bg-purple-500/20 border-purple-500/30',
      icon: Crown,
    },
  }

  const config = planConfig[plan] || planConfig.free
  const Icon = config.icon

  const handleMouseEnter = () => {
    clearTimeout(timerRef.current)
    setShowDetail(true)
  }

  const handleMouseLeave = () => {
    timerRef.current = setTimeout(() => setShowDetail(false), 300)
  }

  return (
    <div
      className={cn('relative', className)}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <Link
        to="/billing"
        className={cn(
          'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium transition-all hover:opacity-80',
          config.color
        )}
        aria-label={`${config.label} plan — click to manage billing`}
      >
        <Icon className="h-3 w-3" />
        <span className="hidden sm:inline">{config.label}</span>
        <span className="sm:hidden">{config.label}</span>
      </Link>

      {/* Hover detail popover */}
      {showDetail && (
        <div
          className="absolute right-0 top-full mt-2 z-50 w-56 rounded-lg border bg-popover p-3 shadow-lg"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold">{config.label} Plan</span>
            {isPaid && (
              <Badge variant="outline" className="text-[10px] text-green-600 border-green-300 bg-green-50 dark:bg-green-950 dark:text-green-400 dark:border-green-800">
                Active
              </Badge>
            )}
          </div>

          {/* Signal usage */}
          <div className="space-y-1">
            <div className="flex justify-between text-[11px] text-muted-foreground">
              <span>Signals this month</span>
              <span className={nearingLimit ? 'text-amber-600 dark:text-amber-400 font-medium' : ''}>
                {isUnlimited ? (
                  <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                    <Infinity className="h-3 w-3" />
                    Unlimited
                  </span>
                ) : (
                  `${signalsUsed.toLocaleString()} / ${signalsLimit.toLocaleString()}`
                )}
              </span>
            </div>
            {!isUnlimited && (
              <Progress
                value={usagePercent}
                className="h-1.5"
              />
            )}
          </div>

          {/* Remaining count */}
          <div className="mt-2 text-[11px] text-muted-foreground">
            {isUnlimited ? (
              <span className="text-green-600 dark:text-green-400">No signal limit</span>
            ) : (
              <>
                <span className="font-medium">{usage.signals_remaining?.toLocaleString() ?? 0}</span>{' '}
                signals remaining
              </>
            )}
          </div>

          {/* View billing link */}
          <Link
            to="/billing"
            className="mt-2 flex items-center gap-1 text-[11px] text-primary hover:underline"
          >
            Manage plan
            <ChevronRight className="h-3 w-3" />
          </Link>
        </div>
      )}
    </div>
  )
}
