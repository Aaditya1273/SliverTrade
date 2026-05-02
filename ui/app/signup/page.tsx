'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { ArrowRight, Mail, Lock, Chrome, User } from 'lucide-react'

export default function SignupPage() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  })
  const [agreedToTerms, setAgreedToTerms] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (formData.password !== formData.confirmPassword) {
      alert('Passwords do not match')
      return
    }
    if (!agreedToTerms) {
      alert('Please agree to terms')
      return
    }
    setLoading(true)
    // TODO: Implement actual signup
    setTimeout(() => setLoading(false), 1000)
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
          <p className="text-muted-foreground">Join 50,000+ traders earning 2x+ returns</p>
        </div>

        {/* Social Signup */}
        <div className="mb-6">
          <Button
            variant="outline"
            className="w-full gap-2 border-border hover:bg-card/50"
            disabled={loading}
          >
            <Chrome className="w-5 h-5" />
            Sign up with Google
          </Button>
        </div>

        {/* Divider */}
        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-background text-muted-foreground">Or create with email</span>
          </div>
        </div>

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
            <p className="text-xs text-muted-foreground">At least 8 characters, with numbers and symbols</p>
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
              <Link href="/terms" className="text-accent hover:text-accent/80 transition-colors">
                Terms of Service
              </Link>
              {' '}and{' '}
              <Link href="/privacy" className="text-accent hover:text-accent/80 transition-colors">
                Privacy Policy
              </Link>
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
