'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ArrowRight, Mail, Lock, Chrome } from 'lucide-react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    // TODO: Implement actual auth
    setTimeout(() => setLoading(false), 1000)
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

        {/* Social Login */}
        <div className="mb-6">
          <Button
            variant="outline"
            className="w-full gap-2 border-border hover:bg-card/50"
            disabled={loading}
          >
            <Chrome className="w-5 h-5" />
            Continue with Google
          </Button>
        </div>

        {/* Divider */}
        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-background text-muted-foreground">Or continue with email</span>
          </div>
        </div>

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
