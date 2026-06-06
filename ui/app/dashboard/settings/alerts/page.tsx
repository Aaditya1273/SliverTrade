'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Loader2, Bell, Check, AlertTriangle, Clock } from 'lucide-react'
import { STRATEGY } from '@/lib/api-config'
import { toast } from 'sonner'
import { useQuery, useMutation } from '@tanstack/react-query'

const STRATEGY_BASE = STRATEGY('/api/v1')

export default function AlertsSettingsPage() {
  const router = useRouter()
  
  const [settings, setSettings] = useState({
    enabled: true,
    min_confidence: 60,
    symbols: '',
    channels: ['browser'],
    quiet_hours_start: 22,
    quiet_hours_end: 8,
  })

  const { data: rules, isLoading } = useQuery({
    queryKey: ['alert-rules'],
    queryFn: async () => {
      const response = await fetch(STRATEGY_BASE + '/alert-rules')
      const data = await response.json()
      return data.data
    },
  })

  useEffect(() => {
    if (rules && rules.length > 0) {
      const rule = rules[0]
      setSettings({
        enabled: rule.enabled,
        min_confidence: rule.min_confidence,
        symbols: rule.symbols.join(', '),
        channels: rule.channels,
        quiet_hours_start: rule.quiet_hours_start || 22,
        quiet_hours_end: rule.quiet_hours_end || 8,
      })
    }
  }, [rules])

  const saveSettingsMutation = useMutation({
    mutationFn: async (newSettings: typeof settings) => {
      const response = await fetch(STRATEGY_BASE + '/alert-rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newSettings,
          symbols: newSettings.symbols.split(',').map((s: string) => s.trim()).filter(Boolean),
          id: rules && Array.isArray(rules) && rules.length > 0 ? rules[0].id : undefined,
        }),
      })
      const data = await response.json()
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to save settings')
      }
      return data
    },
    onSuccess: () => {
      toast.success('Alert settings saved successfully')
    },
    onError: (error: any) => {
      toast.error(`Failed to save: ${error.message}`)
    },
  })

  const testAlertMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(STRATEGY_BASE + '/test-alert', {
        method: 'POST',
      })
      const data = await response.json()
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to send test alert')
      }
      return data
    },
    onSuccess: () => {
      toast.success('Test alert sent! Check your notifications.')
    },
    onError: (error: any) => {
      toast.error(`Failed to send test: ${error.message}`)
    },
  })

  const handleSave = () => {
    saveSettingsMutation.mutate(settings)
  }

  const handleTestAlert = () => {
    testAlertMutation.mutate()
  }

  const toggleChannel = (channel: string) => {
    if (settings.channels.includes(channel)) {
      setSettings({
        ...settings,
        channels: settings.channels.filter(c => c !== channel),
      })
    } else {
      setSettings({
        ...settings,
        channels: [...settings.channels, channel],
      })
    }
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
          <h1 className="text-2xl font-bold">Alert Settings</h1>
          <p className="text-muted-foreground">Configure when and how you receive trading signal notifications</p>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Signal Alerts</CardTitle>
            <CardDescription>Get notified when new trading signals are generated</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <Label>Enable Signal Alerts</Label>
              <Switch
                checked={settings.enabled}
                onCheckedChange={(enabled) => setSettings({ ...settings, enabled })}
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Minimum Confidence</Label>
                <Badge variant="outline">{settings.min_confidence}%</Badge>
              </div>
              <Slider
                value={[settings.min_confidence]}
                onValueChange={([value]) => setSettings({ ...settings, min_confidence: value })}
                min={50}
                max={95}
                step={5}
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                Only send alerts for signals above this confidence level
              </p>
            </div>

            <div className="space-y-2">
              <Label>Symbols to Watch (optional)</Label>
              <Input
                value={settings.symbols}
                onChange={(e) => setSettings({ ...settings, symbols: e.target.value })}
                placeholder="BTC/USDT, ETH/USDT (leave empty for all symbols)"
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated list. Leave empty to receive alerts for all symbols.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Notification Channels</CardTitle>
            <CardDescription>Choose how you want to receive alerts</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg border border-border">
              <div className="flex items-center gap-3">
                <Bell className="w-5 h-5 text-accent" />
                <div>
                  <div className="font-medium">Browser Push</div>
                  <div className="text-xs text-muted-foreground">Desktop notifications in your browser</div>
                </div>
              </div>
              <Switch
                checked={settings.channels.includes('browser')}
                onCheckedChange={() => toggleChannel('browser')}
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg border border-border">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-blue-500" />
                <div>
                  <div className="font-medium">Telegram</div>
                  <div className="text-xs text-muted-foreground">Send alerts to your Telegram bot</div>
                </div>
              </div>
              <Switch
                checked={settings.channels.includes('telegram')}
                onCheckedChange={() => toggleChannel('telegram')}
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg border border-border">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-emerald-500" />
                <div>
                  <div className="font-medium">Email</div>
                  <div className="text-xs text-muted-foreground">Email notifications</div>
                </div>
              </div>
              <Switch
                checked={settings.channels.includes('email')}
                onCheckedChange={() => toggleChannel('email')}
              />
            </div>
          </CardContent>
        </Card>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Quiet Hours</CardTitle>
            <CardDescription>Disable alerts during specific hours (UTC)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Start Hour</Label>
                <Badge variant="outline">{settings.quiet_hours_start}:00</Badge>
              </div>
              <Slider
                value={[settings.quiet_hours_start]}
                onValueChange={([value]) => setSettings({ ...settings, quiet_hours_start: value })}
                min={0}
                max={23}
                step={1}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>End Hour</Label>
                <Badge variant="outline">{settings.quiet_hours_end}:00</Badge>
              </div>
              <Slider
                value={[settings.quiet_hours_end]}
                onValueChange={([value]) => setSettings({ ...settings, quiet_hours_end: value })}
                min={0}
                max={23}
                step={1}
                className="w-full"
              />
            </div>

            <p className="text-xs text-muted-foreground">
              No alerts will be sent between {settings.quiet_hours_start}:00 and {settings.quiet_hours_end}:00 UTC.
            </p>
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
            onClick={handleTestAlert}
            disabled={testAlertMutation.isPending}
          >
            {testAlertMutation.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Bell className="w-4 h-4 mr-2" />
            )}
            Test Alert
          </Button>
          <Button
            variant="outline"
            onClick={() => router.push('/dashboard')}
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  )
}
