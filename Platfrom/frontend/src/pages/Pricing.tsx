import {
  ArrowRight,
  Check,
  CreditCard,
  ExternalLink,
  HelpCircle,
  Loader2,
  LogIn,
  Shield,
  Star,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { showToast } from '@/utils/toast'
import { billingApi, PLANS } from '@/api/billing'
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
import { Switch } from '@/components/ui/switch'
import { useAuthStore } from '@/stores/authStore'

export default function PricingPage() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const [yearly, setYearly] = useState(false)
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null)

  const handleSubscribe = async (planId: string, interval: 'month' | 'year') => {
    if (planId === 'free') {
      navigate(isAuthenticated ? '/dashboard' : '/login')
      return
    }

    if (!isAuthenticated) {
      navigate('/login')
      return
    }

    setLoadingPlan(`${planId}-${interval}`)
    try {
      const response = await billingApi.createCheckout(planId, interval)
      if (response.status === 'success' && response.checkout_url) {
        window.location.href = response.checkout_url
      } else {
        showToast.error(response.message || 'Failed to create checkout session')
      }
    } catch (error) {
      showToast.error('Failed to create checkout session. Please try again.')
    } finally {
      setLoadingPlan(null)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Simple Nav */}
      <header className="sticky top-0 z-30 h-16 w-full border-b bg-background/90 backdrop-blur">
        <nav className="container mx-auto px-4 flex h-full items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <img src="/logo.png" alt="SilverTrade AI" className="h-8 w-8" />
            <span className="text-xl font-bold hidden sm:inline">SilverTrade AI</span>
          </Link>
          <div className="flex items-center gap-2">
            {isAuthenticated ? (
              <Button variant="ghost" size="sm" onClick={() => navigate('/dashboard')}>
                Dashboard
              </Button>
            ) : (
              <Button variant="ghost" size="sm" onClick={() => navigate('/login')}>
                <LogIn className="h-4 w-4 mr-2" />
                Login
              </Button>
            )}
          </div>
        </nav>
      </header>

      {/* Hero */}
      <section className="container mx-auto px-4 py-16 text-center">
        <Badge variant="outline" className="mb-4 px-4 py-1.5 text-sm">
          <Star className="h-3.5 w-3.5 mr-1.5 text-yellow-500 fill-yellow-500" />
          Simple, transparent pricing
        </Badge>
        <h1 className="text-4xl md:text-5xl font-bold mb-4">
          Choose the plan that fits <br />
          <span className="text-primary">your trading needs</span>
        </h1>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
          Start free, upgrade as you grow. All plans include our core algo trading platform with
          webhook integrations and Telegram alerts.
        </p>

        {/* Billing Toggle */}
        <div className="flex items-center justify-center gap-3 mb-12">
          <span className={`text-sm font-medium ${!yearly ? 'text-foreground' : 'text-muted-foreground'}`}>
            Monthly
          </span>
          <Switch checked={yearly} onCheckedChange={setYearly} />
          <span className={`text-sm font-medium ${yearly ? 'text-foreground' : 'text-muted-foreground'}`}>
            Yearly
          </span>
          {yearly && (
            <Badge variant="secondary" className="bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 border-0">
              Save up to 17%
            </Badge>
          )}
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="container mx-auto px-4 pb-20">
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto items-start">
          {PLANS.map((plan) => {
            const price = yearly && plan.id !== 'free' ? plan.yearlyPrice : plan.monthlyPrice
            const interval = yearly ? 'year' : 'month'
            const isLoading = loadingPlan === `${plan.id}-${interval}`

            return (
              <Card
                key={plan.id}
                className={`relative flex flex-col transition-all duration-300 ${
                  plan.popular
                    ? 'border-primary shadow-lg shadow-primary/10 scale-105 z-10'
                    : plan.highlighted
                      ? 'border-2 border-primary/40 shadow-md'
                      : 'hover:border-primary/50'
                }`}
              >
                {/* Popular Badge */}
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-primary text-primary-foreground px-4 py-1 text-xs font-semibold shadow-md">
                      <Star className="h-3 w-3 mr-1 fill-current" />
                      Most Popular
                    </Badge>
                  </div>
                )}

                <CardHeader>
                  <CardTitle className="text-xl">{plan.name}</CardTitle>
                  <CardDescription className="text-sm min-h-[2.5rem]">
                    {plan.description}
                  </CardDescription>
                  <div className="mt-4">
                    <span className="text-4xl font-bold">{price}</span>
                    {plan.id !== 'free' && (
                      <span className="text-muted-foreground ml-1">
                        /{yearly ? 'year' : 'month'}
                      </span>
                    )}
                  </div>
                  {yearly && plan.id !== 'free' && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {plan.monthlyPrice}/month billed annually
                    </p>
                  )}
                </CardHeader>

                <CardContent className="flex-1">
                  <ul className="space-y-3">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2 text-sm">
                        <Check className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>

                <CardFooter className="flex-col gap-3">
                  <Button
                    className="w-full"
                    variant={plan.popular ? 'default' : plan.highlighted ? 'default' : 'outline'}
                    size="lg"
                    disabled={isLoading}
                    onClick={() => handleSubscribe(plan.id, interval)}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Redirecting to checkout...
                      </>
                    ) : (
                      <>
                        {plan.cta}
                        {plan.id !== 'free' && <ExternalLink className="h-4 w-4 ml-2" />}
                      </>
                    )}
                  </Button>
                  {plan.id !== 'free' && (
                    <p className="text-xs text-muted-foreground text-center flex items-center gap-1">
                      <Shield className="h-3 w-3" />
                      Secure checkout powered by Stripe
                    </p>
                  )}
                </CardFooter>
              </Card>
            )
          })}
        </div>
      </section>

      {/* Comparison Table */}
      <section className="border-t bg-muted/30">
        <div className="container mx-auto px-4 py-16">
          <h2 className="text-2xl font-bold text-center mb-2">Compare plans in detail</h2>
          <p className="text-muted-foreground text-center mb-10 max-w-xl mx-auto">
            Everything you need to automate your algo trading, from basic webhooks to advanced
            strategy engines.
          </p>

          <div className="max-w-3xl mx-auto overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 pr-4 font-medium">Feature</th>
                  <th className="text-center py-3 px-4 font-medium">Free</th>
                  <th className="text-center py-3 px-4 font-medium text-primary">Pro</th>
                  <th className="text-center py-3 px-4 font-medium">Enterprise</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {[
                  ['Signals per month', '50', '10,000', 'Unlimited'],
                  ['Active strategies', '1', 'Unlimited', 'Unlimited'],
                  ['Webhook support', 'Basic', 'Advanced', 'Custom endpoints'],
                  ['Telegram notifications', '✓', '✓ + Charts', '✓ + Charts'],
                  ['Option chain & Greeks', '—', '✓', '✓'],
                  ['Python strategy engine', '—', '✓', '✓'],
                  ['Flow workflow editor', '—', '✓', '✓'],
                  ['Multiple brokers', '—', '—', '✓'],
                  ['Sandbox & analyzer', 'Basic', 'Basic', 'Advanced'],
                  ['Priority support', '—', '✓', 'Dedicated'],
                  ['SLA guarantee', '—', '—', '✓'],
                ].map(([feature, free, pro, enterprise]) => (
                  <tr key={feature} className="hover:bg-muted/50 transition-colors">
                    <td className="py-3 pr-4 font-medium">{feature}</td>
                    <td className="text-center py-3 px-4 text-muted-foreground">{free}</td>
                    <td className="text-center py-3 px-4">{pro}</td>
                    <td className="text-center py-3 px-4">{enterprise}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="container mx-auto px-4 py-16">
        <h2 className="text-2xl font-bold text-center mb-2">Frequently asked questions</h2>
        <p className="text-muted-foreground text-center mb-10 max-w-xl mx-auto">
          Everything you need to know about our billing and plans.
        </p>
        <div className="max-w-2xl mx-auto space-y-6">
          {[
            {
              q: 'Can I switch plans at any time?',
              a: 'Yes. You can upgrade or downgrade your plan at any time. Changes take effect immediately, and we prorate any billing differences.',
            },
            {
              q: 'What happens when my trial or plan expires?',
              a: 'You\'ll be downgraded to the Free plan. Your data and configurations are preserved — no information is lost.',
            },
            {
              q: 'Do you offer refunds?',
              a: 'Yes, we offer a 14-day money-back guarantee on all paid plans. Contact our support team for assistance.',
            },
            {
              q: 'Can I pay annually to save?',
              a: 'Yes! Annual billing saves you approximately 17% compared to monthly billing.',
            },
            {
              q: 'What payment methods do you accept?',
              a: 'We accept all major credit and debit cards through Stripe. Enterprise customers can also request invoice-based billing.',
            },
          ].map((faq) => (
            <div key={faq.q} className="border rounded-lg p-4 hover:border-primary/50 transition-colors">
              <h3 className="font-semibold flex items-center gap-2">
                <HelpCircle className="h-4 w-4 text-primary shrink-0" />
                {faq.q}
              </h3>
              <p className="text-sm text-muted-foreground mt-1 ml-6">{faq.a}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t">
        <div className="container mx-auto px-4 py-16 text-center">
          <h2 className="text-2xl font-bold mb-2">Ready to get started?</h2>
          <p className="text-muted-foreground mb-6 max-w-lg mx-auto">
            Join thousands of algo traders who trust SilverTrade AI for their automated trading.
          </p>
          <Button size="lg" onClick={() => navigate(isAuthenticated ? '/billing' : '/login')}>
            <ArrowRight className="h-5 w-5 mr-2" />
            {isAuthenticated ? 'Go to Billing' : 'Create Free Account'}
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>© {new Date().getFullYear()} SilverTrade AI. All rights reserved.</p>
          <p className="mt-1">
            Secure payments powered by{' '}
            <a
              href="https://stripe.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline inline-flex items-center gap-1"
            >
              <CreditCard className="h-3 w-3" />
              Stripe
            </a>
          </p>
        </div>
      </footer>
    </div>
  )
}
