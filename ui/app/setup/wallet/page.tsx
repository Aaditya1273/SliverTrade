'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ArrowRight, Copy, Check, AlertCircle } from 'lucide-react'

export default function WalletSetupPage() {
  const [activeTab, setActiveTab] = useState<'exchange' | 'wallet'>('exchange')
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [copied, setCopied] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopied(id)
    setTimeout(() => setCopied(null), 2000)
  }

  const handleConnectExchange = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    // TODO: Implement exchange connection
    setTimeout(() => {
      setLoading(false)
      // Navigate to dashboard after connection
    }, 1500)
  }

  const supportedExchanges = [
    { name: 'Binance', logo: '📊' },
    { name: 'Kraken', logo: '🔐' },
    { name: 'Coinbase', logo: '💰' },
    { name: 'FTX', logo: '⚡' },
  ]

  const supportedWallets = [
    { name: 'MetaMask', logo: '🦊' },
    { name: 'Phantom', logo: '👻' },
    { name: 'WalletConnect', logo: '🔗' },
    { name: 'Ledger', logo: '🔒' },
  ]

  return (
    <main className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <nav className="border-b border-border px-4 sm:px-6 lg:px-8 h-16 flex items-center">
        <Link href="/" className="text-xl font-bold tracking-tight hover:text-muted-foreground transition-colors">
          SilverTrade
        </Link>
      </nav>

      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Progress Indicator */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Connect Your Accounts</h1>
          <p className="text-muted-foreground">Link your exchange or wallet to start receiving AI signals</p>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'exchange' | 'wallet')} className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-8">
            <TabsTrigger value="exchange">Exchange Connection</TabsTrigger>
            <TabsTrigger value="wallet">Web3 Wallet</TabsTrigger>
          </TabsList>

          {/* Exchange Tab */}
          <TabsContent value="exchange" className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold mb-4">Select Your Exchange</h2>
              <div className="grid grid-cols-2 gap-4 mb-6">
                {supportedExchanges.map((exchange) => (
                  <button
                    key={exchange.name}
                    className="p-4 rounded-lg border border-border hover:border-accent/30 bg-card/50 hover:bg-card/70 transition-all group"
                  >
                    <div className="text-3xl mb-2">{exchange.logo}</div>
                    <p className="font-medium group-hover:text-accent transition-colors">{exchange.name}</p>
                  </button>
                ))}
              </div>
            </div>

            <form onSubmit={handleConnectExchange} className="space-y-4">
              <div className="p-4 rounded-lg bg-accent/10 border border-accent/20 flex gap-3">
                <AlertCircle className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-accent mb-1">Read-only Access</p>
                  <p className="text-muted-foreground">
                    Your API keys are encrypted and we never withdraw funds. View-only permissions recommended.
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="apiKey" className="text-sm font-medium">API Key</Label>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder="Paste your API key here"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                  required
                />
                <p className="text-xs text-muted-foreground">
                  <Link href="#" className="text-accent hover:text-accent/80">Learn how to create API keys →</Link>
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="apiSecret" className="text-sm font-medium">API Secret</Label>
                <Input
                  id="apiSecret"
                  type="password"
                  placeholder="Paste your API secret here"
                  value={apiSecret}
                  onChange={(e) => setApiSecret(e.target.value)}
                  className="bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
                  required
                />
              </div>

              <Button type="submit" className="w-full gap-2" disabled={loading}>
                {loading ? 'Connecting...' : 'Connect Exchange'} {!loading && <ArrowRight className="w-5 h-5" />}
              </Button>
            </form>

            <div className="p-4 rounded-lg bg-card/50 border border-border space-y-2">
              <h3 className="font-medium text-sm">Tips for Security</h3>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>✓ Create a sub-account with view-only permissions</li>
                <li>✓ Never share your secret key with anyone</li>
                <li>✓ Use IP whitelist if available</li>
                <li>✓ We never store keys in plain text</li>
              </ul>
            </div>
          </TabsContent>

          {/* Wallet Tab */}
          <TabsContent value="wallet" className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold mb-4">Connect Your Web3 Wallet</h2>
              <div className="grid grid-cols-2 gap-4 mb-6">
                {supportedWallets.map((wallet) => (
                  <button
                    key={wallet.name}
                    className="p-4 rounded-lg border border-border hover:border-accent/30 bg-card/50 hover:bg-card/70 transition-all group"
                  >
                    <div className="text-3xl mb-2">{wallet.logo}</div>
                    <p className="font-medium group-hover:text-accent transition-colors">{wallet.name}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="p-4 rounded-lg bg-accent/10 border border-accent/20">
              <p className="text-sm text-muted-foreground">
                Web3 wallet integration allows you to trade directly from your wallet while keeping full control of your assets. A transaction will appear in your wallet to verify ownership.
              </p>
            </div>

            <Button className="w-full gap-2">
              Connect Wallet <ArrowRight className="w-5 h-5" />
            </Button>

            <div className="space-y-3">
              <h3 className="font-medium text-sm">What happens next:</h3>
              <ol className="text-sm text-muted-foreground space-y-2">
                <li className="flex gap-3">
                  <span className="font-bold text-accent flex-shrink-0">1</span>
                  <span>Your wallet extension opens to confirm the connection</span>
                </li>
                <li className="flex gap-3">
                  <span className="font-bold text-accent flex-shrink-0">2</span>
                  <span>You approve a small verification transaction</span>
                </li>
                <li className="flex gap-3">
                  <span className="font-bold text-accent flex-shrink-0">3</span>
                  <span>SilverTrade receives your wallet address securely</span>
                </li>
              </ol>
            </div>
          </TabsContent>
        </Tabs>

        {/* Footer CTA */}
        <div className="mt-12 pt-8 border-t border-border text-center">
          <p className="text-sm text-muted-foreground mb-4">
            Want to skip setup and explore the dashboard first?
          </p>
          <Link href="/dashboard" className="text-accent hover:text-accent/80 font-medium transition-colors">
            Take a guided tour →
          </Link>
        </div>
      </div>
    </main>
  )
}
