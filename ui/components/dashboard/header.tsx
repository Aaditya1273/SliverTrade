import Link from 'next/link'
import { Bell, Settings, EyeOff, Eye, Activity, Loader2, AlertTriangle, AlertCircle, Wifi, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useSettings } from '@/hooks/useSettings'
import { useAuth } from '@/hooks/useAuth'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { PLATFORM } from '@/lib/api-config'
import { toast } from 'sonner'

interface DashboardHeaderProps {
  hideBalances: boolean
  setHideBalances: (hide: boolean) => void
}

export function DashboardHeader({ hideBalances, setHideBalances }: DashboardHeaderProps) {
  const { data: settings } = useSettings()
  const { authenticated, apiKey, loading: authLoading } = useAuth()
  const queryClient = useQueryClient()

  const autoExecuteActive = settings?.auto_execute === true
  const needsBroker = authenticated && !apiKey && !authLoading

  const disableAutoExecuteMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(PLATFORM('/api/v1/settings'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ auto_execute: false }),
      })
      const data = await response.json()
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to disable')
      }
      return data
    },
    onSuccess: () => {
      toast.success('Auto-execute disabled')
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
    onError: (err: Error) => {
      toast.error(`Failed to disable: ${err.message}`)
    },
  })

  return (
    <>
      {/* Connect Broker Banner */}
      {needsBroker && (
        <div className="bg-amber-500/10 border-b border-amber-500/20 px-6 lg:px-8 py-2.5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-400">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>
              <strong>Broker not connected.</strong> Connect a broker to enable trading, view positions, and execute signals.
            </span>
          </div>
          <Link
            href="/setup"
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold transition-colors whitespace-nowrap flex-shrink-0"
          >
            <Wifi className="w-3.5 h-3.5" />
            Connect Broker
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      <header className="hidden md:flex border-b border-border px-6 lg:px-8 h-16 items-center justify-between bg-card/30 backdrop-blur-sm sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <div className="text-sm text-muted-foreground">
          Last updated: Just now
        </div>
        {autoExecuteActive && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge
                  className="bg-rose-500 hover:bg-rose-600 text-white border-0 cursor-pointer text-[10px] px-2 py-0.5 gap-1 transition-all"
                  onClick={() => disableAutoExecuteMutation.mutate()}
                >
                  {disableAutoExecuteMutation.isPending ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Activity className="w-3 h-3 animate-pulse" />
                  )}
                  AUTO
                </Badge>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                <p>Auto-execute active — click badge to disable</p>
                <p className="text-[10px] text-muted-foreground">Signals above {settings?.min_signal_confidence}% execute automatically</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
      
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setHideBalances(!hideBalances)}
          className="text-muted-foreground hover:text-foreground"
        >
          {hideBalances ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
        </Button>
        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
          <Bell className="w-5 h-5" />
        </Button>
        <Link href="/dashboard/settings">
          <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground" title="Settings">
            <Settings className="w-5 h-5" />
          </Button>
        </Link>
      </div>
    </header>
    </>
  )
}
