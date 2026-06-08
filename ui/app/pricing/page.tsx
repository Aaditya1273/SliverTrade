'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Check, X, Sparkles, Loader2, ArrowRight } from 'lucide-react'
import { PLATFORM } from '@/lib/api-config'
import { useAuth } from '@/hooks/useAuth'
import { toast } from 'sonner'
import axios from 'axios'

interface PlanFeature {
  name: string
  free: React.ReactNode
  pro: React.ReactNode
  enterprise: React.ReactNode
}

const PLANS = [
  {
    id: 'free',
    name: 'Free',
    price: '₹0',
    period: '/month',
    description: 'Perfect for getting started with AI-powered trading insights.',
    cta: 'Get Started',
    popular: false,
    gradient: 'from-gray-500/10 to-gray-600/5',
    border: 'border-border',
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '₹999',
    period: '/month',
    description: 'For active traders who need unlimited signals and advanced features.',
    cta: 'Upgrade to Pro',
    popular: true,
    gradient: 'from-accent/10 to-accent/5',
    border: 'border-accent/50',
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: '₹4,999',
    period: '/month',
    description: 'For power traders and institutions requiring full API access.',
    cta: 'Contact Sales',
    popular: false,
    gradient: 'from-purple-500/10 to-purple-600/5',
    border: 'border-purple-500/30',
  },
]

const FEATURES: PlanFeature[] = [
  { name: 'AI Signals per month', free: '50', pro: 'Unlimited', enterprise: 'Unlimited' },
  { name: 'Connected Brokers', free: '1', pro: '3', enterprise: 'Unlimited' },
  { name: 'Chat messages per day', free: '20', pro: 'Unlimited', enterprise: 'Unlimited' },
  { name: 'Signal history', free: '7 days', pro: '90 days', enterprise: '1 year' },
  { name: 'Backtesting', free: 'Basic', pro: 'Advanced', enterprise: 'Full' },
  { name: 'Auto-execute signals', free: <X className="w-4 h-4 text-rose-500" />, pro: <Check className="w-4 h-4 text-emerald-500" />, enterprise: <Check className="w-4 h-4 text-emerald-500" /> },
  { name: 'Missed opportunities', free: '7 days', pro: '90 days', enterprise: '1 year' },
  { name: 'Telegram alerts', free: <X className="w-4 h-4 text-rose-500" />, pro: <Check className="w-4 h-4 text-emerald-500" />, enterprise: <Check className="w-4 h-4 text-emerald-500" /> },
  { name: 'API access', free: <X className="w-4 h-4 text-rose-500" />, pro: <Check className="w-4 h-4 text-emerald-500" />, enterprise: <Check className="w-4 h-4 text-emerald-500" /> },
  { name: 'Priority support', free: 'Community', pro: 'Email', enterprise: 'Dedicated' },
]

export default function PricingPage() {
  const { authenticated } = useAuth()
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null)

  const handleUpgrade = async (planId: string) => {
    if (!authenticated) {
      toast.error('Please sign in to upgrade', {
        action: { label: 'Sign In', onClick: () => window.location.href = '/login' }
      })
      return
    }

    if (planId === 'free') {
      window.location.href = '/dashboard'
      return
    }

    if (planId === 'enterprise') {
      window.location.href = 'mailto:sales@silvertrade.ai'
      return
    }

    setLoadingPlan(planId)
    try {
      const response = await axios.post(
        PLATFORM('/billing/checkout'),
        { plan: planId },
        { withCredentials: true }
      )
      if (response.data.checkout_url) {
        window.location.href = response.data.checkout_url
      } else {
        toast.error('Failed to create checkout session')
      }
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Checkout failed')
    } finally {
      setLoadingPlan(null)
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Sparkles className="w-6 h-6 text-accent" />
            <Badge variant="outline" className="border-accent/30 text-accent">Pricing</Badge>
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold mb-4">
            Simple, Transparent Pricing
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Start free and upgrade as your trading grows. No hidden fees, no long-term contracts.
          </p>
        </div>

        {/* Plan Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          {PLANS.map((plan) => (
            <Card
              key={plan.id}
              className={`relative p-8 border-2 ${plan.border} bg-gradient-to-b ${plan.gradient} ${
                plan.popular ? 'scale-105 md:scale-105' : ''
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge className="bg-accent text-accent-foreground px-4 py-1 text-xs font-bold">
                    Most Popular
                  </Badge>
                </div>
              )}

              <div className="mb-6">
                <h3 className="text-xl font-bold mb-1">{plan.name}</h3>
                <p className="text-sm text-muted-foreground mb-4">{plan.description}</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-bold">{plan.price}</span>
                  <span className="text-muted-foreground">{plan.period}</span>
                </div>
              </div>

              <Button
                onClick={() => handleUpgrade(plan.id)}
                disabled={loadingPlan === plan.id}
                className={`w-full gap-2 ${
                  plan.popular
                    ? 'bg-accent hover:bg-accent/90 text-accent-foreground'
                    : ''
                }`}
                variant={plan.popular ? 'default' : 'outline'}
              >
                {loadingPlan === plan.id ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    {plan.cta}
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </Button>

              {/* Feature Preview */}
              <div className="mt-6 space-y-3">
                {FEATURES.slice(0, 4).map((feature) => (
                  <div key={feature.name} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{feature.name}</span>
                    <span className="font-medium">
                      {plan.id === 'free' ? feature.free : plan.id === 'pro' ? feature.pro : feature.enterprise}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>

        {/* Full Feature Comparison */}
        <Card className="p-8 border-border">
          <h2 className="text-2xl font-bold mb-6 text-center">Full Feature Comparison</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 pr-4 font-medium">Feature</th>
                  <th className="text-center py-3 px-4 font-medium">Free</th>
                  <th className="text-center py-3 px-4 font-medium text-accent">Pro</th>
                  <th className="text-center py-3 px-4 font-medium">Enterprise</th>
                </tr>
              </thead>
              <tbody>
                {FEATURES.map((feature, idx) => (
                  <tr key={feature.name} className={idx < FEATURES.length - 1 ? 'border-b border-border/50' : ''}>
                    <td className="py-3 pr-4 text-sm">{feature.name}</td>
                    <td className="py-3 px-4 text-center text-sm">{feature.free}</td>
                    <td className="py-3 px-4 text-center text-sm font-medium text-accent">{feature.pro}</td>
                    <td className="py-3 px-4 text-center text-sm">{feature.enterprise}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* FAQ */}
        <div className="mt-12 text-center">
          <h2 className="text-2xl font-bold mb-4">Have Questions?</h2>
          <p className="text-muted-foreground mb-6">
            All plans include a 7-day free trial. Cancel anytime.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link href="/legal/terms">
              <Button variant="link" className="text-sm">Terms of Service</Button>
            </Link>
            <Link href="/legal/privacy">
              <Button variant="link" className="text-sm">Privacy Policy</Button>
            </Link>
          </div>
        </div>
      </div>
    </main>
  )
}
