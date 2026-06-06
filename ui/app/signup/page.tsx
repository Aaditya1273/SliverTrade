'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { ArrowRight, Mail, Lock, User, AlertCircle } from 'lucide-react'
import { API_CONFIG } from '@/lib/api-config'

const PLATFORM_URL = API_CONFIG.PLATFORM_BASE

export default function SignupPage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  })
  const [agreedToTerms, setAgreedToTerms] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Client-side validation
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      return
    }
    if (!agreedToTerms) {
      setError('Please agree to the terms of service')
      return
    }
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    if (!/[A-Z]/.test(formData.password)) {
      setError('Password must contain at least one uppercase letter')
      return
    }
    if (!/[0-9]/.test(formData.password)) {
      setError('Password must contain at least one number')
      return
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(formData.password)) {
      setError('Password must contain at least one special character')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${PLATFORM_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: formData.name,
          email: formData.email,
          password: formData.password,
          accept_terms: true,
          accept_privacy: true,
          accept_risk: true,
        }),
        credentials: 'include',
      })

      const data = await response.json()

      if (response.ok && data.status === 'success') {
        // Registration successful — redirect to login with success message
        router.push('/login?registered=true')
        router.refresh()
      } else {
        setError(data.message || 'Registration failed. Please try again.')
      }
    } catch (err) {
      setError('Unable to connect to server. Ensure the Platform service is running on port 5000.')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  return (
    <main className="min-h-screen bg-background text-foreground flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="mb-8">
          <Link href="/" className="text-xl font-bold tracking-tight mb-2 inline-block hover:text-muted-foreground transition-colors">
            SilverTrade
          </Link>
          <h1 className="text-3xl font-bold mb-2">Create Account</h1>
          <p className="text-muted-foreground">Start making data-driven trading decisions</p>
        </div>

        {/* Info Banner — email verification is not yet implemented */}
        <div className="mb-6 p-4 rounded-lg bg-accent/10 border border-accent/20 flex gap-3">
          <Mail className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium text-accent mb-1">Account registration</p>
            <p className="text-xs text-muted-foreground">
              Creating an account will allow you to log in and access the dashboard.
              Email verification is optional and can be configured in settings.
            </p>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-destructive/10 border border-destructive/20 flex gap-3">
            <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Signup Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-sm font-medium">Full Name</Label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
              <Input
                id="name"
                name="name"
                type="text"
                placeholder="Alex Johnson"
                value={formData.name}
                onChange={handleChange}
                className="pl-10 bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email" className="text-sm font-medium">Email Address</Label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={handleChange}
                className="pl-10 bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-sm font-medium">Password</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
              <Input
                id="password"
                name="password"
                type="password"
                placeholder="••••••••"
                value={formData.password}
                onChange={handleChange}
                className="pl-10 bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                required
              />
            </div>
            <p className="text-xs text-muted-foreground">At least 8 characters</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword" className="text-sm font-medium">Confirm Password</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
              <Input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                placeholder="••••••••"
                value={formData.confirmPassword}
                onChange={handleChange}
                className="pl-10 bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                required
              />
            </div>
          </div>

          <div className="flex items-start gap-2">
            <Checkbox
              id="terms"
              checked={agreedToTerms}
              onCheckedChange={(checked) => setAgreedToTerms(checked as boolean)}
              className="mt-1"
            />
            <Label htmlFor="terms" className="text-sm font-normal text-muted-foreground cursor-pointer">
              I agree to the{' '}
              <Link href="/legal/terms" className="text-accent hover:text-accent/80 transition-colors">
                Terms of Service
              </Link>
              {' '}and{' '}
              <Link href="/legal/privacy" className="text-accent hover:text-accent/80 transition-colors">
                Privacy Policy
              </Link>
              {/* Phase 10 will build the full Terms of Service and Privacy Policy pages. */}
            </Label>
          </div>

          <Button
            type="submit"
            className="w-full gap-2"
            disabled={loading}
          >
            {loading ? 'Creating account...' : 'Create Account'} {!loading && <ArrowRight className="w-5 h-5" />}
          </Button>
        </form>

        {/* Login Link */}
        <p className="text-center text-sm text-muted-foreground mt-6">
          Already have an account?{' '}
          <Link href="/login" className="text-accent hover:text-accent/80 font-medium transition-colors">
            Sign in
          </Link>
        </p>

        {/* Security Note */}
        <div className="mt-8 p-4 rounded-lg bg-card/30 border border-border text-center">
          <p className="text-xs text-muted-foreground">
            Your data is encrypted end-to-end. We use bank-grade security for all transactions.
          </p>
        </div>
      </div>
    </main>
  )
}
