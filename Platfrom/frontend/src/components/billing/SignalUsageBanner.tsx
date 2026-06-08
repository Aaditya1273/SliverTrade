import { AlertTriangle, BarChart3, Crown, Infinity, Sparkles, TrendingUp, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { useSubscriptionStore } from '@/stores/subscriptionStore'

const PLAN_BADGE = {
  free: { color: 'text-muted-foreground', icon: Sparkles },
  pro: { color: 'text-blue-500', icon: Zap },
  enterprise: { color: 'text-purple-500', icon: Crown },
} as const

interface SignalUsageBannerProps {
  /** Show compact variant (inline, no icon) vs full banner. */
  compact?: boolean
  /** Optional class name for the outer wrapper. */
  className?: string
}

/**
 * Displays current signal usage vs plan limit with a progress bar.
 * Shows upgrade prompt when nearing (80%+) or at (100%) the limit.
 */
export function SignalUsageBanner({ compact, className }: SignalUsageBannerProps) {
  const usage = useSubscriptionStore((s) => s.getUsage())
  const plan = useSubscriptionStore((s) => s.plan())
  const limits = useSubscriptionStore((s) => s.getLimits())
  const isPaid = useSubscriptionStore((s) => s.isPaid())

  const signalsLimit = usage.signals_limit
  const signalsUsed = usage.signals_used_this_month
  const isUnlimited = signalsLimit === null
  const usagePercent = isUnlimited
    ? 0
    : signalsLimit > 0
      ? Math.min(100, Math.round((signalsUsed / signalsLimit) * 100))
      : 0

  const isNearingLimit = !isUnlimited && usagePercent >= 80
  const isAtLimit = !isUnlimited && usagePercent >= 100
  const signalsRemaining = usage.signals_remaining

  if (compact) {
    return (
      <div className={className}>
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground flex items-center gap-1.5">
            <BarChart3 className="h-3.5 w-3.5" />
            Signals this month
          </span>
          <span className={isNearingLimit ? 'text-amber-600 dark:text-amber-400 font-medium' : ''}>
            {isUnlimited ? (
              <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                <Infinity className="h-3.5 w-3.5" />
                Unlimited
              </span>
            ) : (
              `${signalsUsed.toLocaleString()} / ${signalsLimit.toLocaleString()}`
            )}
          </span>
        </div>
        {!isUnlimited && (
          <Progress value={usagePercent} className="h-1.5 mt-1.5" />
        )}
        {isNearingLimit && !isPaid && (
          <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
            <Link to="/pricing" className="underline hover:no-underline font-medium">
              Upgrade your plan
            </Link>{' '}
            for higher limits.
          </p>
        )}
      </div>
    )
  }

  if (isAtLimit && !isPaid) {
    return (
      <div className={`rounded-lg border border-red-300 bg-red-50 p-4 dark:bg-red-950/20 dark:border-red-800 ${className || ''}`}>
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-red-800 dark:text-red-300">
              Signal Limit Reached
            </p>
            <p className="text-xs text-red-600 dark:text-red-400 mt-0.5">
              You&apos;ve used all {signalsLimit?.toLocaleString()} signals this month on the{' '}
              {plan === 'free' ? 'Free' : plan === 'pro' ? 'Pro' : 'Enterprise'} plan.
              No more signals will be processed until the next billing cycle.
            </p>
            <Button asChild size="sm" variant="outline" className="mt-2 border-red-300 text-red-700 hover:bg-red-100 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-950">
              <Link to="/pricing">
                <TrendingUp className="h-4 w-4 mr-1.5" />
                Upgrade for higher limits
              </Link>
            </Button>
          </div>
        </div>
      </div>
    )
  }

  if (isNearingLimit && !isPaid) {
    return (
      <div className={`rounded-lg border border-amber-300 bg-amber-50 p-3 dark:bg-amber-950/20 dark:border-amber-800 ${className || ''}`}>
        <div className="flex items-center gap-3">
          <BarChart3 className="h-5 w-5 text-amber-500 shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-amber-800 dark:text-amber-300">
                Signal usage: {usagePercent}%
              </span>
              <span className="text-amber-600 dark:text-amber-400 text-xs">
                {signalsRemaining?.toLocaleString()} remaining
              </span>
            </div>
            <Progress value={usagePercent} className="h-1.5 mt-1.5" />
            <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
              <Link to="/pricing" className="underline hover:no-underline font-medium">
                Upgrade your plan
              </Link>{' '}
              to increase your monthly signal limit.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return null
}
