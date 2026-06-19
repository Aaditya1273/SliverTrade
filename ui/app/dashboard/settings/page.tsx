'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Settings,
  Shield,
  Zap,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Info,
  Bell,
  Clock,
} from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { PLATFORM, STRATEGY } from '@/lib/api-config'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useSettings, type TradingSettings } from '@/hooks/useSettings'
import { useQuery, useMutation } from '@tanstack/react-query'

const STRATEGY_BASE = STRATEGY('/api/v1')

interface AlertConfig {
  enabled: boolean
  min_confidence: number
  symbols: string
  channels: string[]
  quiet_hours_start: number
  quiet_hours_end: number
}

export default function SettingsPage() {
  const { data: savedSettings, isLoading: settingsLoading } = useSettings()
  const queryClient = useQueryClient()
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [activeTab, setActiveTab] = useState('trading')

  // ── Trading Settings ──
  const [tradingSettings, setTradingSettings] = useState<TradingSettings>({
    default_exchange: 'NSE',
    default_product_type: 'MIS',
    default_order_type: 'MARKET',
    risk_per_trade_pct: 2,
    min_signal_confidence: 60,
    max_open_positions: 5,
    daily_loss_limit_pct: 5,
    auto_execute: false,
  })

  // ── Alert Settings ──
  const [alertSettings, setAlertSettings] = useState<AlertConfig>({
    enabled: true,
    min_confidence: 60,
    symbols: '',
    channels: ['browser'],
    quiet_hours_start: 22,
    quiet_hours_end: 8,
  })

  const { data: alertRules, isLoading: alertsLoading } = useQuery({
    queryKey: ['alert-rules'],
    queryFn: async () => {
      const response = await fetch(STRATEGY_BASE + '/alert-rules')
      const data = await response.json()
      return data.data
    },
  })

  // Populate forms from server
  useEffect(() => {
    if (savedSettings) {
      setTradingSettings(savedSettings)
    }
  }, [savedSettings])

  useEffect(() => {
    if (alertRules && alertRules.length > 0) {
      const rule = alertRules[0]
      setAlertSettings({
        enabled: rule.enabled ?? true,
        min_confidence: rule.min_confidence ?? 60,
        symbols: Array.isArray(rule.symbols) ? rule.symbols.join(', ') : '',
        channels: rule.channels ?? ['browser'],
        quiet_hours_start: rule.quiet_hours_start ?? 22,
        quiet_hours_end: rule.quiet_hours_end ?? 8,
      })
    }
  }, [alertRules])

  // ── Save Trading Settings ──
  const handleSaveTrading = async () => {
    setSaving(true)
    setSaved(false)
    try {
      const response = await fetch(PLATFORM('/api/v1/settings'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(tradingSettings),
      })
      const data = await response.json()
      if (data.status === 'success') {
        queryClient.invalidateQueries({ queryKey: ['settings'] })
        setSaved(true)
        toast.success('Trading settings saved')
        setTimeout(() => setSaved(false), 3000)
      } else {
        toast.error(data.message || 'Failed to save settings')
      }
    } catch {
      toast.error('Unable to reach server')
    } finally {
      setSaving(false)
    }
  }

  // ── Save Alert Settings ──
  const saveAlertMutation = useMutation({
    mutationFn: async (newSettings: AlertConfig) => {
      const response = await fetch(STRATEGY_BASE + '/alert-rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newSettings,
          symbols: newSettings.symbols
            ? newSettings.symbols.split(',').map((s: string) => s.trim()).filter(Boolean)
            : [],
          id: alertRules && Array.isArray(alertRules) && alertRules.length > 0 ? alertRules[0].id : undefined,
        }),
      })
      const data = await response.json()
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to save alert settings')
      }
      return data
    },
    onSuccess: () => {
      toast.success('Alert settings saved successfully')
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] })
    },
    onError: (error: any) => {
      toast.error(`Failed to save: ${error.message}`)
    },
  })

  const testAlertMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(STRATEGY_BASE + '/test-alert', { method: 'POST' })
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

  const toggleChannel = (channel: string) => {
    setAlertSettings(prev => ({
      ...prev,
      channels: prev.channels.includes(channel)
        ? prev.channels.filter(c => c !== channel)
        : [...prev.channels, channel],
    }))
  }

  return (
    <div className="p-4 md:p-6 lg:p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Settings className="w-6 h-6 text-accent" />
            <h1 className="text-3xl font-bold">Settings</h1>
          </div>
          <p className="text-muted-foreground">
            Configure trading execution, risk management, and alert preferences
          </p>
        </div>

        {/* Tab Navigation */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="trading" className="flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Trading
            </TabsTrigger>
            <TabsTrigger value="alerts" className="flex items-center gap-2">
              <Bell className="w-4 h-4" />
              Alerts
            </TabsTrigger>
          </TabsList>

          {/* ═══════════ TRADING TAB ═══════════ */}
          <TabsContent value="trading" className="space-y-6 mt-6">
            {settingsLoading ? (
              <Card className="p-12 border-border flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-accent" />
              </Card>
            ) : (
              <>
                {/* Signal Execution */}
                <Card className="p-6 border-border">
                  <div className="flex items-center gap-2 mb-5">
                    <Zap className="w-5 h-5 text-accent" />
                    <h2 className="text-lg font-semibold">Signal Execution</h2>
                  </div>

                  {/* Auto Execute */}
                  <div className="flex items-center justify-between py-4 border-b border-border/50">
                    <div className="flex-1 pr-8">
                      <div className="flex items-center gap-2 mb-0.5">
                        <Label className="text-sm font-medium">Auto-Execute Signals</Label>
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger>
                              <Info className="w-3.5 h-3.5 text-muted-foreground" />
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                              When enabled, signals above your confidence threshold are placed as market orders automatically without requiring manual confirmation.
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                        {tradingSettings.auto_execute && (
                          <Badge className="bg-rose-500/10 text-rose-500 border-rose-500/20 text-[10px] px-1.5">
                            LIVE
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Signals above confidence threshold execute automatically
                      </p>
                    </div>
                    <Switch
                      checked={tradingSettings.auto_execute}
                      onCheckedChange={(v) => setTradingSettings(s => ({ ...s, auto_execute: v }))}
                    />
                  </div>

                  {/* Min Signal Confidence */}
                  <div className="py-4 border-b border-border/50">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <Label className="text-sm font-medium">Minimum Signal Confidence</Label>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Only execute signals above this threshold
                        </p>
                      </div>
                      <Badge variant="outline" className="border-accent text-accent font-mono">
                        {tradingSettings.min_signal_confidence}%
                      </Badge>
                    </div>
                    <Slider
                      min={50} max={95} step={5}
                      value={[tradingSettings.min_signal_confidence]}
                      onValueChange={([v]) => setTradingSettings(s => ({ ...s, min_signal_confidence: v }))}
                    />
                    <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                      <span>50% (more signals)</span>
                      <span>95% (fewer, higher quality)</span>
                    </div>
                  </div>

                  {/* Default Exchange, Product Type, Order Type */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 py-4">
                    <div>
                      <Label className="text-sm font-medium">Default Exchange</Label>
                      <Select
                        value={tradingSettings.default_exchange}
                        onValueChange={(v) => setTradingSettings(s => ({ ...s, default_exchange: v }))}
                      >
                        <SelectTrigger className="mt-2 bg-card/50 border-border">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="NSE">NSE</SelectItem>
                          <SelectItem value="BSE">BSE</SelectItem>
                          <SelectItem value="NFO">NFO (F&O)</SelectItem>
                          <SelectItem value="MCX">MCX</SelectItem>
                          <SelectItem value="CRYPTO">CRYPTO</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-sm font-medium">Product Type</Label>
                      <Select
                        value={tradingSettings.default_product_type}
                        onValueChange={(v) => setTradingSettings(s => ({ ...s, default_product_type: v }))}
                      >
                        <SelectTrigger className="mt-2 bg-card/50 border-border">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="MIS">MIS (Intraday)</SelectItem>
                          <SelectItem value="CNC">CNC (Delivery)</SelectItem>
                          <SelectItem value="NRML">NRML (Overnight)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-sm font-medium">Order Type</Label>
                      <Select
                        value={tradingSettings.default_order_type}
                        onValueChange={(v) => setTradingSettings(s => ({ ...s, default_order_type: v }))}
                      >
                        <SelectTrigger className="mt-2 bg-card/50 border-border">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="MARKET">MARKET</SelectItem>
                          <SelectItem value="LIMIT">LIMIT</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </Card>

                {/* Risk Management */}
                <Card className="p-6 border-border">
                  <div className="flex items-center gap-2 mb-5">
                    <Shield className="w-5 h-5 text-accent" />
                    <h2 className="text-lg font-semibold">Risk Management</h2>
                  </div>

                  <div className="space-y-6">
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <Label className="text-sm font-medium">Risk Per Trade</Label>
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger><Info className="w-3.5 h-3.5 text-muted-foreground" /></TooltipTrigger>
                                <TooltipContent>Maximum % of available capital to risk on a single trade</TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </div>
                          <p className="text-xs text-muted-foreground mt-0.5">% of capital per trade for auto position sizing</p>
                        </div>
                        <Badge variant="outline" className="border-accent text-accent font-mono">{tradingSettings.risk_per_trade_pct}%</Badge>
                      </div>
                      <Slider min={0.5} max={5} step={0.5} value={[tradingSettings.risk_per_trade_pct]}
                        onValueChange={([v]) => setTradingSettings(s => ({ ...s, risk_per_trade_pct: v }))} />
                      <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                        <span>0.5% (conservative)</span>
                        <span>5% (aggressive)</span>
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <Label className="text-sm font-medium">Max Open Positions</Label>
                          <p className="text-xs text-muted-foreground mt-0.5">Block new orders when this many positions are open</p>
                        </div>
                        <Badge variant="outline" className="border-accent text-accent font-mono">{tradingSettings.max_open_positions}</Badge>
                      </div>
                      <Slider min={1} max={20} step={1} value={[tradingSettings.max_open_positions]}
                        onValueChange={([v]) => setTradingSettings(s => ({ ...s, max_open_positions: v }))} />
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <Label className="text-sm font-medium">Daily Loss Limit</Label>
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                          </div>
                          <p className="text-xs text-muted-foreground mt-0.5">Halt all trading when daily loss exceeds this %</p>
                        </div>
                        <Badge variant="outline" className="border-destructive text-destructive font-mono">-{tradingSettings.daily_loss_limit_pct}%</Badge>
                      </div>
                      <Slider min={1} max={20} step={1} value={[tradingSettings.daily_loss_limit_pct]}
                        onValueChange={([v]) => setTradingSettings(s => ({ ...s, daily_loss_limit_pct: v }))} />
                      <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                        <span>-1% (very tight)</span>
                        <span>-20% (very loose)</span>
                      </div>
                    </div>
                  </div>
                </Card>

                {/* Auto-Execute Warning */}
                {tradingSettings.auto_execute && (
                  <Card className="p-4 border-destructive/20 bg-destructive/5 border">
                    <div className="flex gap-3">
                      <AlertTriangle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
                      <div className="text-sm">
                        <p className="font-semibold text-destructive mb-1">Auto-Execute is ON</p>
                        <p className="text-xs text-muted-foreground">
                          Signals above {tradingSettings.min_signal_confidence}% confidence will be automatically
                          placed as {tradingSettings.default_order_type} orders using {tradingSettings.default_product_type}.
                          Max {tradingSettings.max_open_positions} concurrent positions. Daily loss cap: -{tradingSettings.daily_loss_limit_pct}%.
                        </p>
                      </div>
                    </div>
                  </Card>
                )}

                {/* Config Summary */}
                <Card className="p-5 border-border bg-card/30">
                  <div className="flex items-center gap-2 mb-4">
                    <TrendingUp className="w-4 h-4 text-accent" />
                    <h3 className="text-sm font-semibold">Active Configuration</h3>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                    {[
                      { label: 'Exchange', value: tradingSettings.default_exchange },
                      { label: 'Product', value: tradingSettings.default_product_type },
                      { label: 'Order', value: tradingSettings.default_order_type },
                      { label: 'Auto-Execute', value: tradingSettings.auto_execute ? 'ON' : 'OFF', warn: tradingSettings.auto_execute },
                    ].map(item => (
                      <div key={item.label} className="p-3 rounded-lg bg-card/50 border border-border">
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">{item.label}</p>
                        <p className={`text-sm font-semibold ${item.warn ? 'text-rose-500' : ''}`}>{item.value}</p>
                      </div>
                    ))}
                  </div>
                </Card>

                {/* Save */}
                <div className="flex justify-end pb-8">
                  <Button onClick={handleSaveTrading} disabled={saving} size="lg" className="gap-2 min-w-[160px]">
                    {saving ? (
                      <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</>
                    ) : saved ? (
                      <><CheckCircle2 className="w-4 h-4 text-emerald-400" /> Saved</>
                    ) : (
                      'Save Settings'
                    )}
                  </Button>
                </div>
              </>
            )}
          </TabsContent>

          {/* ═══════════ ALERTS TAB ═══════════ */}
          <TabsContent value="alerts" className="space-y-6 mt-6">
            {alertsLoading ? (
              <Card className="p-12 border-border flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-accent" />
              </Card>
            ) : (
              <>
                {/* Signal Alerts */}
                <Card className="p-6 border-border">
                  <div className="flex items-center gap-2 mb-5">
                    <Bell className="w-5 h-5 text-accent" />
                    <h2 className="text-lg font-semibold">Signal Alerts</h2>
                  </div>
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="text-sm font-medium">Enable Signal Alerts</Label>
                        <p className="text-xs text-muted-foreground mt-0.5">Get notified when new trading signals are generated</p>
                      </div>
                      <Switch checked={alertSettings.enabled} onCheckedChange={(v) => setAlertSettings(s => ({ ...s, enabled: v }))} />
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <Label className="text-sm font-medium">Minimum Confidence</Label>
                        <Badge variant="outline">{alertSettings.min_confidence}%</Badge>
                      </div>
                      <Slider min={50} max={95} step={5} value={[alertSettings.min_confidence]}
                        onValueChange={([v]) => setAlertSettings(s => ({ ...s, min_confidence: v }))} />
                      <p className="text-xs text-muted-foreground mt-1">Only send alerts for signals above this confidence level</p>
                    </div>

                    <div>
                      <Label className="text-sm font-medium">Symbols to Watch (optional)</Label>
                      <Input
                        value={alertSettings.symbols}
                        onChange={(e) => setAlertSettings(s => ({ ...s, symbols: e.target.value }))}
                        placeholder="BTC/USDT, ETH/USDT (leave empty for all symbols)"
                        className="mt-2 bg-card/50 border-border focus:border-accent/50"
                      />
                      <p className="text-xs text-muted-foreground mt-1">Comma-separated list. Leave empty for all symbols.</p>
                    </div>
                  </div>
                </Card>

                {/* Notification Channels */}
                <Card className="p-6 border-border">
                  <div className="flex items-center gap-2 mb-5">
                    <Bell className="w-5 h-5 text-accent" />
                    <h2 className="text-lg font-semibold">Notification Channels</h2>
                  </div>
                  <div className="space-y-4">
                    {[
                      { id: 'browser', label: 'Browser Push', desc: 'Desktop notifications in your browser', icon: Bell, color: 'text-accent' },
                      { id: 'telegram', label: 'Telegram', desc: 'Send alerts to your Telegram bot', icon: AlertTriangle, color: 'text-blue-500' },
                      { id: 'email', label: 'Email', desc: 'Email notifications', icon: Clock, color: 'text-emerald-500' },
                    ].map(channel => {
                      const Icon = channel.icon
                      return (
                        <div key={channel.id} className="flex items-center justify-between p-3 rounded-lg border border-border">
                          <div className="flex items-center gap-3">
                            <Icon className={`w-5 h-5 ${channel.color}`} />
                            <div>
                              <div className="font-medium">{channel.label}</div>
                              <div className="text-xs text-muted-foreground">{channel.desc}</div>
                            </div>
                          </div>
                          <Switch
                            checked={alertSettings.channels.includes(channel.id)}
                            onCheckedChange={() => toggleChannel(channel.id)}
                          />
                        </div>
                      )
                    })}
                  </div>
                </Card>

                {/* Quiet Hours */}
                <Card className="p-6 border-border">
                  <div className="flex items-center gap-2 mb-5">
                    <Clock className="w-5 h-5 text-accent" />
                    <h2 className="text-lg font-semibold">Quiet Hours</h2>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <Label className="text-sm font-medium">Start Hour (UTC)</Label>
                        <Badge variant="outline">{alertSettings.quiet_hours_start}:00</Badge>
                      </div>
                      <Slider min={0} max={23} step={1} value={[alertSettings.quiet_hours_start]}
                        onValueChange={([v]) => setAlertSettings(s => ({ ...s, quiet_hours_start: v }))} />
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <Label className="text-sm font-medium">End Hour (UTC)</Label>
                        <Badge variant="outline">{alertSettings.quiet_hours_end}:00</Badge>
                      </div>
                      <Slider min={0} max={23} step={1} value={[alertSettings.quiet_hours_end]}
                        onValueChange={([v]) => setAlertSettings(s => ({ ...s, quiet_hours_end: v }))} />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      No alerts between {alertSettings.quiet_hours_start}:00 and {alertSettings.quiet_hours_end}:00 UTC
                    </p>
                  </div>
                </Card>

                {/* Save & Test */}
                <div className="flex gap-2 pb-8">
                  <Button
                    onClick={() => saveAlertMutation.mutate(alertSettings)}
                    disabled={saveAlertMutation.isPending}
                    className="flex-1"
                  >
                    {saveAlertMutation.isPending ? (
                      <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Saving...</>
                    ) : (
                      <><CheckCircle2 className="w-4 h-4 mr-2" /> Save Alert Settings</>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => testAlertMutation.mutate()}
                    disabled={testAlertMutation.isPending}
                  >
                    {testAlertMutation.isPending ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Bell className="w-4 h-4 mr-2" />
                    )}
                    Test Alert
                  </Button>
                </div>
              </>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
