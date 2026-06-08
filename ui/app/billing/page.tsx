'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CreditCard, Shield, ExternalLink, Loader2, CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react'
import { PLATFORM } from '@/lib/api-config'
import { useAuth } from '@/hooks/useAuth'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import axios from 'axios'
import Link from 'next/link'

interface BillingInfo {
  plan: string
  subscription_status: string
  next_billing_date: string | null
  signals_used: number
  signals_limit: number
  features: Record<string, any>
}

export default function BillingPage() {
  const { authenticated, apiKey } = useAuth()
  const [portalLoading, setPortalLoading] = useState(false)

  // Fetch user info to determine plan
  const { data: billingInfo, isLoading, error } = useQuery<BillingInfo>({
    queryKey: ['billing-info'],
    queryFn: async () => {
      if (!apiKey) throw new Error('Not authenticated')
      const response = await axios.get(PLATFORM('/api/v1/user/info'), {
        params: { apikey: apiKey },
        withCredentials: true,
      })
      const user = response.data.data || response.data
      return {
        plan: user.plan || 'free',
        subscription_status: user.subscription_status || 'inactive',
        next_billing_date: user.subscription_end_date || null,
        signals_used: user.signals_used_this_month || 0,
        signals_limit: user.plan === 'pro' ? -1 : user.plan === 'enterprise' ? -1 : 50,
        features: user.features || {},
      }
    },
    enabled: !!apiKey,
  })

  const handleManageSubscription = async () => {
    setPortalLoading(true)
    try {
      const response = await axios.get(PLATFORM('/billing/portal'), {
        withCredentials: true,
      })
      if (response.data.portal_url) {
        window.location.href = response.data.portal_url
      } else {
        toast.error('Portal unavailable — billing not yet configured')
        setPortalLoading(false)
      }
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Failed to open portal')
      setPortalLoading(false)
    }
  }

  const plan = billingInfo?.plan || 'free'
  const status = billingInfo?.subscription_status || 'inactive'
  const isActive = status === 'active' || status === 'active_trial'

  if (!authenticated) {
    return (
      <main className="min-h-screen bg-background text-foreground">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <Card className="p-12 text-center border-border">
            <CreditCard className="w-12 h-12 text-accent mx-auto mb-4" />
            <h1 className="text-2xl font-bold mb-2">Billing & Subscription</h1>
            <p className="text-muted-foreground mb-6">Sign in to manage your subscription and billing.</p>
            <Link href="/login">
              <Button>Sign In</Button>
            </Link>
          </Card>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-2">
            <CreditCard className="w-6 h-6 text-accent" />
            <h1 className="text-3xl font-bold">Billing</h1>
          </div>
          <p className="text-muted-foreground">Manage your subscription and payment methods.</p>
        </div>

        {/* Loading */}
        {isLoading && (
          <Card className="p-8 border-border">
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-accent" />
            </div>
          </Card>
        )}

        {/* Error */}
        {error && !isLoading && (
          <Card className="p-8 border-border text-center">
            <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-3" />
            <h2 className="font-semibold mb-1">Failed to Load Billing Info</h2>
            <p className="text-sm text-muted-foreground">{error instanceof Error ? error.message : 'Unknown error'}</p>
          </Card>
        )}

        {/* Plan Details */}
        {!isLoading && !error && (
          <>
            <Card className="p-6 border-border mb-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Current Plan</p>
                  <div className="flex items-center gap-2">
                    <h2 className="text-2xl font-bold capitalize">{plan}</h2>
                    <Badge
                      className={isActive
                        ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                      }
                    >
                      {isActive ? 'Active' : status}
                    </Badge>
                  </div>
                </div>
                <Shield className="w-10 h-10 text-accent" />
              </div>

              {/* Plan Limits */}
              <div className="space-y-3 mb-6">
                <div className="flex items-center justify-between py-2 border-b border-border/50">
                  <span className="text-sm text-muted-foreground">Signals per month</span>
                  <span className="text-sm font-medium">
                    {billingInfo?.signals_limit === -1
                      ? 'Unlimited'
                      : `${billingInfo?.signals_used || 0} / ${billingInfo?.signals_limit || 50}`
                    }
                  </span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-border/50">
                  <span className="text-sm text-muted-foreground">Subscription Status</span>
                  <span className="text-sm font-medium capitalize">{status}</span>
                </div>
                {billingInfo?.next_billing_date && (
                  <div className="flex items-center justify-between py-2 border-b border-border/50">
                    <span className="text-sm text-muted-foreground">Next Billing Date</span>
                    <span className="text-sm font-medium">{billingInfo.next_billing_date}</span>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="space-y-3">
                <Button
                  onClick={handleManageSubscription}
                  disabled={portalLoading}
                  className="w-full gap-2"
                >
                  {portalLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <ExternalLink className="w-4 h-4" />
                  )}
                  {isActive ? 'Manage Subscription' : 'Upgrade Plan'}
                </Button>

                {plan === 'free' && (
                  <Link href="/pricing">
                    <Button variant="outline" className="w-full gap-2">
                      View Plans
                      <ArrowRight className="w-4 h-4" />
                    </Button>
                  </Link>
                )}
              </div>
            </Card>

            {/* Invoices */}
            <Card className="p-6 border-border">
              <h3 className="font-semibold mb-4">Invoices</h3>
              <p className="text-sm text-muted-foreground">
                Your invoices and payment history are available in the{' '}
                <button
                  onClick={handleManageSubscription}
                  className="text-accent hover:underline"
                >
                  Stripe Customer Portal
                </button>
                .
              </p>
            </Card>

            {/* Payment Info */}
            <Card className="p-6 border-border mt-6">
              <h3 className="font-semibold mb-2">Payment Information</h3>
              <p className="text-sm text-muted-foreground">
                All payments are processed securely through Stripe. We do not store your payment details.
              </p>
              <div className="flex items-center gap-1 mt-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span className="text-xs text-muted-foreground">256-bit SSL encrypted</span>
              </div>
            </Card>
          </>
        )}
      </div>
    </main>
  )
}
