import { Check, Crown, Infinity, Minus, Sparkles, X, Zap } from 'lucide-react'
import type { PlanLimits } from '@/api/billing'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

// ── Static plan limit data (mirrors the backend PLAN_LIMITS) ──────────

export const PLAN_LIMITS: Record<string, PlanLimits> = {
  free: {
    signals_per_month: 50,
    active_strategies: 1,
    python_strategies: 0,
    chartink_strategies: 1,
    flow_workflows: 1,
    api_rate_limit: '20 per minute',
    has_telegram_charts: true,
    has_option_chain: false,
    has_python_engine: false,
    has_flow_editor: false,
    has_multiple_brokers: false,
    has_advanced_analytics: false,
    has_dedicated_support: false,
  },
  pro: {
    signals_per_month: 10000,
    active_strategies: null,
    python_strategies: 10,
    chartink_strategies: null,
    flow_workflows: 10,
    api_rate_limit: '60 per minute',
    has_telegram_charts: true,
    has_option_chain: true,
    has_python_engine: true,
    has_flow_editor: true,
    has_multiple_brokers: false,
    has_advanced_analytics: true,
    has_dedicated_support: false,
  },
  enterprise: {
    signals_per_month: null,
    active_strategies: null,
    python_strategies: null,
    chartink_strategies: null,
    flow_workflows: null,
    api_rate_limit: '120 per minute',
    has_telegram_charts: true,
    has_option_chain: true,
    has_python_engine: true,
    has_flow_editor: true,
    has_multiple_brokers: true,
    has_advanced_analytics: true,
    has_dedicated_support: true,
  },
}

// ── Feature row definitions ──────────────────────────────────────────

interface ComparisonRow {
  /** Label for the feature. */
  label: string
  /** Short tooltip description. */
  description: string
  /** Function to render the value for a given plan's limits. */
  render: (limits: PlanLimits) => React.ReactNode
}

const ROWS: ComparisonRow[] = [
  {
    label: 'Monthly Signals',
    description: 'Webhook signals processed per billing month',
    render: (l) => renderLimit(l.signals_per_month, 'signals'),
  },
  {
    label: 'Active Strategies',
    description: 'Concurrent webhook-based trading strategies',
    render: (l) => renderLimit(l.active_strategies, 'strategies'),
  },
  {
    label: 'Python Strategies',
    description: 'Custom Python trading scripts you can run',
    render: (l) => renderLimit(l.python_strategies, 'scripts'),
  },
  {
    label: 'Chartink Strategies',
    description: 'Strategies powered by Chartink screener alerts',
    render: (l) => renderLimit(l.chartink_strategies, 'strategies'),
  },
  {
    label: 'Flow Workflows',
    description: 'Visual workflow automation sequences',
    render: (l) => renderLimit(l.flow_workflows, 'workflows'),
  },
  {
    label: 'API Rate Limit',
    description: 'Maximum API requests per minute',
    render: (l) => (
      <span className="text-sm font-medium">{l.api_rate_limit}</span>
    ),
  },
  {
    label: 'Telegram Charts',
    description: 'Send charts and analytics to Telegram',
    render: (l) => renderBool(l.has_telegram_charts),
  },
  {
    label: 'Option Chain & Greeks',
    description: 'Access option chain data and Greeks',
    render: (l) => renderBool(l.has_option_chain),
  },
  {
    label: 'Python Engine',
    description: 'Run custom Python trading scripts on our servers',
    render: (l) => renderBool(l.has_python_engine),
  },
  {
    label: 'Flow Editor',
    description: 'Visual drag-and-drop workflow builder',
    render: (l) => renderBool(l.has_flow_editor),
  },
  {
    label: 'Multi-Broker',
    description: 'Connect multiple broker accounts simultaneously',
    render: (l) => renderBool(l.has_multiple_brokers),
  },
  {
    label: 'Advanced Analytics',
    description: 'In-depth performance and risk analytics',
    render: (l) => renderBool(l.has_advanced_analytics),
  },
  {
    label: 'Dedicated Support',
    description: 'Priority support with dedicated account management',
    render: (l) => renderBool(l.has_dedicated_support),
  },
]

// ── Render helpers ───────────────────────────────────────────────────

function renderLimit(value: number | null, _unit: string): React.ReactNode {
  if (value === null) {
    return (
      <span className="inline-flex items-center gap-1 text-sm font-semibold text-primary">
        <Infinity className="h-3.5 w-3.5" />
        Unlimited
      </span>
    )
  }
  if (value === 0) {
    return (
      <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
        <Minus className="h-3.5 w-3.5" />
        Not available
      </span>
    )
  }
  // Format large numbers with commas
  const formatted = value >= 1000 ? value.toLocaleString() : String(value)
  return <span className="text-sm font-semibold">{formatted}</span>
}

function renderBool(value: boolean): React.ReactNode {
  return value ? (
    <span className="inline-flex items-center gap-1 text-sm font-medium text-green-600 dark:text-green-400">
      <Check className="h-3.5 w-3.5" />
      Yes
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
      <X className="h-3.5 w-3.5" />
      No
    </span>
  )
}

// ── Plan config ──────────────────────────────────────────────────────

const PLAN_CONFIG = [
  {
    id: 'free',
    name: 'Free',
    icon: Sparkles,
    color: 'text-muted-foreground',
    bg: 'bg-muted/30',
    headerBg: 'bg-muted/50',
  },
  {
    id: 'pro',
    name: 'Pro',
    icon: Zap,
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-50/30 dark:bg-blue-950/20',
    headerBg: 'bg-blue-100/50 dark:bg-blue-950/40',
    popular: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    icon: Crown,
    color: 'text-purple-600 dark:text-purple-400',
    bg: 'bg-purple-50/30 dark:bg-purple-950/20',
    headerBg: 'bg-purple-100/50 dark:bg-purple-950/40',
  },
] as const

// ── Component ────────────────────────────────────────────────────────

interface PlanComparisonProps {
  className?: string
}

/**
 * A visual plan comparison grid for the Pricing page.
 * Shows all 3 plans side-by-side with feature indicators.
 * Uses static data (no auth required — public page).
 */
export function PlanComparison({ className }: PlanComparisonProps) {
  return (
    <div className={className}>
      <div className="grid md:grid-cols-3 gap-4">
        {PLAN_CONFIG.map((planCfg) => {
          const limits = PLAN_LIMITS[planCfg.id]
          const PlanIcon = planCfg.icon

          return (
            <div
              key={planCfg.id}
              className={`rounded-xl border overflow-hidden transition-all duration-300 ${
                planCfg.popular
                  ? 'border-primary shadow-lg shadow-primary/10 -mt-2'
                  : 'hover:border-primary/50'
              } ${planCfg.bg}`}
            >
              {/* Plan header */}
              <div className={`px-4 py-3 ${planCfg.headerBg} border-b`}>
                <div className="flex items-center gap-2 mb-1">
                  <PlanIcon className={`h-5 w-5 ${planCfg.color}`} />
                  <h3 className={`text-lg font-bold ${planCfg.color}`}>
                    {planCfg.name}
                  </h3>
                  {planCfg.popular && (
                    <Badge className="ml-auto text-[10px] px-2 py-0 bg-primary">
                      Popular
                    </Badge>
                  )}
                </div>
              </div>

              {/* Feature rows */}
              <div className="divide-y">
                {ROWS.map((row) => {
                  const value = row.render(limits)

                  return (
                    <Tooltip key={row.label}>
                      <TooltipTrigger asChild>
                        <div className="flex items-center justify-between gap-2 px-4 py-2.5 hover:bg-background/50 transition-colors cursor-default min-h-[40px]">
                          <span className="text-xs text-muted-foreground truncate">
                            {row.label}
                          </span>
                          <span className="shrink-0">{value}</span>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="left" align="center" className="max-w-56">
                        <p className="font-medium mb-0.5">{row.label}</p>
                        <p className="text-xs text-muted-foreground">{row.description}</p>
                      </TooltipContent>
                    </Tooltip>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
