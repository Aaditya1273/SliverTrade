'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ArrowRight, Mail, Lock, AlertCircle, CheckCircle2 } from 'lucide-react'
import { API_CONFIG } from '@/lib/api-config'

const PLATFORM_URL = API_CONFIG.PLATFORM_BASE

export default function LoginPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [registered, setRegistered] = useState(false)

  useEffect(() => {
    if (searchParams.get('registered') === 'true') {
      setRegistered(true)
      // Remove the query param without a page reload
      const url = new URL(window.location.href)
      url.searchParams.delete('registered')
      window.history.replaceState({}, '', url.toString())
    }
  }, [searchParams])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const formData = new URLSearchParams()
      formData.append('username', email)
      formData.append('password', password)

      const response = await fetch(`${PLATFORM_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
        credentials: 'include',
      })

      const data = await response.json()

      if (response.ok && data.status === 'success') {
        // Follow redirect if Platform provides one (e.g., broker auth step)
        if (data.redirect) {
          router.push(data.redirect)
        } else {
          router.push('/dashboard')
        }
        router.refresh()
      } else {
        setError(data.message || 'Invalid credentials. Please try again.')
      }
    } catch (err) {
      setError('Unable to connect to server. Ensure the Platform service is running on port 5000.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="mb-8">
          <Link href="/" className="text-xl font-bold tracking-tight mb-2 inline-block hover:text-muted-foreground transition-colors">
            SilverTrade
          </Link>
          <h1 className="text-3xl font-bold mb-2">Welcome Back</h1>
          <p className="text-muted-foreground">Sign in to access your trading dashboard</p>
        </div>

        {/* Success Message (after registration) */}
        {registered && (
          <div className="mb-6 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-emerald-500 mb-1">Account created successfully</p>
              <p className="text-xs text-muted-foreground">Sign in with your credentials to access the trading dashboard.</p>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-destructive/10 border border-destructive/20 flex gap-3">
            <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Email Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-sm font-medium">Email Address</Label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="pl-10 bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="text-sm font-medium">Password</Label>
              <Link href="/forgot-password" className="text-xs text-muted-foreground hover:text-foreground transition-colors">
                Forgot?
              </Link>
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="pl-10 bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                required
              />
            </div>
          </div>

          <Button
            type="submit"
            className="w-full gap-2"
            disabled={loading}
          >
            {loading ? 'Signing in...' : 'Sign In'} {!loading && <ArrowRight className="w-5 h-5" />}
          </Button>
        </form>

        {/* Signup Link */}
        <p className="text-center text-sm text-muted-foreground mt-6">
          Don&apos;t have an account?{' '}
          <Link href="/signup" className="text-accent hover:text-accent/80 font-medium transition-colors">
            Sign up free
          </Link>
        </p>

        {/* Security Note */}
        <div className="mt-8 p-4 rounded-lg bg-card/30 border border-border text-center">
          <p className="text-xs text-muted-foreground">
            We never store your exchange API keys. All trades execute through encrypted connections.
          </p>
        </div>
      </div>
    </main>
  )
}
