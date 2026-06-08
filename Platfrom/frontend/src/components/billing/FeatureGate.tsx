import { Crown, LockKeyhole, Sparkles, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import type { PlanLimits } from '@/api/billing'
import { useSubscriptionStore } from '@/stores/subscriptionStore'

interface FeatureGateProps {
  /** The feature key to check against the current plan. */
  featureKey: keyof PlanLimits
  /** Optional custom fallback to render when the feature is unavailable. */
  fallback?: React.ReactNode
  /** Optional title for the upgrade prompt (default: "Upgrade Required"). */
  title?: string
  /** Optional description for the upgrade prompt. */
  description?: string
  /** Target plan to suggest (defaults to "Pro"). */
  targetPlan?: 'pro' | 'enterprise'
  /** Children to render when the feature is available. */
  children: React.ReactNode
}

const PLAN_ICONS = {
  free: Sparkles,
  pro: Zap,
  enterprise: Crown,
} as const

const PLAN_NAMES = {
  free: 'Free',
  pro: 'Pro',
  enterprise: 'Enterprise',
} as const

/**
 * Renders `children` if the current plan has access to the given feature.
 * Otherwise, renders an upgrade prompt (or a custom fallback).
 */
export function FeatureGate({
  featureKey,
  fallback,
  title = 'Upgrade Required',
  description,
  targetPlan = 'pro',
  children,
}: FeatureGateProps) {
  const hasAccess = useSubscriptionStore((s) => s.hasFeature(featureKey))
  const plan = useSubscriptionStore((s) => s.plan())

  if (hasAccess) return <>{children}</>

  if (fallback) return <>{fallback}</>

  const TargetIcon = PLAN_ICONS[targetPlan]
  const currentPlanName = PLAN_NAMES[plan]

  return (
    <Card className="border-amber-500/30 bg-amber-50/50 dark:bg-amber-950/10">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <LockKeyhole className="h-5 w-5 text-amber-500" />
          {title}
        </CardTitle>
        <CardDescription>
          {description ||
            `This feature is not available on the ${currentPlanName} plan. Upgrade to ${PLAN_NAMES[targetPlan]} to unlock it.`}
        </CardDescription>
      </CardHeader>
      <CardFooter>
        <Button asChild size="sm">
          <Link to={`/pricing?plan=${targetPlan}`}>
            <TargetIcon className="h-4 w-4 mr-2" />
            Upgrade to {PLAN_NAMES[targetPlan]}
          </Link>
        </Button>
      </CardFooter>
    </Card>
  )
}

// ── Named variants for common gating scenarios ─────────────────────────

interface StrategyLimitGateProps {
  /** Number of strategies currently active. */
  currentCount: number
  /** The limit key to check. */
  limitKey: 'active_strategies' | 'python_strategies' | 'chartink_strategies' | 'flow_workflows'
  /** Human-readable label for what's being counted (e.g. "strategies"). */
  itemLabel: string
  children: React.ReactNode
}

/**
 * Gating variant that checks whether the user has room for more items,
 * based on the plan's numeric cap. Shows count + upgrade prompt when at the limit.
 */
export function CountGate({ currentCount, limitKey, itemLabel, children }: StrategyLimitGateProps) {
  const limits = useSubscriptionStore((s) => s.getLimits())
  const maxItems = limits[limitKey]
  const plan = useSubscriptionStore((s) => s.plan())

  // If the limit is null (unlimited) or 0 (disabled), fall through to FeatureGate
  if (maxItems === null) return <>{children}</>

  if (maxItems === 0) {
    return (
      <FeatureGate
        featureKey={limitKey}
        description={`The ${PLAN_NAMES[plan]} plan doesn't support ${itemLabel}. Upgrade to unlock.`}
      />
    )
  }

  if (currentCount >= maxItems) {
    return (
      <FeatureGate
        featureKey={limitKey}
        title={`${itemLabel.charAt(0).toUpperCase() + itemLabel.slice(1)} Limit Reached`}
        description={`You've used all ${maxItems} available ${itemLabel} on the ${PLAN_NAMES[plan]} plan (${currentCount}/${maxItems}). Upgrade to add more.`}
      />
    )
  }

  return <>{children}</>
}
