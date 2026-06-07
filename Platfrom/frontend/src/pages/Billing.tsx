import {
  ArrowRight,
  CheckCircle2,
  CreditCard,
  ExternalLink,
  Loader2,
  Shield,
  Sparkles,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { showToast } from '@/utils/toast'
import { PLANS, billingApi, type SubscriptionInfo } from '@/api/billing'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuthStore } from '@/stores/authStore'

export default function BillingPage() {
  const user = useAuthStore((s) => s.user)
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [portalLoading, setPortalLoading] = useState(false)
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null)

  const fetchSubscription = useCallback(async () => {
    try {
      const response = await billingApi.getSubscription()
      if (response.status === 'success' && response.subscription) {
        setSubscription(response.subscription)
      }
    } catch {
      // Billing may not be available; set empty subscription
      setSubscription({ plan: 'free', plan_expires_at: null, stripe_customer_id: null, is_active: false })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSubscription()
  }, [fetchSubscription])

  const handleManageSubscription = async () => {
    setPortalLoading(true)
    try {
      const response = await billingApi.getPortalUrl()
      if (response.status === 'success' && response.portal_url) {
        window.location.href = response.portal_url
      } else {
        showToast.error(response.message || 'Failed to open customer portal')
      }
    } catch {
      showToast.error('Failed to open customer portal')
    } finally {
      setPortalLoading(false)
    }
  }

  const handleUpgrade = async (planId: string, interval: 'month' | 'year') => {
    setCheckoutLoading(`${planId}-${interval}`)
    try {
      const response = await billingApi.createCheckout(planId, interval)
      if (response.status === 'success' && response.checkout_url) {
        window.location.href = response.checkout_url
      } else {
        showToast.error(response.message || 'Failed to create checkout session')
      }
    } catch {
      showToast.error('Failed to create checkout session')
    } finally {
      setCheckoutLoading(null)
    }
  }

  const isPaidPlan = subscription?.plan === 'pro' || subscription?.plan === 'enterprise'
  const currentPlanInfo = PLANS.find((p) => p.id === subscription?.plan)
  const upgradePlans = PLANS.filter(
    (p) => p.id !== 'free' && p.id !== subscription?.plan
  )

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Skeleton className="h-48 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <CreditCard className="h-6 w-6" />
          Billing & Subscription
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage your plan, payment methods, and billing history.
        </p>
      </div>

      {/* Current Plan Card */}
      <Card className={isPaidPlan ? 'border-primary/50' : ''}>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                Current Plan
                {isPaidPlan ? (
                  <Badge variant="default" className="bg-green-600 hover:bg-green-700">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Active
                  </Badge>
                ) : (
                  <Badge variant="secondary">
                    <Sparkles className="h-3 w-3 mr-1" />
                    Free
                  </Badge>
                )}
              </CardTitle>
              <CardDescription className="mt-1">
                {isPaidPlan
                  ? 'Your subscription is active and auto-renewing.'
                  : 'You are on the Free plan. Upgrade to unlock premium features.'}
              </CardDescription>
            </div>
            {currentPlanInfo && (
              <Badge
                variant={isPaidPlan ? 'default' : 'secondary'}
                className="text-base px-4 py-1.5"
              >
                {currentPlanInfo.name}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="bg-muted rounded-lg p-4">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-1">
                Username
              </p>
              <p className="font-medium">{user?.username || '—'}</p>
            </div>
            <div className="bg-muted rounded-lg p-4">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-1">
                Plan Expires
              </p>
              <p className="font-medium">
                {subscription?.plan_expires_at
                  ? new Date(subscription.plan_expires_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })
                  : isPaidPlan
                    ? 'Auto-renewing'
                    : 'Never'}
              </p>
            </div>
          </div>

          {currentPlanInfo && (
            <div className="mt-4">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-2">
                Included features
              </p>
              <div className="grid sm:grid-cols-2 gap-x-6 gap-y-2">
                {currentPlanInfo.features.map((feature) => (
                  <div key={feature} className="flex items-center gap-2 text-sm">
                    <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />
                    <span>{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
        <CardFooter className="border-t pt-6">
          {isPaidPlan ? (
            <Button
              onClick={handleManageSubscription}
              disabled={portalLoading}
              className="w-full sm:w-auto"
            >
              {portalLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Opening portal...
                </>
              ) : (
                <>
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Manage Subscription via Stripe
                </>
              )}
            </Button>
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Shield className="h-4 w-4" />
              <span>Secure payments powered by Stripe</span>
            </div>
          )}
        </CardFooter>
      </Card>

      {/* Upgrade Options (if not enterprise) */}
      {!isPaidPlan && (
        <Card>
          <CardHeader>
            <CardTitle>Upgrade Your Plan</CardTitle>
            <CardDescription>
              Unlock more features and higher limits by upgrading to a paid plan.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid sm:grid-cols-2 gap-4">
              {PLANS.filter((p) => p.id !== 'free').map((plan) => {
                const isLoading = checkoutLoading === `${plan.id}-month`
                return (
                  <Card
                    key={plan.id}
                    className={`border-2 transition-all ${
                      plan.popular
                        ? 'border-primary shadow-sm'
                        : 'hover:border-primary/50'
                    }`}
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg">{plan.name}</CardTitle>
                        {plan.popular && (
                          <Badge variant="secondary" className="bg-primary/10 text-primary border-0">
                            Popular
                          </Badge>
                        )}
                      </div>
                      <CardDescription className="text-xs">
                        {plan.description}
                      </CardDescription>
                      <div className="mt-2">
                        <span className="text-2xl font-bold">{plan.monthlyPrice}</span>
                        <span className="text-muted-foreground text-sm ml-1">/month</span>
                      </div>
                    </CardHeader>
                    <CardContent className="pb-3">
                      <ul className="space-y-1.5">
                        {plan.features.slice(0, 5).map((feature) => (
                          <li key={feature} className="flex items-start gap-2 text-xs">
                            <CheckCircle2 className="h-3 w-3 text-primary mt-0.5 shrink-0" />
                            <span>{feature}</span>
                          </li>
                        ))}
                        {plan.features.length > 5 && (
                          <li className="text-xs text-muted-foreground ml-5">
                            +{plan.features.length - 5} more features
                          </li>
                        )}
                      </ul>
                    </CardContent>
                    <CardFooter>
                      <div className="flex flex-col gap-2 w-full">
                        <Button
                          className="w-full"
                          variant={plan.popular ? 'default' : 'outline'}
                          size="sm"
                          disabled={isLoading}
                          onClick={() => handleUpgrade(plan.id, 'month')}
                        >
                          {isLoading ? (
                            <>
                              <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                              Redirecting...
                            </>
                          ) : (
                            <>
                              <ArrowRight className="h-3 w-3 mr-2" />
                              {plan.cta}
                            </>
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={checkoutLoading === `${plan.id}-year`}
                          onClick={() => handleUpgrade(plan.id, 'year')}
                          className="text-xs text-muted-foreground"
                        >
                          {checkoutLoading === `${plan.id}-year` ? (
                            <>
                              <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                              Redirecting...
                            </>
                          ) : (
                            `Pay $${plan.id === 'pro' ? '299' : '999'}/year (save ~17%)`
                          )}
                        </Button>
                      </div>
                    </CardFooter>
                  </Card>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Upgrade/downgrade options for Pro users */}
      {subscription?.plan === 'pro' && (
        <Card>
          <CardHeader>
            <CardTitle>Need More Power?</CardTitle>
            <CardDescription>
              Upgrade to Enterprise for unlimited signals, multiple brokers, and dedicated support.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid sm:grid-cols-2 gap-4">
              {PLANS.filter((p) => p.id === 'enterprise').map((plan) => {
                const isLoading = checkoutLoading === `${plan.id}-month`
                return (
                  <Card key={plan.id} className="border-2 border-primary/40 hover:border-primary transition-all">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg flex items-center gap-2">
                        {plan.name}
                        <Badge variant="secondary" className="bg-primary/10 text-primary border-0">
                          Upgrade
                        </Badge>
                      </CardTitle>
                      <CardDescription className="text-xs">
                        {plan.description}
                      </CardDescription>
                      <div className="mt-2">
                        <span className="text-2xl font-bold">{plan.monthlyPrice}</span>
                        <span className="text-muted-foreground text-sm ml-1">/month</span>
                      </div>
                    </CardHeader>
                    <CardContent className="pb-3">
                      <ul className="space-y-1.5">
                        {plan.features.slice(0, 5).map((feature) => (
                          <li key={feature} className="flex items-start gap-2 text-xs">
                            <CheckCircle2 className="h-3 w-3 text-primary mt-0.5 shrink-0" />
                            <span>{feature}</span>
                          </li>
                        ))}
                        {plan.features.length > 5 && (
                          <li className="text-xs text-muted-foreground ml-5">
                            +{plan.features.length - 5} more features
                          </li>
                        )}
                      </ul>
                    </CardContent>
                    <CardFooter>
                      <Button
                        className="w-full"
                        size="sm"
                        disabled={isLoading}
                        onClick={() => handleUpgrade(plan.id, 'month')}
                      >
                        {isLoading ? (
                          <>
                            <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                            Redirecting...
                          </>
                        ) : (
                          <>
                            <ArrowRight className="h-3 w-3 mr-2" />
                            Upgrade to Enterprise
                          </>
                        )}
                      </Button>
                    </CardFooter>
                  </Card>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Billing Info */}
      <Card>
        <CardHeader>
          <CardTitle>Billing Information</CardTitle>
          <CardDescription>About your billing and payments.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
            <Shield className="h-5 w-5 text-primary shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Secure Payments</p>
              <p className="text-muted-foreground">
                All payments are processed securely through Stripe. We never store your credit card
                details on our servers.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
            <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">14-Day Money-Back Guarantee</p>
              <p className="text-muted-foreground">
                Not satisfied? Contact us within 14 days of your first payment for a full refund.
              </p>
            </div>
          </div>
        </CardContent>
        <CardFooter className="border-t pt-6 flex flex-col sm:flex-row gap-3">
          <Button variant="outline" size="sm" asChild>
            <Link to="/pricing">
              View pricing details
              <ArrowRight className="h-3 w-3 ml-2" />
            </Link>
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
