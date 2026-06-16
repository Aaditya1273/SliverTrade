'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import { Badge } from '@/components/ui/badge'
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
} from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { PLATFORM } from '@/lib/api-config'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useSettings, type TradingSettings } from '@/hooks/useSettings'
import { useAuth } from '@/hooks/useAuth'

export default function SettingsPage() {
  const { authenticated } = useAuth()
  const { data: savedSettings, isLoading } = useSettings()
  const queryClient = useQueryClient()
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const [settings, setSettings] = useState<TradingSettings>({
    default_exchange: 'NSE',
    default_product_type: 'MIS',
    default_order_type: 'MARKET',
    risk_per_trade_pct: 2,
    min_signal_confidence: 60,
    max_open_positions: 5,
    daily_loss_limit_pct: 5,
    auto_execute: false,
  })

  // Populate form from server once loaded
  useEffect(() => {
    if (savedSettings) {
      setSettings(savedSettings)
    }
  }, [savedSettings])

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)

    try {
      const response = await fetch(PLATFORM('/api/v1/settings'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(settings),
      })
      const data = await response.json()

      if (data.status === 'success') {
        // Invalidate so all components (AIFeed, execute_signal) pick up new settings
        queryClient.invalidateQueries({ queryKey: ['settings'] })
        setSaved(true)
        toast.success('Settings saved')
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

  if (!authenticated) {
    return (
      <main className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Sign in to access settings.</p>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Settings className="w-6 h-6 text-accent" />
            <h1 className="text-3xl font-bold">Trading Settings</h1>
          </div>
          <p className="text-muted-foreground">
            Configure how SilverTrade executes signals on your behalf
          </p>
        </div>

        {isLoading ? (
          <Card className="p-12 border-border flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-accent" />
          </Card>
        ) : (
          <>
            {/* ── Execution Mode ─────────────────────────────────────── */}
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
                    {settings.auto_execute && (
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
                  checked={settings.auto_execute}
                  onCheckedChange={(v) => setSettings(s => ({ ...s, auto_execute: v }))}
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
                  <Badge
                    variant="outline"
                    className="border-accent text-accent font-mono"
                  >
                    {settings.min_signal_confidence}%
                  </Badge>
                </div>
                <Slider
                  min={50}
                  max={95}
                  step={5}
                  value={[settings.min_signal_confidence]}
                  onValueChange={([v]) => setSettings(s => ({ ...s, min_signal_confidence: v }))}
                  className="cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                  <span>50% (more signals)</span>
                  <span>95% (fewer, higher quality)</span>
                </div>
              </div>

              {/* Default Exchange */}
              <div className="py-4 border-b border-border/50">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm font-medium">Default Exchange</Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Used for new signals when exchange is not specified
                    </p>
                  </div>
                  <Select
                    value={settings.default_exchange}
                    onValueChange={(v) => setSettings(s => ({ ...s, default_exchange: v }))}
                  >
                    <SelectTrigger className="w-36 bg-card/50 border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="NSE">NSE (Indian Equities)</SelectItem>
                      <SelectItem value="BSE">BSE (Indian Equities)</SelectItem>
                      <SelectItem value="NFO">NFO (F&O)</SelectItem>
                      <SelectItem value="MCX">MCX (Commodities)</SelectItem>
                      <SelectItem value="CRYPTO">CRYPTO</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Product Type */}
              <div className="py-4 border-b border-border/50">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm font-medium">Default Product Type</Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      MIS = intraday (auto-square off), CNC = delivery, NRML = overnight F&O
                    </p>
                  </div>
                  <Select
                    value={settings.default_product_type}
                    onValueChange={(v) => setSettings(s => ({ ...s, default_product_type: v }))}
                  >
                    <SelectTrigger className="w-36 bg-card/50 border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="MIS">MIS (Intraday)</SelectItem>
                      <SelectItem value="CNC">CNC (Delivery)</SelectItem>
                      <SelectItem value="NRML">NRML (Overnight)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Order Type */}
              <div className="py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm font-medium">Default Order Type</Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      MARKET fills instantly at current price. LIMIT waits for your price.
                    </p>
                  </div>
                  <Select
                    value={settings.default_order_type}
                    onValueChange={(v) => setSettings(s => ({ ...s, default_order_type: v }))}
                  >
                    <SelectTrigger className="w-36 bg-card/50 border-border">
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

            {/* ── Risk Management ────────────────────────────────────── */}
            <Card className="p-6 border-border">
              <div className="flex items-center gap-2 mb-5">
                <Shield className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-semibold">Risk Management</h2>
              </div>

              {/* Risk per trade */}
              <div className="py-4 border-b border-border/50">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <Label className="text-sm font-medium">Risk Per Trade</Label>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger>
                            <Info className="w-3.5 h-3.5 text-muted-foreground" />
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs">
                            Maximum % of your available capital to risk on a single trade. Used for auto position sizing.
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      % of capital per trade for auto position sizing
                    </p>
                  </div>
                  <Badge variant="outline" className="border-accent text-accent font-mono">
                    {settings.risk_per_trade_pct}%
                  </Badge>
                </div>
                <Slider
                  min={0.5}
                  max={5}
                  step={0.5}
                  value={[settings.risk_per_trade_pct]}
                  onValueChange={([v]) => setSettings(s => ({ ...s, risk_per_trade_pct: v }))}
                  className="cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                  <span>0.5% (conservative)</span>
                  <span>5% (aggressive)</span>
                </div>
              </div>

              {/* Max open positions */}
              <div className="py-4 border-b border-border/50">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <Label className="text-sm font-medium">Max Open Positions</Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Block new orders when this many positions are open
                    </p>
                  </div>
                  <Badge variant="outline" className="border-accent text-accent font-mono">
                    {settings.max_open_positions}
                  </Badge>
                </div>
                <Slider
                  min={1}
                  max={20}
                  step={1}
                  value={[settings.max_open_positions]}
                  onValueChange={([v]) => setSettings(s => ({ ...s, max_open_positions: v }))}
                  className="cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                  <span>1</span>
                  <span>20</span>
                </div>
              </div>

              {/* Daily loss limit */}
              <div className="py-4">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <Label className="text-sm font-medium">Daily Loss Limit</Label>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger>
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs">
                            All trading halts automatically for the day when your P&L drops below -X% of your capital. Resets at midnight.
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Halt all trading when daily loss exceeds this %
                    </p>
                  </div>
                  <Badge variant="outline" className="border-destructive text-destructive font-mono">
                    -{settings.daily_loss_limit_pct}%
                  </Badge>
                </div>
                <Slider
                  min={1}
                  max={20}
                  step={1}
                  value={[settings.daily_loss_limit_pct]}
                  onValueChange={([v]) => setSettings(s => ({ ...s, daily_loss_limit_pct: v }))}
                  className="cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                  <span>-1% (very tight)</span>
                  <span>-20% (very loose)</span>
                </div>
              </div>
            </Card>

            {/* ── Risk Warning ──────────────────────────────────────── */}
            {settings.auto_execute && (
              <Card className="p-4 border-destructive/20 bg-destructive/5 border">
                <div className="flex gap-3">
                  <AlertTriangle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-semibold text-destructive mb-1">Auto-Execute is ON</p>
                    <p className="text-xs text-muted-foreground">
                      Signals above {settings.min_signal_confidence}% confidence will be automatically
                      placed as {settings.default_order_type} orders using {settings.default_product_type} product type.
                      Maximum {settings.max_open_positions} concurrent positions.
                      Daily loss cap: -{settings.daily_loss_limit_pct}%.
                      Ensure your broker API key has trade permissions enabled.
                    </p>
                  </div>
                </div>
              </Card>
            )}

            {/* ── Current config summary ────────────────────────────── */}
            <Card className="p-5 border-border bg-card/30">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-4 h-4 text-accent" />
                <h3 className="text-sm font-semibold">Active Configuration</h3>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                {[
                  { label: 'Exchange', value: settings.default_exchange },
                  { label: 'Product', value: settings.default_product_type },
                  { label: 'Order', value: settings.default_order_type },
                  { label: 'Auto-Execute', value: settings.auto_execute ? 'ON' : 'OFF', warn: settings.auto_execute },
                ].map(item => (
                  <div key={item.label} className="p-3 rounded-lg bg-card/50 border border-border">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">{item.label}</p>
                    <p className={`text-sm font-semibold ${item.warn ? 'text-rose-500' : ''}`}>{item.value}</p>
                  </div>
                ))}
              </div>
            </Card>

            {/* Save Button */}
            <div className="flex justify-end pb-8">
              <Button
                onClick={handleSave}
                disabled={saving}
                size="lg"
                className="gap-2 min-w-[160px]"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : saved ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    Saved
                  </>
                ) : (
                  'Save Settings'
                )}
              </Button>
            </div>
          </>
        )}
      </div>
    </main>
  )
}
