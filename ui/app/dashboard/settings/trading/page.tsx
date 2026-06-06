'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Loader2, AlertTriangle, Check, Settings } from 'lucide-react'
import { PLATFORM } from '@/lib/api-config'
import { useAuth } from '@/hooks/useAuth'
import { toast } from 'sonner'
import { useQuery, useMutation } from '@tanstack/react-query'

export default function TradingSettingsPage() {
  const router = useRouter()
  const { apiKey } = useAuth()
  const [autoExecuteDialogOpen, setAutoExecuteDialogOpen] = useState(false)
  const [pendingAutoExecute, setPendingAutoExecute] = useState(false)

  const [settings, setSettings] = useState({
    min_signal_confidence: 60,
    risk_per_trade_pct: 2.0,
    default_product_type: 'MIS',
    default_order_type: 'MARKET',
    auto_execute: false,
    max_open_positions: 3,
    daily_loss_limit_pct: 5.0,
  })

  const { data: currentSettings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      const response = await fetch(PLATFORM('/api/v1/settings'), {
        method: 'GET',
        credentials: 'include',
      })
      const data = await response.json()
      return data.data || data
    },
  })

  useEffect(() => {
    if (currentSettings) {
      setSettings({
        min_signal_confidence: currentSettings.min_signal_confidence || 60,
        risk_per_trade_pct: currentSettings.risk_per_trade_pct || 2.0,
        default_product_type: currentSettings.default_product_type || 'MIS',
        default_order_type: currentSettings.default_order_type || 'MARKET',
        auto_execute: currentSettings.auto_execute || false,
        max_open_positions: currentSettings.max_open_positions || 3,
        daily_loss_limit_pct: currentSettings.daily_loss_limit_pct || 5.0,
      })
    }
  }, [currentSettings])

  const saveSettingsMutation = useMutation({
    mutationFn: async (newSettings: typeof settings) => {
      const response = await fetch(PLATFORM('/api/v1/settings'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(newSettings),
      })
      const data = await response.json()
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to save settings')
      }
      return data
    },
    onSuccess: () => {
      toast.success('Settings saved successfully')
    },
    onError: (error: any) => {
      toast.error(`Failed to save: ${error.message}`)
    },
  })

  const handleSave = () => {
    saveSettingsMutation.mutate(settings)
  }

  const handleAutoExecuteToggle = (enabled: boolean) => {
    if (enabled) {
      setPendingAutoExecute(true)
      setAutoExecuteDialogOpen(true)
    } else {
      setSettings({ ...settings, auto_execute: false })
    }
  }

  const confirmAutoExecute = () => {
    setSettings({ ...settings, auto_execute: true })
    setAutoExecuteDialogOpen(false)
    setPendingAutoExecute(false)
  }

  if (!apiKey) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="p-6 text-center">
            <Settings className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
            <p className="text-muted-foreground">Connect a broker to access settings</p>
            <Button onClick={() => router.push('/setup')} className="mt-4">
              Connect Broker
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background p-4 md:p-8">
      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">Trading Settings</h1>
          <p className="text-muted-foreground">Configure your risk management and execution preferences</p>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Signal Execution</CardTitle>
            <CardDescription>Configure when and how signals are executed</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Minimum Signal Confidence</Label>
                <Badge variant="outline">{settings.min_signal_confidence}%</Badge>
              </div>
              <Slider
                value={[settings.min_signal_confidence]}
                onValueChange={([value]) => setSettings({ ...settings, min_signal_confidence: value })}
                min={50}
                max={95}
                step={5}
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                Signals below this confidence will not be executed
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Auto-Execute Mode</Label>
                <Switch
                  checked={settings.auto_execute}
                  onCheckedChange={handleAutoExecuteToggle}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                When enabled, signals above confidence threshold are executed automatically
              </p>
              {settings.auto_execute && (
                <Badge className="bg-rose-500 text-white">
                  <AlertTriangle className="w-3 h-3 mr-1" />
                  AUTO MODE ACTIVE
                </Badge>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Max Open Positions</Label>
                <Badge variant="outline">{settings.max_open_positions}</Badge>
              </div>
              <Slider
                value={[settings.max_open_positions]}
                onValueChange={([value]) => setSettings({ ...settings, max_open_positions: value })}
                min={1}
                max={10}
                step={1}
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                Maximum number of positions to hold simultaneously
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Risk Management</CardTitle>
            <CardDescription>Control your risk per trade and daily limits</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Risk Per Trade</Label>
                <Badge variant="outline">{settings.risk_per_trade_pct}%</Badge>
              </div>
              <Slider
                value={[settings.risk_per_trade_pct]}
                onValueChange={([value]) => setSettings({ ...settings, risk_per_trade_pct: value })}
                min={0.5}
                max={5}
                step={0.5}
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                Percentage of available capital to risk per trade
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Daily Loss Limit</Label>
                <Badge variant="outline">{settings.daily_loss_limit_pct}%</Badge>
              </div>
              <Slider
                value={[settings.daily_loss_limit_pct]}
                onValueChange={([value]) => setSettings({ ...settings, daily_loss_limit_pct: value })}
                min={1}
                max={20}
                step={1}
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                Halt all trading if daily P&L drops below this percentage
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Order Defaults</CardTitle>
            <CardDescription>Default parameters for manual orders</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Default Product Type</Label>
              <div className="flex gap-2">
                {['CNC', 'NRML', 'MIS'].map((type) => (
                  <Button
                    key={type}
                    type="button"
                    variant={settings.default_product_type === type ? 'default' : 'outline'}
                    onClick={() => setSettings({ ...settings, default_product_type: type })}
                    className="flex-1"
                  >
                    {type}
                  </Button>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                CNC: Delivery, NRML: Overnight, MIS: Intraday
              </p>
            </div>

            <div className="space-y-2">
              <Label>Default Order Type</Label>
              <div className="flex gap-2">
                {['MARKET', 'LIMIT'].map((type) => (
                  <Button
                    key={type}
                    type="button"
                    variant={settings.default_order_type === type ? 'default' : 'outline'}
                    onClick={() => setSettings({ ...settings, default_order_type: type })}
                    className="flex-1"
                  >
                    {type}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex gap-2">
          <Button
            onClick={handleSave}
            disabled={saveSettingsMutation.isPending}
            className="flex-1"
          >
            {saveSettingsMutation.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Check className="w-4 h-4 mr-2" />
            )}
            Save Settings
          </Button>
          <Button
            variant="outline"
            onClick={() => router.push('/dashboard')}
          >
            Cancel
          </Button>
        </div>
      </div>

      <AlertDialog open={autoExecuteDialogOpen} onOpenChange={setAutoExecuteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-rose-500" />
              Enable Auto-Execute Mode?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This will automatically execute all signals above {settings.min_signal_confidence}% confidence without manual confirmation. 
              <br /><br />
              <strong className="text-rose-500">Warning: This can result in real trades being placed automatically. Ensure you understand the risks before enabling.</strong>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setPendingAutoExecute(false)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={confirmAutoExecute} className="bg-rose-500 hover:bg-rose-600">
              Enable Auto-Execute
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
