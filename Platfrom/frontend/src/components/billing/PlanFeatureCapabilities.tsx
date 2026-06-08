import { Check, Crown, Info, LockKeyhole, Sparkles, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useSubscriptionStore } from '@/stores/subscriptionStore'
import type { PlanLimits } from '@/api/billing'

// ── Feature definitions for Python Strategy page ──────────────────────

interface FeatureDef {
  /** Key in PlanLimits to check. */
  key: keyof PlanLimits
  /** Short display label. */
  label: string
  /** Tooltip description. */
  description: string
}

const PYTHON_FEATURES: FeatureDef[] = [
  {
    key: 'has_python_engine',
    label: 'Python Engine',
    description: 'Run custom Python trading scripts with full process isolation',
  },
  {
    key: 'python_strategies',
    label: 'Strategy Uploads',
    description: 'Number of Python strategy scripts you can upload simultaneously',
  },
  {
    key: 'has_multiple_brokers',
    label: 'Multi-Broker',
    description: 'Connect and trade across multiple broker accounts',
  },
  {
    key: 'has_dedicated_support',
    label: 'Dedicated Support',
    description: 'Priority support with dedicated account management',
  },
]

// ── Plan display helpers ──────────────────────────────────────────────

const PLAN_CONFIG = {
  free: {
    label: 'Free',
    icon: Sparkles,
    color: 'text-muted-foreground',
    bg: 'bg-muted',
    border: 'border-muted-foreground/20',
  },
  pro: {
    label: 'Pro',
    icon: Zap,
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-100 dark:bg-blue-950/50',
    border: 'border-blue-500/30',
  },
  enterprise: {
    label: 'Enterprise',
    icon: Crown,
    color: 'text-purple-600 dark:text-purple-400',
    bg: 'bg-purple-100 dark:bg-purple-950/50',
    border: 'border-purple-500/30',
  },
} as const

interface PlanFeatureCapabilitiesProps {
  /** Optional extra className for the wrapper card. */
  className?: string
  /** Optional limit key for counting the resource (default: python_strategies). */
  countKey?: 'python_strategies' | 'active_strategies' | 'chartink_strategies'
  /** Current count of the resource (e.g. number of uploaded strategies). */
  currentCount?: number
}

/**
 * A compact feature-gating indicator card that shows which Python strategy
 * features are available (✓) or locked (🔒) on the current plan.
 *
 * Includes a strategy count progress bar and an upgrade CTA when at capacity.
 */
export function PlanFeatureCapabilities({
  className,
  countKey = 'python_strategies',
  currentCount,
}: PlanFeatureCapabilitiesProps) {
  const plan = useSubscriptionStore((s) => s.plan())
  const hasFeature = useSubscriptionStore((s) => s.hasFeature)
  const limits = useSubscriptionStore((s) => s.getLimits())
  const isPaid = useSubscriptionStore((s) => s.isPaid())

  const cfg = PLAN_CONFIG[plan]
  const PlanIcon = cfg.icon

  const maxItems = limits[countKey]
  const count = currentCount ?? 0

  // Determine if the plan has the python engine at all
  const hasEngine = hasFeature('has_python_engine')

  // Progress percentage for the count limit
  const progressPct =
    maxItems !== null && maxItems > 0 ? Math.min(100, Math.round((count / maxItems) * 100)) : 0
  const isNearLimit = progressPct >= 80
  const isAtLimit = progressPct >= 100

  return (
    <div
      className={`rounded-lg border p-4 space-y-3 ${cfg.border} ${cfg.bg} ${className ?? ''}`}
    >
      {/* Header: plan badge + upgrade CTA */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${cfg.color}`}
          >
            <PlanIcon className="h-3.5 w-3.5" />
            {cfg.label}
          </div>
          {!isPaid && (
            <span className="text-xs text-muted-foreground">
              — {maxItems === 0 ? 'locked' : `${count}/${maxItems ?? '∞'} used`}
            </span>
          )}
        </div>
        {!isPaid && (
          <Button asChild size="sm" variant="outline" className="h-7 text-xs gap-1">
            <Link to="/pricing">
              <Zap className="h-3 w-3" />
              Upgrade
            </Link>
          </Button>
        )}
      </div>

      {/* Feature badges grid */}
      <div className="flex flex-wrap gap-1.5">
        {PYTHON_FEATURES.map((feat) => {
          const available = hasFeature(feat.key)

          // For numeric keys like python_strategies: available if unlimited (null) or has capacity (> 0)
          const isAvailable = feat.key === 'python_strategies' ? maxItems === null || maxItems > 0 : available

          return (
            <Tooltip key={feat.key}>
              <TooltipTrigger asChild>
                <span
                  className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs cursor-default transition-colors ${
                    isAvailable
                      ? 'border-green-500/30 bg-green-50 text-green-700 dark:bg-green-950/20 dark:text-green-400'
                      : 'border-muted-foreground/20 bg-muted/50 text-muted-foreground'
                  }`}
                >
                  {isAvailable ? (
                    <Check className="h-3 w-3" />
                  ) : (
                    <LockKeyhole className="h-3 w-3" />
                  )}
                  {feat.label}
                </span>
              </TooltipTrigger>
              <TooltipContent side="top" align="center" className="max-w-64">
                <p className="font-medium mb-1">{feat.label}</p>
                <p className="text-muted-foreground mb-1">{feat.description}</p>
                {!isAvailable && (
                  <p className="text-amber-600 dark:text-amber-400 font-medium">
                    Available on Pro and above
                  </p>
                )}
              </TooltipContent>
            </Tooltip>
          )
        })}
      </div>

      {/* Progress bar for count-based limits */}
      {maxItems !== null && maxItems > 0 && (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {count} / {maxItems} {countKey.replace('_', ' ')}
            </span>
            {isAtLimit && (
              <span className="text-red-500 font-medium flex items-center gap-1">
                <LockKeyhole className="h-3 w-3" />
                Limit reached
              </span>
            )}
            {isNearLimit && !isAtLimit && (
              <span className="text-amber-500 font-medium">Nearing limit</span>
            )}
          </div>
          <Progress
            value={progressPct}
            className={`h-1.5 ${isAtLimit ? '[&>div]:bg-red-500' : isNearLimit ? '[&>div]:bg-amber-500' : ''}`}
          />
        </div>
      )}

      {/* Bottom upgrade callout for Free users */}

      {!hasEngine && !isPaid && (
        <p className="text-xs text-muted-foreground flex items-start gap-1.5">
          <Info className="h-3.5 w-3.5 mt-0.5 shrink-0 text-amber-500" />
          <span>
            The Free plan has limited Python capabilities.{' '}
            <Link to="/pricing" className="text-primary font-medium hover:underline">
              Upgrade to Pro
            </Link>{' '}
            for the full Python engine with process isolation, scheduling, and more.
          </span>
        </p>
      )}
    </div>
  )
}
