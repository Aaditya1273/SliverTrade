import { webClient } from './client'

export interface PlanUsage {
  signals_used_this_month: number
  signals_limit: number | null
  signals_remaining: number | null
  /** ISO timestamp of the last monthly signal reset, or null if never reset. */
  last_signal_reset_at?: string | null
  /** Current number of webhook strategies owned by the user. */
  active_strategies_count?: number
  /** Current number of Python strategy scripts uploaded. */
  python_strategies_count?: number
  /** Current number of Chartink strategies configured. */
  chartink_strategies_count?: number
  /** Current number of Flow workflows. */
  flow_workflows_count?: number
}

export interface PlanLimits {
  signals_per_month: number | null
  active_strategies: number | null
  python_strategies: number | null
  chartink_strategies: number | null
  flow_workflows: number | null
  api_rate_limit: string
  has_telegram_charts: boolean
  has_option_chain: boolean
  has_python_engine: boolean
  has_flow_editor: boolean
  has_multiple_brokers: boolean
  has_advanced_analytics: boolean
  has_dedicated_support: boolean
}

export interface SubscriptionInfo {
  plan: 'free' | 'pro' | 'enterprise'
  plan_expires_at: string | null
  stripe_customer_id: string | null
  is_active: boolean
  usage: PlanUsage
  limits: PlanLimits
}

export interface SubscriptionResponse {
  status: 'success' | 'error'
  subscription?: SubscriptionInfo
  message?: string
}

export interface CheckoutResponse {
  status: 'success' | 'error'
  checkout_url?: string
  message?: string
}

export interface PortalResponse {
  status: 'success' | 'error'
  portal_url?: string
  message?: string
}

export interface SignalUsageRecord {
  month_year: string
  signals_used: number
  signals_limit: number | null
  plan_at_time: string | null
  recorded_at: string | null
}

export interface UsageHistoryResponse {
  status: 'success' | 'error'
  history?: SignalUsageRecord[]
  message?: string
}

export const billingApi = {
  /**
   * Get the current user's subscription status.
   */
  getSubscription: async (): Promise<SubscriptionResponse> => {
    const response = await webClient.get<SubscriptionResponse>('/billing/subscription')
    return response.data
  },

  /**
   * Create a Stripe checkout session for the given plan and interval.
   */
  createCheckout: async (
    plan: string,
    interval: 'month' | 'year' = 'month'
  ): Promise<CheckoutResponse> => {
    const response = await webClient.post<CheckoutResponse>('/billing/checkout', {
      plan,
      interval,
    })
    return response.data
  },

  /**
   * Get a Stripe Customer Portal URL for managing subscriptions.
   */
  getPortalUrl: async (): Promise<PortalResponse> => {
    const response = await webClient.get<PortalResponse>('/billing/portal')
    return response.data
  },

  /**
   * Get archived monthly signal usage history.
   */
  getUsageHistory: async (): Promise<UsageHistoryResponse> => {
    const response = await webClient.get<UsageHistoryResponse>('/billing/usage-history')
    return response.data
  },
}

/** Plan display information. */
export interface PlanInfo {
  id: 'free' | 'pro' | 'enterprise'
  name: string
  description: string
  monthlyPrice: string
  yearlyPrice: string
  monthlyPriceId: string
  yearlyPriceId: string
  features: string[]
  highlighted?: boolean
  popular?: boolean
  cta: string
}

export const PLANS: PlanInfo[] = [
  {
    id: 'free',
    name: 'Free',
    description: 'Get started with basic algo trading capabilities',
    monthlyPrice: '₹0',
    yearlyPrice: '₹0',
    monthlyPriceId: '',
    yearlyPriceId: '',
    features: [
      'Up to 50 signals per month',
      '1 active strategy',
      'Basic webhook support',
      'Telegram notifications',
      'Standard support',
    ],
    cta: 'Get Started',
  },
  {
    id: 'pro',
    name: 'Pro',
    description: 'For active algo traders who need more power',
    monthlyPrice: '$29.99',
    yearlyPrice: '$299',
    monthlyPriceId: 'price_1TfZ26KioKWjvo1ExkUR6YTw',
    yearlyPriceId: 'price_1TfZ27KioKWjvo1EX0rMkicH',
    features: [
      'Up to 10,000 signals per month',
      'Unlimited strategies',
      'Advanced webhook support',
      'Telegram notifications & charts',
      'Option chain & Greeks',
      'Python strategy engine',
      'Flow workflow editor',
      'Priority support',
    ],
    popular: true,
    cta: 'Subscribe to Pro',
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    description: 'For power traders and institutional setups',
    monthlyPrice: '$99.99',
    yearlyPrice: '$999',
    monthlyPriceId: 'price_1TfZ27KioKWjvo1EJT3LQZx5',
    yearlyPriceId: 'price_1TfZ28KioKWjvo1EnptgXP6L',
    features: [
      'Unlimited signals',
      'Everything in Pro',
      'Multiple broker connections',
      'Advanced sandbox & analyzer',
      'Custom webhook endpoints',
      'Dedicated support',
      'SLA guarantee',
      'Early access to new features',
    ],
    highlighted: true,
    cta: 'Subscribe to Enterprise',
  },
]
