'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Check, AlertCircle, Loader2, ChevronRight, ExternalLink, Lock, Key } from 'lucide-react'
import { PLATFORM, API_CONFIG } from '@/lib/api-config'
import { useAuth } from '@/hooks/useAuth'

type Step = 'broker' | 'credentials' | 'connecting'
type AuthType = 'api_key' | 'oauth' | 'totp'

interface Broker {
  id: string
  name: string
  logo: string
  exchanges: string[]
  authType: AuthType
  authLabel: string
  /** Human guidance text shown on the credential form */
  helpText: string
  /** Extra fields beyond apiKey/apiSecret this broker requires */
  extraFields?: Array<{ key: string; label: string; type: string; placeholder: string }>
}

const brokers: Broker[] = [
  // ── OAuth brokers ──
  {
    id: 'zerodha', name: 'Zerodha', logo: '🚀', exchanges: ['NSE', 'NFO', 'BSE', 'CDS'],
    authType: 'oauth', authLabel: 'OAuth', helpText: 'Enter your Zerodha Client ID (from Kite Connect → API)',
  },
  {
    id: 'upstox', name: 'Upstox', logo: '⚡', exchanges: ['NSE', 'NFO', 'BSE', 'MCX'],
    authType: 'oauth', authLabel: 'OAuth', helpText: 'Enter your Upstox Client ID from the Upstox Developer Portal',
  },
  {
    id: 'fyers', name: 'Fyers', logo: '📊', exchanges: ['NSE', 'NFO', 'BSE', 'MCX'],
    authType: 'oauth', authLabel: 'OAuth', helpText: 'Enter your Fyers App ID from the Fyers API dashboard',
  },
  {
    id: 'dhan', name: 'Dhan', logo: '💰', exchanges: ['NSE', 'NFO', 'BSE'],
    authType: 'oauth', authLabel: 'OAuth', helpText: 'Enter your Dhan Client ID from the Dhan Developer portal',
  },
  {
    id: 'aliceblue', name: 'Alice Blue', logo: '🔵', exchanges: ['NSE', 'NFO', 'BSE', 'MCX'],
    authType: 'oauth', authLabel: 'OAuth', helpText: 'Enter your Alice Blue App Code from the Alice Blue console',
  },
  {
    id: 'groww', name: 'Groww', logo: '🌱', exchanges: ['NSE', 'NFO'],
    authType: 'oauth', authLabel: 'OAuth', helpText: 'Enter your Groww App Key from the Groww dev portal',
  },
  // ── TOTP brokers ──
  {
    id: 'angelone', name: 'Angel One', logo: '👼', exchanges: ['NSE', 'NFO', 'BSE', 'MCX'],
    authType: 'totp', authLabel: 'TOTP + PIN', helpText: 'Enter your Angel One credentials',
    extraFields: [
      { key: 'totp', label: 'TOTP Code', type: 'text', placeholder: '6-digit TOTP from your authenticator app' },
    ],
  },
  {
    id: 'kotak', name: 'Kotak', logo: '🏦', exchanges: ['NSE', 'NFO', 'BSE'],
    authType: 'totp', authLabel: 'TOTP + MPIN', helpText: 'Enter your Kotak Neo credentials',
    extraFields: [
      { key: 'mobile', label: 'Mobile Number', type: 'tel', placeholder: 'Registered mobile number' },
    ],
  },
  // ── API Key brokers ──
  {
    id: 'binance', name: 'Binance', logo: '₿', exchanges: ['CRYPTO'],
    authType: 'api_key', authLabel: 'API Key', helpText: 'Create an API key in Binance Account → API Management',
  },
  {
    id: 'bybit', name: 'Bybit', logo: '🔷', exchanges: ['CRYPTO'],
    authType: 'api_key', authLabel: 'API Key', helpText: 'Create an API key in Bybit Account → API Management',
  },
]

/**
 * Construct the broker's OAuth initiation URL or callback URL.
 * For OAuth brokers, this is the URL the user will be redirected to.
 * For API-key/TOTP brokers, this is the Platform's callback URL.
 */
function getAuthUrl(
  broker: Broker,
  apiKey: string,
  apiSecret: string,
  platformBase: string,
): string {
  if (broker.authType === 'api_key' || broker.authType === 'totp') {
    // API-key and TOTP brokers authenticate via the Platform's callback
    return `${platformBase}/${broker.id}/callback`
  }

  // OAuth brokers — construct the broker's OAuth login URL
  const platformCallback = `${platformBase}/${broker.id}/callback`

  switch (broker.id) {
    case 'zerodha':
      // Kite Connect OAuth: client_id=api_key&redirect_uri=...
      return `https://kite.trade/connect/login?api_key=${apiKey}&v=3&redirect_uri=${encodeURIComponent(platformCallback)}`

    case 'upstox':
      // Upstox OAuth
      return `https://api.upstox.com/v2/login/authorization/dialog?client_id=${apiKey}&redirect_uri=${encodeURIComponent(platformCallback)}&response_type=code`

    case 'fyers':
      // Fyers OAuth: client_id and redirect_uri
      return `https://api.fyers.in/api/v2/generate-authcode?client_id=${apiKey}&redirect_uri=${encodeURIComponent(platformCallback)}&response_type=code&state=silvertrade`

    case 'dhan':
      // Dhan OAuth is initiated by the Platform at /dhan/initiate-oauth
      return `${platformBase}/dhan/initiate-oauth`

    case 'aliceblue':
      // AliceBlue: appcode is the API key
      return `https://ant.aliceblueonline.com/?appcode=${apiKey}`

    default:
      // Generic fallback: try Platform callback (may redirect to broker's login)
      return `${platformBase}/${broker.id}/callback`
  }
}

export default function SetupPage() {
  const router = useRouter()
  const { apiKey: userApiKey } = useAuth()
  const [step, setStep] = useState<Step>('broker')
  const [selectedBroker, setSelectedBroker] = useState<Broker | null>(null)
  const [credentials, setCredentials] = useState<Record<string, string>>({ apiKey: '', apiSecret: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // If already has broker connected, redirect to dashboard
  if (userApiKey) {
    router.push('/dashboard')
  }

  const handleBrokerSelect = (broker: Broker) => {
    setSelectedBroker(broker)
    setError(null)
    setCredentials({ apiKey: '', apiSecret: '' })
    setStep('credentials')
  }

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedBroker) return
    setLoading(true)
    setError(null)

    const platformBase = API_CONFIG.PLATFORM_BASE.replace(/\/+$/, '')
    const authUrl = getAuthUrl(selectedBroker, credentials.apiKey, credentials.apiSecret, platformBase)

    try {
      // Build the payload for POST /api/broker/credentials
      const body: Record<string, string> = {
        redirect_url: `${platformBase}/${selectedBroker.id}/callback`,
      }

      if (credentials.apiKey) body.broker_api_key = credentials.apiKey
      if (credentials.apiSecret) body.broker_api_secret = credentials.apiSecret

      // Save to .env
      const response = await fetch(PLATFORM('/api/broker/credentials'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      })

      const data = await response.json()
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Failed to save credentials')
      }

      // Show connecting state while redirecting (URL already computed)
      setStep('connecting')
      window.location.href = authUrl
    } catch (err: any) {
      setError(err.message || 'Connection failed')
      setLoading(false)
    }
  }

  // ── Connecting / Redirecting screen ──
  if (step === 'connecting' && selectedBroker) {
    const isOAuth = selectedBroker.authType === 'oauth'

    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-lg border-border">
          <CardContent className="p-12 text-center">
            <div className="text-6xl mb-4">{selectedBroker.logo}</div>
            <Loader2 className="w-8 h-8 animate-spin text-accent mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              {isOAuth
                ? `Redirecting to ${selectedBroker.name}...`
                : `Connecting to ${selectedBroker.name}...`}
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              {isOAuth
                ? 'You will be redirected to complete authentication with your broker.'
                : 'The broker callback is being processed. Please wait...'}
            </p>
            {error && (
              <div className="flex items-center gap-2 text-destructive text-sm p-3 rounded-lg bg-destructive/5 border border-destructive/20 text-left mb-4">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}
            {!error && (
              <div className="flex items-center justify-center gap-2 p-3 rounded-lg bg-accent/5 border border-accent/20 text-xs text-accent">
                <ExternalLink className="w-4 h-4" />
                <span>If not redirected,{' '}
                  <button
                    onClick={() => {
                      const platformBase = API_CONFIG.PLATFORM_BASE.replace(/\/+$/, '')
                      window.location.href = getAuthUrl(selectedBroker, credentials.apiKey || '', credentials.apiSecret || '', platformBase)
                    }}
                    className="underline hover:no-underline"
                  >
                    click here
                  </button>
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl border-border">
        <CardHeader>
          <CardTitle className="text-2xl">Connect Your Broker</CardTitle>
          <CardDescription>
            {step === 'broker'
              ? 'Select your broker to get started'
              : `Enter your ${selectedBroker?.name} credentials`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Step 1: Choose Broker */}
          {step === 'broker' && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Choose your broker. You&apos;ll need an API key from your broker&apos;s developer portal.
              </p>

              <div className="mb-4">
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                  Indian Brokers
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {brokers.filter(b => !b.exchanges.includes('CRYPTO')).map((broker) => (
                    <BrokerCard
                      key={broker.id}
                      broker={broker}
                      onClick={() => handleBrokerSelect(broker)}
                    />
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                  Crypto Brokers
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {brokers.filter(b => b.exchanges.includes('CRYPTO')).map((broker) => (
                    <BrokerCard
                      key={broker.id}
                      broker={broker}
                      onClick={() => handleBrokerSelect(broker)}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Enter Credentials */}
          {step === 'credentials' && selectedBroker && (
            <form onSubmit={handleCredentialsSubmit} className="space-y-4">
              <div className="flex items-center gap-3 mb-4 p-4 rounded-lg bg-card/50 border border-border">
                <div className="text-3xl">{selectedBroker.logo}</div>
                <div>
                  <div className="font-semibold">{selectedBroker.name}</div>
                  <Badge variant="outline" className="text-[10px] mt-1 flex items-center gap-1 w-fit">
                    {selectedBroker.authType === 'oauth' ? <ExternalLink className="w-3 h-3" /> :
                     selectedBroker.authType === 'totp' ? <Lock className="w-3 h-3" /> :
                     <Key className="w-3 h-3" />}
                    {selectedBroker.authLabel}
                  </Badge>
                </div>
              </div>

              <p className="text-sm text-muted-foreground bg-card/30 p-3 rounded-lg border border-border">
                {selectedBroker.helpText}
              </p>

              {selectedBroker.authType === 'oauth' && (
                <div className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/20 text-sm text-blue-600 dark:text-blue-400">
                  <strong>OAuth Broker:</strong> You&apos;ll be redirected to {selectedBroker.name}&apos;s
                  login page after saving. Enter your <strong>Client ID</strong> (not your trading password)
                  below.
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="apiKey">
                  {selectedBroker.authType === 'oauth' ? 'Client ID / API Key' : 'API Key'}
                </Label>
                <Input
                  id="apiKey"
                  type="password"
                  value={credentials.apiKey}
                  onChange={(e) => setCredentials({ ...credentials, apiKey: e.target.value })}
                  placeholder={`Your ${selectedBroker.name} ${selectedBroker.authType === 'oauth' ? 'Client ID' : 'API key'}`}
                  required
                />
              </div>

              {selectedBroker.authType !== 'oauth' && (
                <div className="space-y-2">
                  <Label htmlFor="apiSecret">API Secret</Label>
                  <Input
                    id="apiSecret"
                    type="password"
                    value={credentials.apiSecret}
                    onChange={(e) => setCredentials({ ...credentials, apiSecret: e.target.value })}
                    placeholder={`Your ${selectedBroker.name} API secret`}
                    required
                  />
                </div>
              )}

              {/* Broker-specific extra fields */}
              {selectedBroker.extraFields?.map((field) => (
                <div key={field.key} className="space-y-2">
                  <Label htmlFor={field.key}>{field.label}</Label>
                  <Input
                    id={field.key}
                    type={field.type}
                    value={credentials[field.key] || ''}
                    onChange={(e) => setCredentials({ ...credentials, [field.key]: e.target.value })}
                    placeholder={field.placeholder}
                  />
                </div>
              ))}

              {error && (
                <div className="flex items-center gap-2 text-destructive text-sm p-3 rounded-lg bg-destructive/5 border border-destructive/20">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => { setStep('broker'); setError(null) }}
                  disabled={loading}
                  className="flex-1"
                >
                  Back
                </Button>
                <Button type="submit" disabled={loading} className="flex-1">
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      {selectedBroker.authType === 'oauth' ? <ExternalLink className="w-4 h-4 mr-2" /> : <Lock className="w-4 h-4 mr-2" />}
                      Connect
                    </>
                  )}
                </Button>
              </div>

              <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20">
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  <strong>Security Note:</strong> Your API keys are encrypted and stored securely.
                  We only use them to place trades on your behalf.
                </p>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

/** A single broker selection card with auth type badge */
function BrokerCard({ broker, onClick }: { broker: Broker; onClick: () => void }) {
  const authBadgeColor =
    broker.authType === 'oauth'
      ? 'bg-blue-500/10 text-blue-500 border-blue-500/20'
      : broker.authType === 'totp'
        ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
        : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'

  const authIcon =
    broker.authType === 'oauth'
      ? <ExternalLink className="w-3 h-3" />
      : broker.authType === 'totp'
        ? <Lock className="w-3 h-3" />
        : <Key className="w-3 h-3" />

  return (
    <button
      onClick={onClick}
      className="p-4 rounded-lg border border-border hover:border-accent hover:bg-accent/5 transition-all text-left group"
    >
      <div className="text-3xl mb-2">{broker.logo}</div>
      <div className="font-medium text-sm group-hover:text-accent transition-colors">{broker.name}</div>
      <div className="text-xs text-muted-foreground mt-1">
        {broker.exchanges.join(', ')}
      </div>
      <Badge variant="outline" className={`text-[10px] px-1.5 py-0 mt-2 flex items-center gap-1 ${authBadgeColor}`}>
        {authIcon}
        {broker.authLabel}
      </Badge>
    </button>
  )
}
