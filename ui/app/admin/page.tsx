'use client'

import { useQuery } from '@tanstack/react-query'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Users, Activity, Signal, Wifi, DollarSign, TrendingUp, Loader2, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PLATFORM } from '@/lib/api-config'
import { useAuth } from '@/hooks/useAuth'
import axios from 'axios'
import Link from 'next/link'

interface AdminStats {
  total_users: number
  free_users: number
  pro_users: number
  enterprise_users: number
  signals_today: number
  signals_this_month: number
  active_broker_connections: number
  recent_signups: number
  mrr: number
  services: Record<string, { status: string; latency_ms?: number; active_pools?: number; detail?: string }>
}

export default function AdminDashboardPage() {
  const { authenticated } = useAuth()

  const { data: stats, isLoading, error } = useQuery<AdminStats>({
    queryKey: ['admin-stats'],
    queryFn: async () => {
      const resp = await axios.get(PLATFORM('/admin/api/stats'), {
        withCredentials: true,
      })
      return resp.data as AdminStats
    },
    enabled: !!authenticated,
    refetchInterval: 60_000,
  })

  if (!authenticated) {
    return (
      <main className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <Card className="p-8 text-center border-border max-w-md">
          <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Access Denied</h1>
          <p className="text-muted-foreground mb-6">You need admin access to view this page.</p>              <Link href="/dashboard">
                <Button className="px-6 py-2 rounded-lg bg-accent text-accent-foreground font-medium">Back to Dashboard</Button>
              </Link>
        </Card>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-6 h-6 text-accent" />
            <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          </div>
          <p className="text-muted-foreground">System overview and user management.</p>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-accent" />
          </div>
        )}

        {/* Error */}
        {error && !isLoading && (
          <Card className="p-8 text-center border-border">
            <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-3" />
            <h2 className="font-semibold mb-1">Failed to Load Stats</h2>
            <p className="text-sm text-muted-foreground">{error instanceof Error ? error.message : 'Unknown error'}</p>
          </Card>
        )}

        {/* Stats Grid */}
        {!isLoading && !error && stats && (
          <>
            {/* Users Section */}
            <div className="mb-8">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Users className="w-5 h-5 text-accent" />
                Users
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard icon={<Users className="w-5 h-5" />} label="Total Users" value={stats.total_users} color="text-blue-500" />
                <StatCard icon={<Users className="w-5 h-5" />} label="Free" value={stats.free_users} color="text-gray-500" />
                <StatCard icon={<Users className="w-5 h-5" />} label="Pro" value={stats.pro_users} color="text-accent" />
                <StatCard icon={<Users className="w-5 h-5" />} label="Enterprise" value={stats.enterprise_users} color="text-purple-500" />
              </div>
            </div>

            {/* Revenue Section */}
            <div className="mb-8">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-accent" />
                Revenue
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <StatCard icon={<DollarSign className="w-5 h-5" />} label="MRR (Monthly)" value={`₹${(stats.mrr || 0).toLocaleString()}`} color="text-emerald-500" />
                <StatCard icon={<TrendingUp className="w-5 h-5" />} label="Recent Signups (24h)" value={stats.recent_signups} color="text-blue-500" />
                <StatCard icon={<Wifi className="w-5 h-5" />} label="Active Broker Connections" value={stats.active_broker_connections} color="text-accent" />
              </div>
            </div>

            {/* Signals Section */}
            <div className="mb-8">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Signal className="w-5 h-5 text-accent" />
                Signal Activity
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <StatCard icon={<Signal className="w-5 h-5" />} label="Signals Generated Today" value={stats.signals_today} color="text-accent" />
                <StatCard icon={<Signal className="w-5 h-5" />} label="Signals This Month" value={stats.signals_this_month} color="text-blue-500" />
              </div>
            </div>

            {/* Services Health */}
            <div className="mb-8">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-accent" />
                System Health
              </h2>
              <Card className="p-6 border-border">
                {stats.services && Object.keys(stats.services).length > 0 ? (
                  <div className="space-y-3">
                    {Object.entries(stats.services).map(([name, info]) => (
                      <div key={name} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                        <span className="text-sm font-medium">{name}</span>
                        <div className="flex items-center gap-3">
                          <Badge
                            className={
                              info.status === 'healthy'
                                ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                                : info.status === 'unavailable'
                                ? 'bg-gray-500/10 text-gray-400 border-gray-500/20'
                                : 'bg-rose-500/10 text-rose-500 border-rose-500/20'
                            }
                          >
                            {info.status}
                          </Badge>
                          {info.latency_ms !== undefined && (
                            <span className="text-xs text-muted-foreground">{info.latency_ms.toFixed(1)}ms</span>
                          )}
                          {info.active_pools !== undefined && (
                            <span className="text-xs text-muted-foreground">{info.active_pools} pools</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Service health data pending...</p>
                )}
              </Card>
            </div>

            {/* Admin Links */}
            <Card className="p-6 border-border">
              <h3 className="font-semibold mb-4">Admin Tools</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <AdminLink href="/admin/freeze" label="Freeze Quantities" />
                <AdminLink href="/admin/holidays" label="Market Holidays" />
                <AdminLink href="/admin/timings" label="Market Timings" />
              </div>
            </Card>
          </>
        )}
      </div>
    </main>
  )
}

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string | number; color: string }) {
  return (
    <Card className="p-5 border-border">
      <div className="flex items-center gap-3 mb-2">
        <span className={color}>{icon}</span>
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <p className="text-2xl font-bold">{typeof value === 'number' ? value.toLocaleString() : value}</p>
    </Card>
  )
}

function AdminLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href}>
      <div className="p-4 rounded-lg border border-border bg-card/30 hover:border-accent/30 hover:bg-card/50 transition-all cursor-pointer text-center">
        <p className="text-sm font-medium">{label}</p>
      </div>
    </Link>
  )
}
