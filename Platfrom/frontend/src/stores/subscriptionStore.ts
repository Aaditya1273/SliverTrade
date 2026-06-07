import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { billingApi, type PlanLimits, type PlanUsage, type SubscriptionInfo } from '@/api/billing'

export type PlanTier = 'free' | 'pro' | 'enterprise'

interface SubscriptionStore {
  /** Cached subscription info (null = not loaded yet). */
  subscription: SubscriptionInfo | null
  /** True while a fetch is in progress. */
  loading: boolean
  /** Human-readable error message if fetch failed. */
  error: string | null
  /** Timestamp of the last successful fetch (ms). */
  lastFetched: number | null

  /** Fetch subscription from the backend and cache in the store. */
  fetchSubscription: () => Promise<void>
  /** Reset to unloaded state (e.g. on logout). */
  reset: () => void

  // ── Convenience getters (computed at call-time from cached fields) ──────

  /** The current plan tier. */
  plan: () => PlanTier
  /** True if the user has an active paid subscription. */
  isPaid: () => boolean
  /** Remaining signals this month (null = unlimited). */
  signalsRemaining: () => number | null
  /** Whether a specific feature is available on the current plan. */
  hasFeature: (featureKey: keyof PlanLimits) => boolean
  /** The plan limits object (or free defaults if not loaded). */
  getLimits: () => PlanLimits
  /** Usage stats for the current billing period. */
  getUsage: () => PlanUsage
}

const FREE_LIMITS: PlanLimits = {
  signals_per_month: 50,
  active_strategies: 1,
  python_strategies: 0,
  chartink_strategies: 1,
  flow_workflows: 1,
  api_rate_limit: '20 per minute',
  has_telegram_charts: false,
  has_option_chain: false,
  has_python_engine: false,
  has_flow_editor: false,
  has_multiple_brokers: false,
  has_advanced_analytics: false,
  has_dedicated_support: false,
}

const FREE_USAGE: PlanUsage = {
  signals_used_this_month: 0,
  signals_limit: 50,
  signals_remaining: 50,
}

export const useSubscriptionStore = create<SubscriptionStore>()(
  persist(
    (set, get) => ({
      subscription: null,
      loading: false,
      error: null,
      lastFetched: null,

      fetchSubscription: async () => {
        set({ loading: true, error: null })
        try {
          const response = await billingApi.getSubscription()
          if (response.status === 'success' && response.subscription) {
            set({
              subscription: response.subscription,
              loading: false,
              error: null,
              lastFetched: Date.now(),
            })
          } else {
            // Billing unavailable — fall back to free defaults
            set({
              subscription: {
                plan: 'free',
                plan_expires_at: null,
                stripe_customer_id: null,
                is_active: false,
                usage: FREE_USAGE,
                limits: FREE_LIMITS,
              },
              loading: false,
              error: response.message || 'Failed to load subscription',
              lastFetched: Date.now(),
            })
          }
        } catch (err) {
          set({
            subscription: null,
            loading: false,
            error: err instanceof Error ? err.message : 'Network error',
          })
        }
      },

      reset: () => {
        set({ subscription: null, loading: false, error: null, lastFetched: null })
      },

      // ── Convenience getters ────────────────────────────────────────────

      plan: () => get().subscription?.plan ?? 'free',
      isPaid: () => {
        const sub = get().subscription
        if (!sub) return false
        return sub.is_active && (sub.plan === 'pro' || sub.plan === 'enterprise')
      },
      signalsRemaining: () => get().subscription?.usage?.signals_remaining ?? null,
      hasFeature: (featureKey) => {
        const limits = get().subscription?.limits
        if (!limits) return false
        const value = limits[featureKey]
        if (typeof value === 'boolean') return value
        if (value === null) return true // null = unlimited
        if (typeof value === 'number') return value > 0
        return true
      },
      getLimits: () => get().subscription?.limits ?? FREE_LIMITS,
      getUsage: () => get().subscription?.usage ?? FREE_USAGE,
    }),
    {
      name: 'silvertrade-subscription',
      // Only persist the subscription object and lastFetched; re-fetch if stale.
      partialize: (state) => ({
        subscription: state.subscription,
        lastFetched: state.lastFetched,
      }),
    }
  )
)
