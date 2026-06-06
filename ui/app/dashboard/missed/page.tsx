'use client'

import { Card } from '@/components/ui/card'
import { DollarSign, Zap, TrendingUp } from 'lucide-react'
import Link from 'next/link'

export default function MissedProfitsPage() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Missed Opportunities</h1>
          <p className="text-muted-foreground">
            Missed opportunity tracking activates once you receive your first signal.
            Generate a signal to start.
          </p>
        </div>

        {/* Stats Grid — all show — until real data exists */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card className="p-6 border-border">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-muted-foreground" />
              </div>
              <h3 className="font-medium text-sm text-muted-foreground">Total Missed Profit</h3>
            </div>
            <p className="text-3xl font-bold text-muted-foreground">—</p>
          </Card>

          <Card className="p-6 border-border">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-muted-foreground" />
              </div>
              <h3 className="font-medium text-sm text-muted-foreground">Avg. Missed %</h3>
            </div>
            <p className="text-3xl font-bold text-muted-foreground">—</p>
          </Card>

          <Card className="p-6 border-border">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                <Zap className="w-5 h-5 text-muted-foreground" />
              </div>
              <h3 className="font-medium text-sm text-muted-foreground">Total Signals</h3>
            </div>
            <p className="text-3xl font-bold text-muted-foreground">0</p>
          </Card>

          <Card className="p-6 border-border">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-muted-foreground" />
              </div>
              <h3 className="font-medium text-sm text-muted-foreground">High Confidence</h3>
            </div>
            <p className="text-3xl font-bold text-muted-foreground">—</p>
          </Card>
        </div>

        {/* Empty state */}
        <Card className="p-12 border-border flex flex-col items-center justify-center text-center">
          <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-4">
            <Zap className="w-8 h-8 text-accent" />
          </div>
          <h2 className="text-xl font-semibold mb-2">No Signals Yet</h2>
          <p className="text-sm text-muted-foreground mb-6 max-w-md">
            Missed opportunity tracking activates once you receive your first signal.
            Generate a signal from the AI Feed to start tracking. Every signal you don't
            act on will be recorded here with real missed profit calculations.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-accent-foreground text-sm font-medium hover:bg-accent/90 transition-colors"
          >
            Go to Dashboard
          </Link>
        </Card>

        {/* Info card */}
        <Card className="mt-8 p-6 border-border bg-accent/5">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-accent" />
            How It Works
          </h3>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>✓ Every signal you don&apos;t execute is automatically tracked</li>
            <li>✓ Missed profit is calculated from actual price movement 1 hour after signal</li>
            <li>✓ High confidence signals (80%+) you missed are highlighted</li>
            <li>✓ Enable alerts to get notified of future signals in real-time</li>
          </ul>
        </Card>
      </div>
    </main>
  )
}
