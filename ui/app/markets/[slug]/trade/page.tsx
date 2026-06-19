'use client'

import { useState, useMemo } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { COINS, type Signal } from '@/lib/market-data'
import CryptoIcon from '@/components/CryptoIcon'
import { formatCompact, formatPrice, pctColor } from '@/lib/market-utils'
import {
  Search, TrendingUp, Sparkles, AlertTriangle, BarChart3,
  Bell, Bookmark, Activity, Brain, Menu, X, Wallet, Eye,
  ChevronDown, Clock, ArrowUpRight, Zap,
  Settings, Star, History,
} from 'lucide-react'

// ── Mock Order Book Data ──────────────────────────────────────────────

function generateOrderBook(price: number) {
  const asks: { price: number; amount: number; total: number }[] = []
  const bids: { price: number; amount: number; total: number }[] = []
  let askP = price * 1.001
  let bidP = price * 0.999
  for (let i = 0; i < 12; i++) {
    const aAmt = +(Math.random() * (0.1 + i * 0.02) + 0.01).toFixed(4)
    const bAmt = +(Math.random() * (0.1 + i * 0.02) + 0.01).toFixed(4)
    asks.push({ price: +askP.toFixed(2), amount: aAmt, total: +(aAmt * askP).toFixed(2) })
    bids.push({ price: +bidP.toFixed(2), amount: bAmt, total: +(bAmt * bidP).toFixed(2) })
    askP *= 1.0008
    bidP *= 0.9992
  }
  // Calculate max total for depth bars
  const maxAsk = Math.max(...asks.map(a => a.total), 1)
  const maxBid = Math.max(...bids.map(b => b.total), 1)
  return {
    asks: asks.map(a => ({ ...a, depthPct: (a.total / maxAsk) * 100 })),
    bids: bids.map(b => ({ ...b, depthPct: (b.total / maxBid) * 100 })),
    spread: +((asks[0].price - bids[0].price) / asks[0].price * 100).toFixed(3),
  }
}

// ── Candlestick generator ──────────────────────────────────────────────

function generateCandles(base: number, count: number) {
  const candles: { open: number; high: number; low: number; close: number; time: number }[] = []
  let price = base * 0.95
  for (let i = 0; i < count; i++) {
    const open = price
    const close = open * (1 + (Math.random() - 0.48) * 0.03)
    const high = Math.max(open, close) * (1 + Math.random() * 0.012)
    const low = Math.min(open, close) * (1 - Math.random() * 0.012)
    candles.push({ open, high, low, close, time: i })
    price = close
  }
  return candles
}

// ── Main Component ────────────────────────────────────────────────────

export default function TradePage() {
  const params = useParams()
  const slug = (params?.slug as string)?.toUpperCase() || 'BTC'
  const coin = COINS.find(c => c.symbol === slug) || COINS[0]

  // ── State ──
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [chartTimeframe, setChartTimeframe] = useState<string>('1h')
  const [chartIndicator, setChartIndicator] = useState<string | null>(null)
  const [orderTab, setOrderTab] = useState<'Market' | 'Limit' | 'Stop Limit' | 'DCA'>('Market')
  const [tradeSide, setTradeSide] = useState<'buy' | 'sell'>('buy')
  const [orderPrice, setOrderPrice] = useState(coin.price.toFixed(2))
  const [orderAmount, setOrderAmount] = useState('')
  const [orderTotal, setOrderTotal] = useState('')
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [authMode, setAuthMode] = useState<'signin' | 'signup' | 'wallet' | 'exchange'>('signin')
  const [expandedSidebar, setExpandedSidebar] = useState<'watchlist' | 'positions' | 'trending' | 'recent' | null>('watchlist')

  const signalColors: Record<Signal, string> = { BUY: '#16a34a', SELL: '#dc2626', WAIT: '#d97706' }
  const candles = useMemo(() => generateCandles(coin.price, 120), [coin.price])
  const orderBook = useMemo(() => generateOrderBook(coin.price), [coin.price])
  const timeframes = ['1m', '5m', '15m', '1h', '4h', '1D', '1W']

  // ── Handlers ──
  const handleAmountSlider = (pct: number) => {
    const amt = ((pct / 100) * 1000).toFixed(4)
    setOrderAmount(amt)
    setOrderTotal((+amt * coin.price).toFixed(2))
  }

  const handleAmountChange = (val: string) => {
    setOrderAmount(val)
    setOrderTotal(val ? (+val * coin.price).toFixed(2) : '')
  }

  const handleTotalChange = (val: string) => {
    setOrderTotal(val)
    setOrderAmount(val ? (+val / coin.price).toFixed(4) : '')
  }

  const handleConfirmTrade = () => {
    setShowAuthModal(true)
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#F4F1EA' }}>
      {/* ═══════════ TOP NAV ═══════════ */}
      <header className="sticky top-0 z-50 border-b" style={{ backgroundColor: '#F4F1EA', borderColor: '#D9D3C5' }}>
        <div className="w-full px-3 lg:px-4" style={{ maxWidth: 1800, margin: '0 auto' }}>
          <div className="flex items-center justify-between h-12">
            <Link href="/" className="flex items-center gap-2 shrink-0">
              <span className="text-lg font-bold tracking-tight" style={{ fontFamily: "'Archivo Black', sans-serif" }}>
                <span className="text-black">SILVER</span><span className="text-[#E25A2B]">TRADE</span>
              </span>
            </Link>
            <nav className="hidden lg:flex items-center gap-0.5">              {[{ href: '/markets', label: 'Markets', icon: BarChart3 }, { href: '/dashboard', label: 'Profile', icon: Eye },
                { href: '/dashboard', label: 'Portfolio', icon: Wallet },
                { href: '/dashboard/watchlist', label: 'Watchlist', icon: Bookmark },
                { href: '/dashboard/chat', label: 'AI Signals', icon: Brain },
                { href: '/dashboard/settings/alerts', label: 'Alerts', icon: Bell },
              ].map(item => {
                const Icon = item.icon
                return (
                  <Link key={item.href} href={item.href}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors"
                    style={{ color: '#6B6760' }}>
                    <Icon className="w-3.5 h-3.5" />{item.label}
                  </Link>
                )
              })}
            </nav>
            <div className="flex items-center gap-2">
              <div className="hidden sm:block relative w-40 lg:w-52">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5" style={{ color: '#6B6760' }} />
                <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search..."
                  className="w-full pl-8 pr-2.5 py-1.5 text-xs rounded-lg outline-none"
                  style={{ backgroundColor: '#E6E1D6', color: '#0E0E0C' }} />
              </div>
              <Link href="/login" className="px-3 py-1.5 text-xs font-medium rounded-md" style={{ color: '#6B6760' }}>Sign In</Link>
              <Link href="/signup" className="px-3 py-1.5 text-xs font-semibold rounded-md text-white" style={{ backgroundColor: '#0E0E0C' }}>Get Started</Link>
              <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="lg:hidden p-1.5 rounded-md hover:bg-black/5">
                {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ═══════════ ASSET HEADER ═══════════ */}
      <div className="border-b" style={{ borderColor: '#D9D3C5', backgroundColor: '#F4F1EA' }}>
        <div className="w-full px-3 lg:px-4" style={{ maxWidth: 1800, margin: '0 auto' }}>
          <div className="flex items-center gap-4 h-11 overflow-x-auto">
            <Link href={`/markets/${coin.symbol.toLowerCase()}`} className="flex items-center gap-2 shrink-0">
              <CryptoIcon symbol={coin.symbol} size={24} />
              <span className="text-sm font-bold">{coin.symbol}/USDT</span>
            </Link>
            <div className="text-right shrink-0">
              <div className="text-base font-bold tracking-tight">{formatPrice(coin.price)}</div>
            </div>
            <span className="text-xs font-medium shrink-0" style={{ color: pctColor(coin.change24h) }}>
              {coin.change24h >= 0 ? '+' : ''}{coin.change24h.toFixed(2)}%
            </span>
            <div className="w-px h-5 shrink-0" style={{ backgroundColor: '#D9D3C5' }} />
            <div className="flex items-center gap-1.5 shrink-0">
              <Sparkles className="w-3 h-3 text-[#E25A2B]" />
              <span className="text-[10px] uppercase tracking-wider font-semibold text-[#E25A2B]">AI</span>
              <span className="text-xs font-bold" style={{ color: signalColors[coin.aiSignal] }}>{coin.aiSignal}</span>
              <span className="text-[10px] font-mono" style={{ color: '#6B6760' }}>{coin.confidence}%</span>
            </div>
            <div className="w-px h-5 shrink-0" style={{ backgroundColor: '#D9D3C5' }} />
            <span className="text-[10px]" style={{ color: '#6B6760' }}>24h Vol: {formatCompact(coin.volume24h)}</span>
            <div className="w-px h-5 shrink-0" style={{ backgroundColor: '#D9D3C5' }} />
            <span className="text-[10px]" style={{ color: '#6B6760' }}>MCap: {formatCompact(coin.marketCap)}</span>
            <div className="flex-1 min-w-4" />
            {/* Star / bookmark */}
            <button className="p-1 rounded hover:bg-black/5 shrink-0">
              <Star className="w-3.5 h-3.5" style={{ color: '#6B6760' }} />
            </button>
          </div>
        </div>
      </div>

      {/* ═══════════ 3-COLUMN LAYOUT ═══════════ */}
      <div className="w-full px-3 lg:px-4 py-3" style={{ maxWidth: 1800, margin: '0 auto' }}>
        <div className="flex gap-3">

          {/* ─── LEFT SIDEBAR ─── */}
          <div className="hidden lg:block w-[220px] shrink-0 space-y-2">
            {/* Watchlist */}
            <SidebarSection
              title="Watchlist"
              icon={Bookmark}
              isOpen={expandedSidebar === 'watchlist'}
              onClick={() => setExpandedSidebar(expandedSidebar === 'watchlist' ? null : 'watchlist')}
            >
              {['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOT', 'AVAX', 'LINK'].map(sym => {
                const c = COINS.find(x => x.symbol === sym)
                if (!c) return null
                return (
                  <Link key={sym} href={`/markets/${sym.toLowerCase()}/trade`}
                    className="flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors hover:bg-black/[0.03]"
                    style={{ backgroundColor: sym === coin.symbol ? 'rgba(226,90,43,0.08)' : 'transparent' }}>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{sym}</span>
                    </div>
                    <div className="text-right">
                      <div className="font-medium text-[11px]" style={{ color: pctColor(c.change24h) }}>
                        {c.change24h >= 0 ? '+' : ''}{c.change24h.toFixed(2)}%
                      </div>
                    </div>
                  </Link>
                )
              })}
            </SidebarSection>

            {/* Trending */}
            <SidebarSection
              title="Trending"
              icon={TrendingUp}
              isOpen={expandedSidebar === 'trending'}
              onClick={() => setExpandedSidebar(expandedSidebar === 'trending' ? null : 'trending')}
            >
              {[...COINS].sort((a, b) => b.change24h - a.change24h).slice(0, 5).map(c => (
                <Link key={c.symbol} href={`/markets/${c.symbol.toLowerCase()}/trade`}
                  className="flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors hover:bg-black/[0.03]">
                  <div className="flex items-center gap-2">
                    <CryptoIcon symbol={c.symbol} size={16} />
                    <span className="font-medium">{c.symbol}</span>
                  </div>
                  <div className="text-right">
                    <div className="font-medium text-[11px]" style={{ color: pctColor(c.change24h) }}>
                      +{c.change24h.toFixed(2)}%
                    </div>
                  </div>
                </Link>
              ))}
            </SidebarSection>

            {/* Recently Viewed */}
            <SidebarSection
              title="Recently Viewed"
              icon={History}
              isOpen={expandedSidebar === 'recent'}
              onClick={() => setExpandedSidebar(expandedSidebar === 'recent' ? null : 'recent')}
            >
              {[{ sym: 'ETH', pct: 1.82 }, { sym: 'SOL', pct: 6.71 }, { sym: 'AVAX', pct: 8.92 }].map((item, i) => {
                const c = COINS.find(x => x.symbol === item.sym)
                if (!c) return null
                return (
                  <Link key={item.sym} href={`/markets/${item.sym.toLowerCase()}/trade`}
                    className="flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors hover:bg-black/[0.03]">
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] font-mono" style={{ color: '#6B6760' }}>{i + 1}</span>
                      <CryptoIcon symbol={c.symbol} size={16} />
                      <span className="font-medium">{item.sym}</span>
                    </div>
                    <span className="font-medium text-[11px]" style={{ color: pctColor(item.pct) }}>
                      {item.pct >= 0 ? '+' : ''}{item.pct.toFixed(2)}%
                    </span>
                  </Link>
                )
              })}
            </SidebarSection>

            {/* Open Positions */}
            <SidebarSection
              title="Positions"
              icon={Wallet}
              isOpen={expandedSidebar === 'positions'}
              onClick={() => setExpandedSidebar(expandedSidebar === 'positions' ? null : 'positions')}
            >
              <div className="px-2.5 py-3 text-center">
                <p className="text-[10px]" style={{ color: '#6B6760' }}>No open positions</p>
                <p className="text-[10px] mt-1" style={{ color: '#6B6760' }}>Connect wallet to trade</p>
              </div>
            </SidebarSection>
          </div>

          {/* ─── CENTER: CHART + AI OVERLAY + TRADE PANEL ─── */}
          <div className="flex-1 min-w-0 space-y-3">

            {/* Chart Container */}
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5', backgroundColor: '#F4F1EA' }}>
              {/* Timeframe + Indicators bar */}
              <div className="flex items-center justify-between px-3 py-1.5 border-b" style={{ borderColor: '#D9D3C5', backgroundColor: '#FAF9F6' }}>
                <div className="flex items-center gap-0.5">
                  {timeframes.map(tf => (
                    <button key={tf} onClick={() => setChartTimeframe(tf)}
                      className={`px-2 py-0.5 text-[10px] font-medium rounded-sm transition-colors ${
                        chartTimeframe === tf ? 'text-white' : 'text-[#6B6760] hover:text-[#0E0E0C]'
                      }`}
                      style={chartTimeframe === tf ? { backgroundColor: '#E25A2B' } : {}}>
                      {tf}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-1">
                  {['RSI', 'MACD', 'EMA', 'BB'].map(ind => (
                    <button key={ind} onClick={() => setChartIndicator(chartIndicator === ind ? null : ind)}
                      className={`px-2 py-0.5 text-[10px] font-medium rounded-sm transition-colors ${
                        chartIndicator === ind ? 'text-white' : 'text-[#6B6760] hover:text-[#0E0E0C]'
                      }`}
                      style={chartIndicator === ind ? { backgroundColor: '#0E0E0C' } : {}}>
                      {ind}
                    </button>
                  ))}
                  <div className="w-px h-3 mx-1" style={{ backgroundColor: '#D9D3C5' }} />
                  <Settings className="w-3 h-3" style={{ color: '#6B6760' }} />
                </div>
              </div>

              {/* Chart Area with AI Overlay */}
              <div className="relative" style={{ height: 400 }}>
                {/* Candlestick SVG chart */}
                <svg width="100%" height="100%" viewBox="0 0 1000 380" preserveAspectRatio="none" className="overflow-visible absolute inset-0">
                  {[0, 95, 190, 285, 380].map(y => (
                    <line key={y} x1="0" y1={y} x2="1000" y2={y} stroke="#E6E1D6" strokeWidth="0.5" />
                  ))}
                  {candles.slice(-80).map((c, i) => {
                    const x = (i / 79) * 980 + 10
                    const allLow = Math.min(...candles.map(cc => cc.low))
                    const allHigh = Math.max(...candles.map(cc => cc.high))
                    const range = allHigh - allLow || 1
                    const highY = 355 - ((c.high - allLow) / range) * 315
                    const lowY = 355 - ((c.low - allLow) / range) * 315
                    const openY = 355 - ((c.open - allLow) / range) * 315
                    const closeY = 355 - ((c.close - allLow) / range) * 315
                    const isUp = c.close >= c.open
                    const color = isUp ? '#16a34a' : '#dc2626'
                    return (
                      <g key={i}>
                        <line x1={x} y1={highY} x2={x} y2={lowY} stroke={color} strokeWidth={0.6} />
                        <rect x={x - 2} y={Math.min(openY, closeY)} width={4} height={Math.max(Math.abs(closeY - openY), 1)} fill={color} rx={0.3} />
                      </g>
                    )
                  })}
                  {/* Volume bars bottom */}
                  {candles.slice(-80).map((c, i) => {
                    const x = (i / 79) * 980 + 10
                    const volH = ((c.high - c.low) / (Math.max(...candles.map(cc => cc.high - cc.low)) || 1)) * 30
                    return (
                      <rect key={`v-${i}`} x={x - 1.5} y={355 - volH} width={3} height={volH}
                        fill={c.close >= c.open ? 'rgba(22,163,74,0.12)' : 'rgba(220,38,38,0.12)'} />
                    )
                  })}
                  {/* Crosshair */}
                  <line x1={500} y1="0" x2={500} y2="380" stroke="#E25A2B" strokeWidth="0.5" strokeDasharray="3,3" opacity={0.2} />
                  <line x1="0" y1={200} x2="1000" y2={200} stroke="#E25A2B" strokeWidth="0.5" strokeDasharray="3,3" opacity={0.2} />
                </svg>

                {/* AI Overlay Panel (positioned over top-right of chart) */}
                <div className="absolute top-2 right-2 rounded-lg border shadow-lg"
                  style={{ borderColor: '#D9D3C5', backgroundColor: 'rgba(15,15,13,0.92)', width: 220 }}>
                  <div className="flex items-center gap-1.5 px-3 py-2 border-b" style={{ borderColor: '#333' }}>
                    <Brain className="w-3 h-3 text-[#E25A2B]" />
                    <span className="text-[9px] font-semibold uppercase tracking-widest text-[#E25A2B]">AI Execution Intelligence</span>
                  </div>
                  <div className="p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px]" style={{ color: '#999' }}>AI Verdict</span>
                      <span className="text-xs font-bold" style={{ color: signalColors[coin.aiSignal] }}>{coin.aiSignal}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px]" style={{ color: '#999' }}>Confidence</span>
                      <div className="flex items-center gap-1.5">
                        <div className="w-12 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: '#222' }}>
                          <div className="h-full rounded-full" style={{ width: `${coin.confidence}%`, backgroundColor: signalColors[coin.aiSignal] }} />
                        </div>
                        <span className="text-[10px] font-mono font-bold" style={{ color: '#F4F1EA' }}>{coin.confidence}%</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px]" style={{ color: '#999' }}>Risk</span>
                      <span className="text-[10px] font-semibold text-orange-400">Medium</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px]" style={{ color: '#999' }}>Expected Upside</span>
                      <span className="text-[10px] font-semibold text-green-400">+12.4%</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px]" style={{ color: '#999' }}>Expected Downside</span>
                      <span className="text-[10px] font-semibold text-red-400">-4.8%</span>
                    </div>
                    <div className="pt-1.5 border-t space-y-1" style={{ borderColor: '#333' }}>
                      <div className="flex items-center justify-between text-[9px]">
                        <span style={{ color: '#666' }}>Rec. Entry</span>
                        <span className="font-medium" style={{ color: '#F4F1EA' }}>${(coin.price * 0.985).toFixed(2)}</span>
                      </div>
                      <div className="flex items-center justify-between text-[9px]">
                        <span style={{ color: '#666' }}>Take Profit</span>
                        <span className="font-medium text-green-400">${(coin.price * 1.12).toFixed(2)}</span>
                      </div>
                      <div className="flex items-center justify-between text-[9px]">
                        <span style={{ color: '#666' }}>Stop Loss</span>
                        <span className="font-medium text-red-400">${(coin.price * 0.96).toFixed(2)}</span>
                      </div>
                    </div>
                    <div className="text-[9px] leading-relaxed pt-1" style={{ color: '#888' }}>
                      <span className="text-[#E25A2B] font-medium">Reason: </span>
                      {coin.aiSignal === 'BUY'
                        ? 'Strong whale accumulation. Support holding at $102k level. RSI bullish crossover.'
                        : coin.aiSignal === 'SELL'
                          ? 'Resistance rejection at $105k. Declining volume. RSI bearish divergence.'
                          : 'Price consolidating. Await break above $103.5k for confirmation.'}
                    </div>
                  </div>
                  <button onClick={handleConfirmTrade}
                    className="w-full py-2.5 text-[10px] font-bold text-white transition-all hover:opacity-90 rounded-b-lg"
                    style={{ backgroundColor: signalColors[coin.aiSignal] }}>
                    Execute {coin.aiSignal === 'BUY' ? 'Buy' : coin.aiSignal === 'SELL' ? 'Sell' : 'Alert'} — {coin.confidence}% Confidence
                  </button>
                </div>

                {/* Top-left price overlay */}
                <div className="absolute top-2 left-3 space-y-0.5">
                  <div className="text-[10px] font-mono" style={{ color: '#6B6760' }}>{coin.symbol}/USDT</div>
                  <div className="text-base font-bold">{formatPrice(coin.price)}</div>
                  <div className="flex items-center gap-2 text-[10px]">
                    <span style={{ color: pctColor(coin.change24h) }}>{coin.change24h >= 0 ? '+' : ''}{coin.change24h.toFixed(2)}%</span>
                    <span style={{ color: '#6B6760' }}>24h</span>
                  </div>
                </div>
              </div>

              {/* RSI indicator panel (when selected) */}
              {chartIndicator === 'RSI' && (
                <div className="h-16 border-t px-3 flex items-center" style={{ borderColor: '#D9D3C5', backgroundColor: '#FAF9F6' }}>
                  <svg width="100%" height="40" viewBox="0 0 800 40" preserveAspectRatio="none">
                    <line x1="0" y1="20" x2="800" y2="20" stroke="#D9D3C5" strokeWidth="0.5" strokeDasharray="2,2" />
                    {candles.slice(-80).map((c, i) => {
                      const x = (i / 79) * 790 + 5
                      const rsiVal = 30 + Math.random() * 40
                      const y = 35 - (rsiVal / 100) * 30
                      return <circle key={i} cx={x} cy={y} r={1} fill={rsiVal > 70 ? '#dc2626' : rsiVal < 30 ? '#16a34a' : '#6B6760'} />
                    })}
                    <text x="5" y="10" fontSize="8" fill="#6B6760">RSI: {coin.trend === 'bullish' ? '62.4' : '38.7'}</text>
                  </svg>
                </div>
              )}
            </div>

            {/* ═══════════ TRADE EXECUTION PANEL ═══════════ */}
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5', backgroundColor: '#F4F1EA' }}>
              {/* Tab bar */}
              <div className="flex border-b" style={{ borderColor: '#D9D3C5' }}>
                {(['Market', 'Limit', 'Stop Limit', 'DCA'] as const).map(tab => (
                  <button key={tab} onClick={() => setOrderTab(tab)}
                    className={`px-4 py-2.5 text-xs font-medium transition-colors relative ${
                      orderTab === tab ? 'text-[#0E0E0C]' : 'text-[#6B6760] hover:text-[#0E0E0C]'
                    }`}>
                    {tab}
                    {orderTab === tab && (
                      <div className="absolute bottom-0 left-2 right-2 h-0.5 rounded-full" style={{ backgroundColor: '#E25A2B' }} />
                    )}
                  </button>
                ))}
                {/* Buy/Sell toggle - aligned right */}
                <div className="flex-1" />
                <div className="flex items-center gap-1 px-3">
                  <button onClick={() => setTradeSide('buy')}
                    className={`px-3 py-1.5 text-[10px] font-bold rounded-md transition-all ${
                      tradeSide === 'buy'
                        ? 'text-white shadow-sm'
                        : 'text-[#6B6760] hover:bg-black/5'
                    }`}
                    style={tradeSide === 'buy' ? { backgroundColor: '#16a34a' } : {}}>
                    Buy
                  </button>
                  <button onClick={() => setTradeSide('sell')}
                    className={`px-3 py-1.5 text-[10px] font-bold rounded-md transition-all ${
                      tradeSide === 'sell'
                        ? 'text-white shadow-sm'
                        : 'text-[#6B6760] hover:bg-black/5'
                    }`}
                    style={tradeSide === 'sell' ? { backgroundColor: '#dc2626' } : {}}>
                    Sell
                  </button>
                </div>
              </div>

              {/* Order form */}
              <div className="p-4">
                <div className="grid grid-cols-1 lg:grid-cols-[1fr_200px] gap-4">
                  {/* Left: Form fields */}
                  <div className="space-y-3">
                    {(orderTab === 'Limit' || orderTab === 'Stop Limit') && (
                      <div>
                        <label className="text-[10px] font-medium mb-1 block" style={{ color: '#6B6760' }}>
                          {orderTab === 'Stop Limit' ? 'Stop Price' : 'Price'}
                        </label>
                        <div className="relative">
                          <input value={orderPrice} onChange={e => setOrderPrice(e.target.value)}
                            className="w-full px-3 py-2 text-xs rounded-lg outline-none font-mono"
                            style={{ backgroundColor: '#E6E1D6', color: '#0E0E0C' }} />
                          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px]" style={{ color: '#6B6760' }}>USDT</span>
                        </div>
                      </div>
                    )}
                    <div>
                      <label className="text-[10px] font-medium mb-1 block" style={{ color: '#6B6760' }}>Amount</label>
                      <div className="relative">
                        <input value={orderAmount} onChange={e => handleAmountChange(e.target.value)} placeholder="0.0000"
                          className="w-full px-3 py-2 text-xs rounded-lg outline-none font-mono"
                          style={{ backgroundColor: '#E6E1D6', color: '#0E0E0C' }} />
                        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px]" style={{ color: '#6B6760' }}>{coin.symbol}</span>
                      </div>
                    </div>
                    {/* Quick amount slider */}
                    <div className="flex items-center gap-1.5">
                      {[25, 50, 75, 100].map(pct => (
                        <button key={pct} onClick={() => handleAmountSlider(pct)}
                          className="flex-1 py-1.5 text-[10px] font-medium rounded-md transition-colors hover:bg-black/10"
                          style={{ backgroundColor: '#E6E1D6', color: '#0E0E0C' }}>
                          {pct}%
                        </button>
                      ))}
                    </div>
                    <div>
                      <label className="text-[10px] font-medium mb-1 block" style={{ color: '#6B6760' }}>Total</label>
                      <div className="relative">
                        <input value={orderTotal} onChange={e => handleTotalChange(e.target.value)} placeholder="0.00"
                          className="w-full px-3 py-2 text-xs rounded-lg outline-none font-mono"
                          style={{ backgroundColor: '#E6E1D6', color: '#0E0E0C' }} />
                        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px]" style={{ color: '#6B6760' }}>USDT</span>
                      </div>
                    </div>

                    {/* Buy/Sell button */}
                    <button onClick={handleConfirmTrade}
                      className="w-full py-3 rounded-lg text-sm font-bold text-white transition-all hover:opacity-90 shadow-sm"
                      style={{ backgroundColor: tradeSide === 'buy' ? '#16a34a' : '#dc2626' }}>
                      {tradeSide === 'buy' ? 'Buy' : 'Sell'} {coin.symbol}
                    </button>
                  </div>

                  {/* Right: AI Assist */}
                  <div className="rounded-lg p-3 border" style={{ borderColor: '#D9D3C5', backgroundColor: '#0E0E0C' }}>
                    <div className="flex items-center gap-1.5 mb-2">
                      <Brain className="w-3 h-3 text-[#E25A2B]" />
                      <span className="text-[9px] font-semibold uppercase tracking-widest text-[#E25A2B]">AI Assist</span>
                    </div>
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[9px]" style={{ color: '#666' }}>Rec. Entry</span>
                        <span className="text-[10px] font-medium" style={{ color: '#F4F1EA' }}>${(coin.price * 0.985).toFixed(2)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[9px]" style={{ color: '#666' }}>Position Size</span>
                        <span className="text-[10px] font-medium" style={{ color: '#F4F1EA' }}>{+(1000 / coin.price).toFixed(4)} {coin.symbol}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[9px]" style={{ color: '#666' }}>Risk</span>
                        <span className="text-[10px] font-medium text-orange-400">Medium</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[9px]" style={{ color: '#666' }}>Est. Probability</span>
                        <span className="text-[10px] font-medium text-green-400">{coin.confidence}%</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[9px]" style={{ color: '#666' }}>Expected Return</span>
                        <span className="text-[10px] font-medium text-green-400">+12.4%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Trades / Order History mini section */}
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5' }}>
              <div className="flex items-center gap-2 px-3 py-2 border-b" style={{ borderColor: '#D9D3C5' }}>
                <Clock className="w-3 h-3" style={{ color: '#6B6760' }} />
                <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#6B6760' }}>Recent Trades</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>
                  <thead>
                    <tr className="text-[9px] uppercase tracking-wider" style={{ color: '#6B6760' }}>
                      {['Price (USDT)', 'Amount', 'Total', 'Time'].map(h => (
                        <th key={h} className="px-3 py-1.5 text-right font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Array.from({ length: 5 }).map((_, i) => {
                      const side = i % 2 === 0 ? 'buy' : 'sell'
                      const change = (Math.random() - 0.5) * 0.002
                      return (
                        <tr key={i} className="text-[11px] font-mono" style={{ borderBottom: i < 4 ? '1px solid' : 'none', borderColor: '#E6E1D6' }}>
                          <td className="px-3 py-1.5 text-right font-medium" style={{ color: side === 'buy' ? '#16a34a' : '#dc2626' }}>
                            {(coin.price * (1 + change)).toFixed(2)}
                          </td>
                          <td className="px-3 py-1.5 text-right" style={{ color: '#6B6760' }}>{(Math.random() * 2).toFixed(4)}</td>
                          <td className="px-3 py-1.5 text-right" style={{ color: '#6B6760' }}>{(Math.random() * 5).toFixed(2)}</td>
                          <td className="px-3 py-1.5 text-right" style={{ color: '#6B6760' }}>{`${Math.floor(Math.random() * 30)}s ago`}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* ─── RIGHT SIDEBAR: ORDER BOOK + AI ALERTS ─── */}
          <div className="hidden lg:block w-[240px] shrink-0 space-y-3">

            {/* Order Book */}
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5', backgroundColor: '#F4F1EA' }}>
              <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: '#D9D3C5' }}>
                <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#6B6760' }}>Order Book</span>
                <span className="text-[9px]" style={{ color: '#6B6760' }}>{coin.symbol}/USDT</span>
              </div>

              {/* Header */}
              <div className="flex items-center justify-between px-3 py-1 text-[9px] uppercase tracking-wider" style={{ color: '#6B6760', backgroundColor: '#FAF9F6' }}>
                <span>Price</span>
                <span>Amount</span>
                <span>Total</span>
              </div>

              {/* Asks (red) */}
              <div className="space-y-0.5 px-1.5 py-1">
                {orderBook.asks.slice().reverse().map((ask, i) => (
                  <div key={`a-${i}`} className="relative flex items-center justify-between px-1.5 py-0.5 text-[10px] font-mono">
                    <div className="absolute right-0 top-0 bottom-0 rounded-sm" style={{
                      width: `${ask.depthPct}%`,
                      backgroundColor: 'rgba(220,38,38,0.08)',
                    }} />
                    <span className="relative z-10 font-medium" style={{ color: '#dc2626' }}>{ask.price.toFixed(2)}</span>
                    <span className="relative z-10" style={{ color: '#6B6760' }}>{ask.amount.toFixed(4)}</span>
                    <span className="relative z-10" style={{ color: '#6B6760' }}>{ask.total.toFixed(2)}</span>
                  </div>
                ))}
              </div>

              {/* Spread / Last Price */}
              <div className="flex items-center justify-between px-3 py-1.5 border-t border-b" style={{ borderColor: '#D9D3C5', backgroundColor: '#FAF9F6' }}>
                <span className="text-xs font-bold font-mono" style={{ color: pctColor(coin.change24h) }}>
                  {formatPrice(coin.price)}
                </span>
                <span className="text-[9px]" style={{ color: '#6B6760' }}>Spread: {orderBook.spread}%</span>
              </div>

              {/* Bids (green) */}
              <div className="space-y-0.5 px-1.5 py-1">
                {orderBook.bids.map((bid, i) => (
                  <div key={`b-${i}`} className="relative flex items-center justify-between px-1.5 py-0.5 text-[10px] font-mono">
                    <div className="absolute right-0 top-0 bottom-0 rounded-sm" style={{
                      width: `${bid.depthPct}%`,
                      backgroundColor: 'rgba(22,163,74,0.08)',
                    }} />
                    <span className="relative z-10 font-medium" style={{ color: '#16a34a' }}>{bid.price.toFixed(2)}</span>
                    <span className="relative z-10" style={{ color: '#6B6760' }}>{bid.amount.toFixed(4)}</span>
                    <span className="relative z-10" style={{ color: '#6B6760' }}>{bid.total.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Market Alerts */}
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5', backgroundColor: '#F4F1EA' }}>
              <div className="flex items-center gap-2 px-3 py-2 border-b" style={{ borderColor: '#D9D3C5' }}>
                <Zap className="w-3 h-3 text-[#E25A2B]" />
                <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#6B6760' }}>AI Alerts</span>
              </div>
              <div className="divide-y" style={{ borderColor: '#D9D3C5' }}>
                {[
                  { icon: TrendingUp, label: 'Whale Buy Detected', desc: '12.5K BTC accumulated', color: '#16a34a', time: '2m ago' },
                  { icon: ArrowUpRight, label: 'Exchange Outflow Spike', desc: '8.2K BTC left exchanges', color: '#E25A2B', time: '5m ago' },
                  { icon: Activity, label: 'Volume Surge', desc: '240% above 4h average', color: '#16a34a', time: '8m ago' },
                  { icon: TrendingUp, label: 'Bullish Sentiment', desc: 'Social sentiment at 73% positive', color: '#3b82f6', time: '12m ago' },
                  { icon: AlertTriangle, label: 'Liquidation Cluster', desc: '$24M long liquidation cluster', color: '#dc2626', time: '18m ago' },
                ].map((alert, i) => {
                  const Icon = alert.icon
                  return (
                    <div key={i} className="flex items-start gap-2.5 px-3 py-2.5">
                      <Icon className="w-3 h-3 mt-0.5 shrink-0" style={{ color: alert.color }} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-medium">{alert.label}</span>
                          <span className="text-[9px]" style={{ color: '#6B6760' }}>{alert.time}</span>
                        </div>
                        <div className="text-[10px]" style={{ color: '#6B6760' }}>{alert.desc}</div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Quick balance */}
            <div className="rounded-lg border p-3" style={{ borderColor: '#D9D3C5', backgroundColor: '#FAF9F6' }}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[9px] font-semibold uppercase tracking-wider" style={{ color: '#6B6760' }}>Balances</span>
                <Eye className="w-3 h-3" style={{ color: '#6B6760' }} />
              </div>
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span style={{ color: '#6B6760' }}>USDT</span>
                  <span className="font-medium">0.00</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span style={{ color: '#6B6760' }}>{coin.symbol}</span>
                  <span className="font-medium">0.0000</span>
                </div>
                <div className="flex items-center justify-between text-[10px] pt-1 border-t" style={{ borderColor: '#D9D3C5' }}>
                  <span style={{ color: '#6B6760' }}>Total Value</span>
                  <span className="font-medium">$0.00</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════ AUTH MODAL (only on "Confirm Trade") ═══════════ */}
      {showAuthModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="rounded-xl border shadow-2xl w-[380px] overflow-hidden" style={{ borderColor: '#D9D3C5', backgroundColor: '#F4F1EA' }}>
            {/* Modal header */}
            <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: '#D9D3C5' }}>
              <h2 className="text-base font-bold">Complete Your Trade</h2>
              <button onClick={() => setShowAuthModal(false)} className="p-1 rounded-md hover:bg-black/5">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5">
              <p className="text-xs mb-5" style={{ color: '#6B6760' }}>
                Sign in or connect a wallet to execute your {tradeSide} order of <strong style={{ color: '#0E0E0C' }}>{orderAmount || '0.00'} {coin.symbol}</strong>.
              </p>

              {/* Auth tabs */}
              <div className="flex gap-1.5 mb-4">
                {(['signin', 'signup', 'wallet', 'exchange'] as const).map(mode => (
                  <button key={mode} onClick={() => setAuthMode(mode)}
                    className={`flex-1 py-2 text-[10px] font-semibold rounded-md transition-all ${
                      authMode === mode ? 'text-white' : 'text-[#6B6760] hover:text-[#0E0E0C]'
                    }`}
                    style={authMode === mode ? { backgroundColor: '#0E0E0C' } : { backgroundColor: '#E6E1D6' }}>
                    {mode === 'signin' ? 'Sign In' : mode === 'signup' ? 'Sign Up' : mode === 'wallet' ? 'Wallet' : 'Exchange'}
                  </button>
                ))}
              </div>

              {/* Sign In form */}
              {authMode === 'signin' && (
                <div className="space-y-3">
                  <div>
                    <label className="text-[10px] font-medium block mb-1" style={{ color: '#6B6760' }}>Email</label>
                    <input type="email" placeholder="you@example.com"
                      className="w-full px-3 py-2.5 text-xs rounded-lg outline-none"
                      style={{ backgroundColor: '#E6E1D6', color: '#0E0E0C' }} />
                  </div>
                  <div>
                    <label className="text-[10px] font-medium block mb-1" style={{ color: '#6B6760' }}>Password</label>
                    <input type="password" placeholder="••••••••"
                      className="w-full px-3 py-2.5 text-xs rounded-lg outline-none"
                      style={{ backgroundColor: '#E6E1D6', color: '#0E0E0C' }} />
                  </div>
                  <button className="w-full py-2.5 rounded-lg text-xs font-bold text-white transition-all hover:opacity-90"
                    style={{ backgroundColor: tradeSide === 'buy' ? '#16a34a' : '#dc2626' }}>
                    {tradeSide === 'buy' ? 'Buy' : 'Sell'} {coin.symbol}
                  </button>
                  <p className="text-[10px] text-center" style={{ color: '#6B6760' }}>
                    Don't have an account? <button onClick={() => setAuthMode('signup')} className="font-semibold" style={{ color: '#E25A2B' }}>Sign Up</button>
                  </p>
                </div>
              )}

              {/* Sign Up form */}
              {authMode === 'signup' && (
                <div className="space-y-3">
                  <div>
                    <label className="text-[10px] font-medium block mb-1" style={{ color: '#6B6760' }}>Email</label>
                    <input type="email" placeholder="you@example.com"
                      className="w-full px-3 py-2.5 text-xs rounded-lg outline-none"
                      style={{ backgroundColor: '#E6E1D6', color: '#0E0E0C' }} />
                  </div>
                  <div>
                    <label className="text-[10px] font-medium block mb-1" style={{ color: '#6B6760' }}>Password</label>
                    <input type="password" placeholder="Create a password"
                      className="w-full px-3 py-2.5 text-xs rounded-lg outline-none"
                      style={{ backgroundColor: '#E6E1D6', color: '#0E0E0C' }} />
                  </div>
                  <button className="w-full py-2.5 rounded-lg text-xs font-bold text-white transition-all hover:opacity-90" style={{ backgroundColor: '#E25A2B' }}>
                    Create Account & Execute
                  </button>
                </div>
              )}

              {/* Wallet Connect */}
              {authMode === 'wallet' && (
                <div className="space-y-2">
                  {['MetaMask', 'WalletConnect', 'Coinbase Wallet', 'Phantom'].map(wallet => (
                    <button key={wallet}
                      className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-xs font-medium transition-colors hover:bg-black/5 border"
                      style={{ borderColor: '#D9D3C5', backgroundColor: '#FAF9F6' }}>
                      <div className="w-6 h-6 rounded-full flex items-center justify-center text-[8px] font-bold" style={{ backgroundColor: '#E6E1D6' }}>{wallet[0]}</div>
                      {wallet}
                    </button>
                  ))}
                </div>
              )}

              {/* Exchange Connect */}
              {authMode === 'exchange' && (
                <div className="space-y-2">
                  {['Binance', 'Bybit', 'Coinbase', 'Kraken'].map(ex => (
                    <button key={ex}
                      className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-xs font-medium transition-colors hover:bg-black/5 border"
                      style={{ borderColor: '#D9D3C5', backgroundColor: '#FAF9F6' }}>
                      <div className="w-6 h-6 rounded-full flex items-center justify-center text-[8px] font-bold" style={{ backgroundColor: '#E6E1D6' }}>{ex[0]}</div>
                      Connect {ex}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Bottom padding */}
      <div className="h-8" />
    </div>
  )
}

// ── Sub-components ──────────────────────────────────────────────────

function SidebarSection({
  title, icon: Icon, children, isOpen, onClick,
}: {
  title: string; icon: any; children: React.ReactNode; isOpen: boolean; onClick: () => void
}) {
  return (
    <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5', backgroundColor: '#F4F1EA' }}>
      <button onClick={onClick}
        className="flex items-center justify-between w-full px-3 py-2.5 text-[10px] font-semibold uppercase tracking-wider transition-colors hover:bg-black/[0.02]"
        style={{ color: '#6B6760' }}>
        <div className="flex items-center gap-2">
          <Icon className="w-3 h-3" />
          {title}
        </div>
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-0' : '-rotate-90'}`} />
      </button>
      {isOpen && <div className="pb-1">{children}</div>}
    </div>
  )
}
