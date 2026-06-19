'use client'

import { useState, useMemo } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { COINS, type Signal } from '@/lib/market-data'
import CryptoIcon from '@/components/CryptoIcon'
import { formatCompact, formatPrice, pctColor } from '@/lib/market-utils'
import {
  Search, TrendingUp, TrendingDown, Minus, Sparkles, BarChart3,
  Bookmark, Users, Activity, Brain, Menu, X, Eye, Globe,
  Twitter, MessageCircle,
  ChevronDown, ChevronUp, ChevronRight, Heart, Clock,
  Zap, Star,
} from 'lucide-react'

// ── Candlestick generator ────────────────────────────────────────────

function generateCandles(base: number, count: number) {
  const candles: { open: number; high: number; low: number; close: number; time: number }[] = []
  let price = base * 0.95
  for (let i = 0; i < count; i++) {
    const open = price
    const close = open * (1 + (Math.random() - 0.48) * 0.04)
    const high = Math.max(open, close) * (1 + Math.random() * 0.015)
    const low = Math.min(open, close) * (1 - Math.random() * 0.015)
    candles.push({ open, high, low, close, time: i })
    price = close
  }
  return candles
}

// ── Main Component ──────────────────────────────────────────────────

export default function CoinDetailPage() {
  const params = useParams()
  const slug = (params?.slug as string)?.toUpperCase() || 'BTC'
  const coin = COINS.find(c => c.symbol === slug) || COINS[0]

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [chartPeriod, setChartPeriod] = useState('1D')
  const [search, setSearch] = useState('')
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null)
  const [activeInfoTab, setActiveInfoTab] = useState<'overview' | 'markets' | 'news' | 'community'>('overview')

  const signalColors: Record<Signal, string> = { BUY: '#16a34a', SELL: '#dc2626', WAIT: '#d97706' }
  const candles = useMemo(() => generateCandles(coin.price, 100), [coin.price])

  const supply = coin.marketCap / coin.price

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#F4F1EA' }}>
      {/* ═══════════ TOP NAV ═══════════ */}
      <header className="sticky top-0 z-50 border-b" style={{ backgroundColor: '#F4F1EA', borderColor: '#D9D3C5' }}>
        <div className="w-full px-1.5 lg:px-2" style={{ maxWidth: 1800, margin: '0 auto' }}>
          <div className="flex items-center justify-between h-12">
            <Link href="/" className="flex items-center gap-1.5 shrink-0">
              <span className="text-base font-bold tracking-tight" style={{ fontFamily: "'Archivo Black', sans-serif" }}>
                <span className="text-black">SILVER</span><span className="text-[#E25A2B]">TRADE</span>
              </span>
            </Link>
            <nav className="hidden lg:flex items-center gap-0.5">
              {[{ href: '/markets', label: 'Markets', icon: BarChart3, active: true }, { href: '/dashboard', label: 'Portfolio', icon: Users }, { href: '/dashboard/chat', label: 'AI Signals', icon: Brain }].map(item => {
                const Icon = item.icon
                return <Link key={item.href} href={item.href} className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${item.active ? 'text-white bg-[#E25A2B]' : 'text-[#6B6760] hover:text-[#0E0E0C] hover:bg-black/5'}`}><Icon className="w-3.5 h-3.5" />{item.label}</Link>
              })}
            </nav>
            <div className="flex items-center gap-1.5 lg:gap-2">
              <div className="hidden sm:block relative w-36 lg:w-48">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3" style={{ color: '#6B6760' }} />
                <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search..."
                  className="w-full pl-7 pr-2 py-1.5 text-xs rounded-md outline-none" style={{ backgroundColor: '#E6E1D6', color: '#0E0E0C' }} />
              </div>
              <Link href="/login" className="px-2.5 py-1.5 text-xs font-medium rounded-md" style={{ color: '#6B6760' }}>Sign In</Link>
              <Link href="/signup" className="px-2.5 py-1.5 text-xs font-semibold rounded-md text-white" style={{ backgroundColor: '#0E0E0C' }}>Get Started</Link>
              <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="lg:hidden p-1.5 rounded-md hover:bg-black/5">
                {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ═══════════ ASSET INFO STRIP ═══════════ */}
      <div className="border-b" style={{ borderColor: '#D9D3C5' }}>
        <div className="w-full px-1.5 lg:px-2" style={{ maxWidth: 1800, margin: '0 auto' }}>
          <div className="flex items-center gap-2 h-12 overflow-x-auto">
            <div className="flex items-center gap-2 shrink-0">
              <Link href={`/markets/${coin.symbol.toLowerCase()}/trade`} className="flex items-center gap-2">
                <CryptoIcon symbol={coin.symbol} size={28} />
                <h1 className="text-base font-bold">{coin.name}</h1>
                <span className="text-xs font-mono font-medium" style={{ color: '#6B6760' }}>{coin.symbol}</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded" style={{ backgroundColor: '#E6E1D6', color: '#6B6760' }}>Rank #{coin.rank}</span>
              </Link>
            </div>
            <div className="shrink-0">
              <div className="text-lg font-bold tracking-tight">{formatPrice(coin.price)}</div>
            </div>
            <span className="text-xs font-medium shrink-0" style={{ color: pctColor(coin.change24h) }}>
              {coin.change24h >= 0 ? '+' : ''}{coin.change24h.toFixed(2)}%
            </span>
            <div className="w-px h-4 shrink-0" style={{ backgroundColor: '#D9D3C5' }} />
            <div className="flex items-center gap-3 text-[11px] shrink-0 overflow-x-auto">
              <span style={{ color: '#6B6760' }}>MCap <strong style={{ color: '#0E0E0C' }}>{formatCompact(coin.marketCap)}</strong></span>
              <span style={{ color: '#6B6760' }}>Vol <strong style={{ color: '#0E0E0C' }}>{formatCompact(coin.volume24h)}</strong></span>
              <span style={{ color: '#6B6760' }}>Supply <strong style={{ color: '#0E0E0C' }}>{supply > 1e9 ? `${(supply / 1e9).toFixed(2)}B` : supply > 1e6 ? `${(supply / 1e6).toFixed(2)}M` : `${(supply / 1e3).toFixed(1)}K`}</strong></span>
            </div>
            <div className="w-px h-4 shrink-0" style={{ backgroundColor: '#D9D3C5' }} />
            <div className="flex items-center gap-1.5 shrink-0">
              <Sparkles className="w-3 h-3 text-[#E25A2B]" />
              <span className="text-[9px] font-semibold uppercase tracking-widest text-[#E25A2B]">AI</span>
              <span className="text-xs font-bold" style={{ color: signalColors[coin.aiSignal] }}>{coin.aiSignal}</span>
              <span className="text-[10px] font-mono font-semibold" style={{ color: '#6B6760' }}>{coin.confidence}%</span>
            </div>
            <div className="flex-1 min-w-4" />
            <div className="flex items-center gap-1">
              <button className="p-1.5 rounded-md hover:bg-black/5 shrink-0"><Star className="w-3.5 h-3.5" style={{ color: '#6B6760' }} /></button>
              <Link href={`/markets/${coin.symbol.toLowerCase()}/trade`}
                className="px-3 py-1.5 text-[11px] font-bold rounded-md text-white shrink-0"
                style={{ backgroundColor: signalColors[coin.aiSignal] }}>
                {coin.aiSignal === 'BUY' ? 'Buy' : coin.aiSignal === 'SELL' ? 'Sell' : 'Alert'}
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════ FIRST VIEWPORT — DENSE ABOVE FOLD ═══════════ */}
      <div className="w-full px-1.5 lg:px-2 py-2" style={{ maxWidth: 1800, margin: '0 auto' }}>
        <div className="flex gap-2">
          {/* ─── LEFT: Asset Stat Panel (compact) ─── */}
          <div className="hidden xl:block w-[200px] shrink-0 space-y-2">
            <div className="rounded-lg border p-2 space-y-1.5" style={{ borderColor: '#D9D3C5' }}>
              {[
                { l: 'Market Cap', v: formatCompact(coin.marketCap) },
                { l: '24h Volume', v: formatCompact(coin.volume24h) },
                { l: '24h Change', v: `${coin.change24h >= 0 ? '+' : ''}${coin.change24h.toFixed(2)}%`, c: pctColor(coin.change24h) },
                { l: '7D Change', v: `${coin.change7d >= 0 ? '+' : ''}${coin.change7d.toFixed(2)}%`, c: pctColor(coin.change7d) },
                { l: 'Circulating Supply', v: `${(supply / 1e6).toFixed(2)}M ${coin.symbol}` },
                { l: 'All-Time High', v: formatPrice(coin.price * 1.55) },
                { l: 'All-Time Low', v: formatPrice(coin.price * 0.35) },
              ].map(item => (
                <div key={item.l} className="flex items-center justify-between">
                  <span className="text-[10px]" style={{ color: '#6B6760' }}>{item.l}</span>
                  <span className="text-[11px] font-semibold" style={item.c ? { color: item.c } : { color: '#0E0E0C' }}>{item.v}</span>
                </div>
              ))}
            </div>
            <div className="rounded-lg border p-2" style={{ borderColor: '#D9D3C5' }}>
              <div className="flex items-center gap-1.5 mb-1.5">
                <Brain className="w-3 h-3 text-[#E25A2B]" />
                <span className="text-[9px] font-semibold uppercase tracking-widest text-[#E25A2B]">AI Verdict</span>
              </div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-black" style={{ color: signalColors[coin.aiSignal] }}>{coin.aiSignal}</span>
                <span className="text-[11px] font-bold" style={{ color: signalColors[coin.aiSignal] }}>{coin.confidence}%</span>
              </div>
              <div className="w-full h-1 rounded-full overflow-hidden mb-1.5" style={{ backgroundColor: '#E6E1D6' }}>
                <div className="h-full rounded-full" style={{ width: `${coin.confidence}%`, backgroundColor: signalColors[coin.aiSignal] }} />
              </div>
              <div className="text-[10px] leading-relaxed" style={{ color: '#6B6760' }}>
                <span className="font-medium" style={{ color: '#0E0E0C' }}>Risk: </span>Medium
                <br />
                <span className="font-medium" style={{ color: '#0E0E0C' }}>Upside: </span><span className="text-green-600">+12.4%</span>
                <br />
                <span className="font-medium" style={{ color: '#0E0E0C' }}>Downside: </span><span className="text-red-600">-4.8%</span>
              </div>
              <Link href={`/markets/${coin.symbol.toLowerCase()}/trade`}
                className="block w-full text-center py-1.5 mt-1.5 rounded-md text-[11px] font-bold text-white"
                style={{ backgroundColor: signalColors[coin.aiSignal] }}>Execute</Link>
            </div>
            <div className="grid grid-cols-2 gap-1">
              {[{ icon: Globe, label: 'Website' }, { icon: Twitter, label: 'Twitter' }, { icon: MessageCircle, label: 'Discord' }, { icon: Eye, label: 'Explorer' }].map(item => {
                const Icon = item.icon
                return <a key={item.label} href="#" className="flex items-center gap-1.5 p-1.5 rounded-lg border text-[10px] transition-colors hover:bg-black/5" style={{ borderColor: '#D9D3C5', color: '#6B6760' }}><Icon className="w-3 h-3" />{item.label}</a>
              })}
            </div>
          </div>

          {/* ─── CENTER: CHART (HERO) ─── */}
          <div className="flex-1 min-w-0">
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5' }}>
              {/* Chart toolbar */}
              <div className="flex items-center justify-between px-3 py-1.5 border-b" style={{ borderColor: '#D9D3C5', backgroundColor: '#FAF9F6' }}>
                <div className="flex items-center gap-0.5">
                  {['1D', '7D', '1M', '3M', '1Y', 'ALL'].map(p => (
                    <button key={p} onClick={() => setChartPeriod(p)}
                      className={`px-2 py-0.5 text-[10px] font-medium rounded-sm transition-colors ${chartPeriod === p ? 'text-white' : 'text-[#6B6760] hover:text-[#0E0E0C]'}`}
                      style={chartPeriod === p ? { backgroundColor: '#E25A2B' } : {}}>{p}</button>
                  ))}
                </div>
                <div className="flex items-center gap-2 text-[10px]" style={{ color: '#6B6760' }}>
                  <span className="font-medium" style={{ color: pctColor(coin.change24h) }}>{coin.change24h >= 0 ? '+' : ''}{coin.change24h.toFixed(2)}%</span>
                  <span className="w-px h-2.5" style={{ backgroundColor: '#D9D3C5' }} />
                  <span>O {formatPrice(candles[0]?.open || coin.price)}</span>
                  <span>H {formatPrice(Math.max(...candles.slice(-20).map(c => c.high)))}</span>
                  <span>L {formatPrice(Math.min(...candles.slice(-20).map(c => c.low)))}</span>
                </div>
              </div>
              {/* Chart canvas */}
              <div className="relative" style={{ height: 600 }}>
                <svg width="100%" height="100%" viewBox="0 0 1200 500" preserveAspectRatio="none" className="overflow-visible absolute inset-0">
                  {[0, 100, 200, 300, 400, 500].map(y => (<line key={y} x1="0" y1={y} x2="1200" y2={y} stroke="#E6E1D6" strokeWidth="0.5" />))}
                  {candles.slice(-80).map((c, i) => {
                    const x = (i / 79) * 1180 + 10
                    const allLow = Math.min(...candles.map(cc => cc.low))
                    const allHigh = Math.max(...candles.map(cc => cc.high))
                    const range = allHigh - allLow || 1
                    const highY = 470 - ((c.high - allLow) / range) * 420
                    const lowY = 470 - ((c.low - allLow) / range) * 420
                    const openY = 470 - ((c.open - allLow) / range) * 420
                    const closeY = 470 - ((c.close - allLow) / range) * 420
                    const isUp = c.close >= c.open
                    const color = isUp ? '#16a34a' : '#dc2626'
                    return (<g key={i}><line x1={x} y1={highY} x2={x} y2={lowY} stroke={color} strokeWidth={0.6} /><rect x={x - 2} y={Math.min(openY, closeY)} width={4} height={Math.max(Math.abs(closeY - openY), 1)} fill={color} rx={0.3} /></g>)
                  })}
                  {candles.slice(-80).map((c, i) => {
                    const x = (i / 79) * 1180 + 10
                    const volH = ((c.high - c.low) / (Math.max(...candles.map(cc => cc.high - cc.low)) || 1)) * 35
                    return <rect key={`v-${i}`} x={x - 1.5} y={470 - volH} width={3} height={volH} fill={c.close >= c.open ? 'rgba(22,163,74,0.1)' : 'rgba(220,38,38,0.1)'} />
                  })}
                  <line x1={600} y1="0" x2={600} y2="500" stroke="#E25A2B" strokeWidth="0.5" strokeDasharray="3,3" opacity={0.15} />
                  <line x1="0" y1={250} x2="1200" y2={250} stroke="#E25A2B" strokeWidth="0.5" strokeDasharray="3,3" opacity={0.15} />
                </svg>
                <div className="absolute top-2 left-3 space-y-0.5">
                  <div className="text-[10px] font-mono" style={{ color: '#6B6760' }}>{coin.symbol}/USD</div>
                  <div className="text-6xl font-bold tracking-tight leading-none">{formatPrice(coin.price)}</div>
                  <div className="flex items-center gap-2 text-xs font-medium"><span style={{ color: pctColor(coin.change24h) }}>{coin.change24h >= 0 ? '+' : ''}{coin.change24h.toFixed(2)}%</span><span style={{ color: '#6B6760' }}>24h</span></div>
                </div>
              </div>
              {/* AI signal strip */}
              <div className="flex items-center gap-1.5 px-2 py-1 border-t overflow-x-auto" style={{ borderColor: '#D9D3C5', backgroundColor: '#0E0E0C' }}>
                <span className="text-[9px] font-semibold uppercase tracking-widest text-[#E25A2B] shrink-0">AI</span>
                {['Market: Bullish', 'Whales: Accumulating', 'Social: Positive', 'News: Neutral', 'Vol: Low', 'Trend: Strong'].map(s => (
                  <span key={s} className="text-[10px] shrink-0" style={{ color: '#999' }}>{s}</span>
                ))}
              </div>
            </div>

            {/* ─── INFO TAB BAR (switches content below) ─── */}
            <div className="flex items-center gap-0.5 mt-2 border-b" style={{ borderColor: '#D9D3C5' }}>
              {([
                { key: 'overview', label: 'Overview' },
                { key: 'markets', label: 'Markets' },
                { key: 'news', label: 'News' },
                { key: 'community', label: 'Community' },
              ] as const).map(tab => (
                <button key={tab.key} onClick={() => setActiveInfoTab(tab.key)}
                  className={`px-2.5 py-1.5 text-[10px] font-semibold relative ${activeInfoTab === tab.key ? 'text-[#0E0E0C]' : 'text-[#6B6760] hover:text-[#0E0E0C]'}`}>
                  {tab.label}
                  {activeInfoTab === tab.key && <div className="absolute bottom-0 left-1 right-1 h-0.5 rounded-full" style={{ backgroundColor: '#E25A2B' }} />}
                </button>
              ))}
              <div className="flex-1" />
              <Link href={`/markets/${coin.symbol.toLowerCase()}/trade`} className="text-[11px] font-medium flex items-center gap-1 px-2 py-1 rounded" style={{ color: '#E25A2B' }}>Trade <ChevronRight className="w-3 h-3" /></Link>
            </div>

            {/* ─── TAB CONTENT ─── */}
            <div className="mt-2 space-y-2">

              {/* ─── OVERVIEW ─── */}
              {activeInfoTab === 'overview' && (
                <>                      {/* Markets table (always visible first) */}
                  <section>
                    <h3 className="text-3xl font-bold mb-1.5">Markets</h3>
                    <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5' }}>
                      <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>
                        <thead><tr className="text-[11px] font-semibold uppercase tracking-wider" style={{ backgroundColor: '#F4F1EA', color: '#6B6760' }}>
                          {['Exchange', 'Pair', 'Price', 'Volume', 'Liquidity', 'Spread', 'Trust'].map(h => (<th key={h} className="px-2 py-1.5 text-right first:text-left">{h}</th>))}
                        </tr></thead>
                        <tbody>
                          {[{ ex: 'Binance', vol: coin.volume24h * 0.35, liq: 96.2, spr: 0.01, trust: '4.9' }, { ex: 'Bybit', vol: coin.volume24h * 0.22, liq: 94.8, spr: 0.02, trust: '4.8' }, { ex: 'Coinbase', vol: coin.volume24h * 0.18, liq: 93.1, spr: 0.03, trust: '4.7' }, { ex: 'Kraken', vol: coin.volume24h * 0.08, liq: 89.5, spr: 0.04, trust: '4.5' }, { ex: 'KuCoin', vol: coin.volume24h * 0.06, liq: 87.3, spr: 0.03, trust: '4.4' }].map((row, i) => (
                            <tr key={row.ex} className="transition-colors hover:bg-black/[0.02]" style={{ borderBottom: i < 4 ? '1px solid' : 'none', borderColor: '#D9D3C5' }}>
                              <td className="px-2 py-1.5 text-left font-medium">{row.ex}</td>
                              <td className="px-2 py-1.5 text-right font-mono">{coin.symbol}/USDT</td>
                              <td className="px-2 py-1.5 text-right font-semibold">{formatPrice(coin.price)}</td>
                              <td className="px-2 py-1.5 text-right" style={{ color: '#6B6760' }}>{formatCompact(row.vol)}</td>
                              <td className="px-2 py-1.5 text-right">{row.liq}%</td>
                              <td className="px-2 py-1.5 text-right">{row.spr}%</td>
                              <td className="px-2 py-1.5 text-right font-mono">{row.trust}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>

                  {/* News */}
                  <section>
                    <h3 className="text-3xl font-bold mb-1.5">News</h3>
                    <div className="space-y-1.5">
                      {[
                        { h: `${coin.name} Network Activity Surges 40%`, s: 'On-chain metrics show increased institutional participation.', tag: 'Bullish', tagColor: '#16a34a' },
                        { h: `Analysts Eye ${coin.symbol} as Key Level Approaches`, s: 'Technical indicators point to potential breakout near resistance.', tag: 'Neutral', tagColor: '#d97706' },
                        { h: `Regulatory Clarity Could Boost ${coin.name} Adoption`, s: 'New frameworks in major economies provide institutional clarity.', tag: 'Bullish', tagColor: '#16a34a' },
                      ].map((item, i) => (
                        <div key={i} className="p-2 rounded-lg border transition-colors hover:bg-black/[0.02]" style={{ borderColor: '#D9D3C5' }}>
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-xs font-semibold leading-snug">{item.h}</p>
                            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0" style={{ backgroundColor: `${item.tagColor}15`, color: item.tagColor }}>{item.tag}</span>
                          </div>
                          <p className="text-sm mt-0.5" style={{ color: '#6B6760' }}>{item.s}</p>
                        </div>
                      ))}
                    </div>
                  </section>

                  {/* Whale Intelligence */}
                  <section>
                    <h3 className="text-3xl font-bold mb-1.5">Whale Activity</h3>
                    <div className="rounded-lg border divide-y" style={{ borderColor: '#D9D3C5' }}>
                      {[
                        { t: 'Accumulation', d: `Top 10 wallets accumulated 850,000 ${coin.symbol}`, c: '+12.4%', clr: '#16a34a' },
                        { t: 'Selling Pressure', d: `Whale wallet sold 120,000 ${coin.symbol} on Binance`, c: '-3.2%', clr: '#dc2626' },
                        { t: 'Large Transaction', d: `$42.8M ${coin.symbol} moved to unknown wallet`, c: 'Alert', clr: '#d97706' },
                        { t: 'Exchange Inflow', d: `${coin.symbol} inflows spiked 28%`, c: '+28%', clr: '#dc2626' },
                        { t: 'Exchange Outflow', d: `${coin.symbol} outflows at 3-month high`, c: '+45%', clr: '#16a34a' },
                      ].map((item, i) => (
                        <div key={i} className="flex items-center justify-between px-2.5 py-2">
                          <div className="flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: item.clr }} />
                            <div><div className="text-xs font-medium">{item.t}</div><div className="text-sm" style={{ color: '#6B6760' }}>{item.d}</div></div>
                          </div>
                          <span className="text-[11px] font-semibold shrink-0" style={{ color: item.clr }}>{item.c}</span>
                        </div>
                      ))}
                    </div>
                  </section>

                  {/* Community Sentiment */}
                  <section>
                    <h3 className="text-3xl font-bold mb-1.5">Community Sentiment</h3>
                    <div className="grid grid-cols-3 gap-1.5">
                      <div className="p-2 rounded-lg border text-center" style={{ borderColor: '#D9D3C5' }}>
                        <div className="text-[11px] font-semibold uppercase tracking-wider text-green-600">Bullish</div>
                        <div className="text-lg font-bold text-green-600">62%</div>
                        <div className="w-full h-1 rounded-full mt-1 overflow-hidden" style={{ backgroundColor: '#E6E1D6' }}><div className="h-full rounded-full bg-green-500" style={{ width: '62%' }} /></div>
                      </div>
                      <div className="p-2 rounded-lg border text-center" style={{ borderColor: '#D9D3C5' }}>
                        <div className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#6B6760' }}>Neutral</div>
                        <div className="text-lg font-bold" style={{ color: '#6B6760' }}>23%</div>
                        <div className="w-full h-1 rounded-full mt-1 overflow-hidden" style={{ backgroundColor: '#E6E1D6' }}><div className="h-full rounded-full" style={{ width: '23%', backgroundColor: '#6B6760' }} /></div>
                      </div>
                      <div className="p-2 rounded-lg border text-center" style={{ borderColor: '#D9D3C5' }}>
                        <div className="text-[11px] font-semibold uppercase tracking-wider text-red-600">Bearish</div>
                        <div className="text-lg font-bold text-red-600">15%</div>
                        <div className="w-full h-1 rounded-full mt-1 overflow-hidden" style={{ backgroundColor: '#E6E1D6' }}><div className="h-full rounded-full bg-red-500" style={{ width: '15%' }} /></div>
                      </div>
                    </div>
                  </section>

                  {/* AI Analysis */}
                  <section>
                    <h3 className="text-3xl font-bold mb-1.5">AI Analysis</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                      <div className="p-2.5 rounded-lg border" style={{ borderColor: '#D9D3C5' }}>
                        <div className="text-xl font-semibold uppercase tracking-wider mb-1" style={{ color: '#E25A2B' }}>Short-Term (1-7D)</div>
                        <p className="text-sm leading-relaxed" style={{ color: '#0E0E0C' }}>{coin.symbol === 'DOGE' || coin.symbol === 'SHIB' ? 'Bearish momentum. RSI below 40. Key support test imminent.' : 'Bullish momentum. Price above key moving averages. Room for upside.'}</p>
                        <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded mt-1.5 ${coin.trend === 'bullish' ? 'text-green-700 bg-green-100' : coin.trend === 'bearish' ? 'text-red-700 bg-red-100' : 'text-amber-700 bg-amber-100'}`}>
                          {coin.trend === 'bullish' ? <TrendingUp className="w-2.5 h-2.5" /> : coin.trend === 'bearish' ? <TrendingDown className="w-2.5 h-2.5" /> : <Minus className="w-2.5 h-2.5" />}
                          {coin.trend === 'bullish' ? 'Bullish' : coin.trend === 'bearish' ? 'Bearish' : 'Neutral'}
                        </span>
                      </div>
                      <div className="p-2.5 rounded-lg border" style={{ borderColor: '#D9D3C5' }}>
                        <div className="text-xl font-semibold uppercase tracking-wider mb-1" style={{ color: '#d97706' }}>Mid-Term (1-4W)</div>
                        <p className="text-sm leading-relaxed" style={{ color: '#0E0E0C' }}>Macro factors supportive. Institutional accumulation continues. Network fundamentals strengthening.</p>
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded mt-1.5 text-amber-700 bg-amber-100"><Minus className="w-2.5 h-2.5" /> Neutral-Bullish</span>
                      </div>
                    </div>
                    {/* Tech indicators */}
                    <div className="mt-1.5 rounded-lg border" style={{ borderColor: '#D9D3C5' }}>
                      <div className="grid grid-cols-5 divide-x text-center text-[10px]" style={{ borderColor: '#D9D3C5' }}>
                        {[
                          { l: 'RSI', v: coin.trend === 'bearish' ? '38.2' : '62.8', s: 'Neutral' },
                          { l: 'MACD', v: coin.aiSignal === 'BUY' ? 'Bullish' : 'Bearish', s: coin.aiSignal === 'BUY' ? 'BUY' : 'SELL' },
                          { l: 'EMA 50', v: 'Price Above', s: coin.trend !== 'bearish' ? 'Bullish' : 'Bearish' },
                          { l: 'Bollinger', v: 'Upper Band', s: coin.trend === 'bullish' ? 'Bullish' : 'Bearish' },
                          { l: 'OBV', v: 'Rising', s: 'Bullish' },
                        ].map((item, i) => (
                          <div key={i} className="p-2">
                            <div style={{ color: '#6B6760' }}>{item.l}</div>
                            <div className="font-semibold">{item.v}</div>
                            <div className={`text-[9px] font-bold ${item.s === 'BUY' || item.s === 'Bullish' ? 'text-green-600' : item.s === 'SELL' || item.s === 'Bearish' ? 'text-red-600' : 'text-amber-600'}`}>{item.s}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                    {/* Key Levels */}
                    <div className="flex items-center gap-2 mt-1.5">
                      {[{ l: 'Support', v: formatPrice(coin.price * 0.92) }, { l: 'Resistance', v: formatPrice(coin.price * 1.08) }, { l: 'Risk', v: 'Medium' }, { l: 'Catalyst', v: 'Earnings' }].map(item => (
                        <div key={item.l} className="flex items-center gap-1 text-xs"><span className="text-[10px]" style={{ color: '#6B6760' }}>{item.l}:</span><span className="font-semibold">{item.v}</span></div>
                      ))}
                    </div>
                  </section>

                  {/* Tokenomics */}
                  <section>
                    <h3 className="text-3xl font-bold mb-1.5">Tokenomics</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                      <div className="p-2.5 rounded-lg border space-y-2" style={{ borderColor: '#D9D3C5' }}>
                        {[
                          { l: 'Circulating Supply', v: `${(supply / 1e6).toFixed(1)}M ${coin.symbol}`, pct: Math.min(100, (supply / (supply * 1.25)) * 100) },
                          { l: 'Total Supply', v: `${(supply * 1.15 / 1e6).toFixed(1)}M ${coin.symbol}`, pct: 85 },
                          { l: 'Max Supply', v: coin.symbol === 'BTC' ? '21M BTC' : `${(supply * 1.25 / 1e6).toFixed(1)}M ${coin.symbol}`, pct: 100 },
                        ].map(item => (
                          <div key={item.l}><div className="flex items-center justify-between mb-0.5"><span className="text-[10px]" style={{ color: '#6B6760' }}>{item.l}</span><span className="text-[10px] font-semibold">{item.v}</span></div>
                            <div className="w-full h-1 rounded-full overflow-hidden" style={{ backgroundColor: '#E6E1D6' }}><div className="h-full rounded-full bg-[#E25A2B]" style={{ width: `${item.pct}%` }} /></div>
                          </div>
                        ))}
                      </div>
                      <div className="p-2.5 rounded-lg border" style={{ borderColor: '#D9D3C5' }}>
                        <div className="text-xl font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#6B6760' }}>Unlock Schedule</div>
                        {[{ l: 'Next Unlock', v: '2.5M tokens', t: '14 days', p: 35 }, { l: 'Q3 2026', v: '5.0M tokens', t: '~90 days', p: 55 }, { l: 'Fully Diluted', v: 'All released', t: '2028', p: 100 }].map(item => (
                          <div key={item.l} className="mb-1.5"><div className="flex items-center justify-between mb-0.5"><span className="text-[10px]" style={{ color: '#6B6760' }}>{item.l}</span><div className="flex items-center gap-1.5"><span className="text-[10px] font-semibold">{item.v}</span><span className="text-[9px]" style={{ color: '#6B6760' }}>{item.t}</span></div></div><div className="w-full h-1 rounded-full overflow-hidden" style={{ backgroundColor: '#E6E1D6' }}><div className="h-full rounded-full bg-[#E25A2B]" style={{ width: `${item.p}%` }} /></div></div>
                        ))}
                      </div>
                    </div>
                  </section>

                  {/* FAQ */}
                  <section>
                    <h3 className="text-3xl font-bold mb-1.5">FAQ</h3>
                    <div className="space-y-0.5">
                      {[
                        { q: `What is ${coin.name}?`, a: `${coin.name} (${coin.symbol}) is ranked #${coin.rank} with a price of ${formatPrice(coin.price)} and market cap of ${formatCompact(coin.marketCap)}.` },
                        { q: `Is ${coin.symbol} a good investment?`, a: `AI verdict is ${coin.aiSignal} with ${coin.confidence}% confidence. ${coin.aiSignal === 'BUY' ? 'Technical indicators are favorable.' : coin.aiSignal === 'SELL' ? 'Risk factors suggest caution.' : 'Market showing mixed signals.'}` },
                        { q: `What does the AI think?`, a: `AI analyzes 50+ data points. Current verdict: ${coin.aiSignal} (${coin.confidence}% confidence).` },
                        { q: `What are the risks of ${coin.symbol}?`, a: `Key risks include: market volatility, regulatory changes, competition from other cryptocurrencies, technological risks, and market sentiment shifts. The AI risk score is currently rated as Medium.` },
                      ].map((faq, i) => (
                        <div key={i} className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5' }}>
                          <button onClick={() => setExpandedFaq(expandedFaq === i ? null : i)} className="flex items-center justify-between w-full px-2.5 py-2 text-left transition-colors hover:bg-black/[0.02]">
                            <span className="text-xs font-medium">{faq.q}</span>
                            {expandedFaq === i ? <ChevronUp className="w-3 h-3 shrink-0" style={{ color: '#6B6760' }} /> : <ChevronDown className="w-3 h-3 shrink-0" style={{ color: '#6B6760' }} />}
                          </button>
                          {expandedFaq === i && <div className="px-2.5 pb-2"><p className="text-sm leading-relaxed" style={{ color: '#6B6760' }}>{faq.a}</p></div>}
                        </div>
                      ))}
                    </div>
                  </section>

                  {/* Similar Assets */}
                  <section>
                    <h3 className="text-3xl font-bold mb-1.5">Similar Assets</h3>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                      {COINS.filter(c => c.symbol !== coin.symbol).slice(0, 4).map(sim => (
                        <Link key={sim.symbol} href={`/markets/${sim.symbol.toLowerCase()}`} className="p-2.5 rounded-lg border transition-all hover:bg-black/[0.02]" style={{ borderColor: '#D9D3C5' }}>
                          <div className="flex items-center gap-1.5 mb-1.5">
                            <CryptoIcon symbol={sim.symbol} size={20} />
                            <div><div className="text-xs font-semibold">{sim.symbol}</div><div className="text-[9px]" style={{ color: '#6B6760' }}>{sim.name}</div></div>
                          </div>
                          <div className="flex items-center justify-between"><span className="text-xs font-semibold">{formatPrice(sim.price)}</span><span className="text-[10px] font-medium" style={{ color: pctColor(sim.change24h) }}>{sim.change24h >= 0 ? '+' : ''}{sim.change24h.toFixed(2)}%</span></div>
                          <div className="flex items-center justify-between mt-1"><span className="text-[9px] font-bold px-1 py-0.5 rounded" style={{ backgroundColor: `${signalColors[sim.aiSignal]}15`, color: signalColors[sim.aiSignal] }}>{sim.aiSignal}</span><span className="text-[9px] font-mono" style={{ color: '#6B6760' }}>{sim.confidence}%</span></div>
                        </Link>
                      ))}
                    </div>
                  </section>
                </>
              )}

              {/* ─── MARKETS TAB ─── */}
              {activeInfoTab === 'markets' && (
                <section><h3 className="text-3xl font-bold mb-1.5">All Markets</h3>
                  <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5' }}>
                    <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>                        <thead><tr className="text-[11px] font-semibold uppercase tracking-wider" style={{ backgroundColor: '#F4F1EA', color: '#6B6760' }}>
                          {['Exchange', 'Pair', 'Price', 'Volume', 'Liquidity', 'Spread', 'Trust', 'AI Score'].map(h => (<th key={h} className="px-2 py-1.5 text-right first:text-left">{h}</th>))}
                      </tr></thead>
                      <tbody>
                        {[{ ex: 'Binance', vol: coin.volume24h * 0.35, liq: 96.2, spr: 0.01, trust: '4.9', ai: 96 }, { ex: 'Bybit', vol: coin.volume24h * 0.22, liq: 94.8, spr: 0.02, trust: '4.8', ai: 91 }, { ex: 'Coinbase', vol: coin.volume24h * 0.18, liq: 93.1, spr: 0.03, trust: '4.7', ai: 88 }, { ex: 'Kraken', vol: coin.volume24h * 0.08, liq: 89.5, spr: 0.04, trust: '4.5', ai: 85 }, { ex: 'KuCoin', vol: coin.volume24h * 0.06, liq: 87.3, spr: 0.03, trust: '4.4', ai: 82 }, { ex: 'Gate.io', vol: coin.volume24h * 0.04, liq: 85.1, spr: 0.05, trust: '4.2', ai: 78 }, { ex: 'OKX', vol: coin.volume24h * 0.03, liq: 83.6, spr: 0.04, trust: '4.3', ai: 80 }].map((row, i) => (
                          <tr key={row.ex} className="transition-colors hover:bg-black/[0.02]" style={{ borderBottom: i < 6 ? '1px solid' : 'none', borderColor: '#D9D3C5' }}>
                            <td className="px-2.5 py-2 text-left font-medium">{row.ex}</td>
                            <td className="px-2.5 py-2 text-right font-mono">{coin.symbol}/USDT</td>
                            <td className="px-2.5 py-2 text-right font-semibold">{formatPrice(coin.price)}</td>
                            <td className="px-2.5 py-2 text-right" style={{ color: '#6B6760' }}>{formatCompact(row.vol)}</td>
                            <td className="px-2.5 py-2 text-right">{row.liq}%</td>
                            <td className="px-2.5 py-2 text-right">{row.spr}%</td>
                            <td className="px-2.5 py-2 text-right font-mono">{row.trust}</td>
                            <td className="px-2.5 py-2 text-right"><span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ backgroundColor: `${row.ai >= 90 ? '#16a34a' : row.ai >= 85 ? '#d97706' : '#6B6760'}15`, color: row.ai >= 90 ? '#16a34a' : row.ai >= 85 ? '#d97706' : '#6B6760' }}>{row.ai}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <div className="px-2.5 py-2 border-t text-center text-[10px]" style={{ borderColor: '#D9D3C5', color: '#6B6760' }}>View all 24 markets →</div>
                  </div>
                </section>
              )}

              {/* ─── NEWS TAB ─── */}
              {activeInfoTab === 'news' && (
                <section><h3 className="text-3xl font-bold mb-1.5">Latest News</h3>
                  <div className="space-y-1.5">
                    {[
                      { h: `${coin.name} Network Activity Surges 40% as Institutional Interest Grows`, s: 'On-chain metrics show significant increase in large transactions and active addresses. Volume up 340% week-over-week.', tag: 'Bullish', tc: '#16a34a', eff: 'High' },
                      { h: `Analysts Eye ${coin.symbol} as Key Level Approaches`, s: 'Technical indicators point to an impending breakout as price consolidates near resistance. $105K is the key level.', tag: 'Bullish', tc: '#16a34a', eff: 'Medium' },
                      { h: `Regulatory Clarity Could Boost ${coin.name} Adoption`, s: 'New regulatory frameworks in major economies provide clarity for institutional adoption. Multiple filings expected.', tag: 'Bullish', tc: '#16a34a', eff: 'Medium' },
                      { h: `${coin.symbol} Whales Accumulate 50,000 Tokens in 24 Hours`, s: 'Large holders have been accumulating aggressively. Exchange outflows suggest self-custody trend.', tag: 'Bullish', tc: '#16a34a', eff: 'High' },
                      { h: `Technical Analysis: ${coin.symbol} Forms Bullish Pattern`, s: 'Ascending triangle pattern forming on the daily timeframe. Volume profile supports an upward breakout.', tag: 'Neutral', tc: '#d97706', eff: 'Low' },
                    ].map((item, i) => (
                      <div key={i} className="p-2 rounded-lg border transition-colors hover:bg-black/[0.02]" style={{ borderColor: '#D9D3C5' }}>
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-xs font-semibold leading-snug">{item.h}</p>
                          <div className="flex items-center gap-1 shrink-0">
                            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ backgroundColor: `${item.tc}15`, color: item.tc }}>{item.tag}</span>
                            <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ backgroundColor: '#E6E1D6', color: '#6B6760' }}>{item.eff}</span>
                          </div>
                        </div>
                        <p className="text-xs mt-0.5 leading-relaxed" style={{ color: '#6B6760' }}>{item.s}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* ─── COMMUNITY TAB ─── */}
              {activeInfoTab === 'community' && (
                <section>
                  <h3 className="text-3xl font-bold mb-1.5">Community</h3>
                  <div className="space-y-2">
                    <div className="grid grid-cols-3 gap-1.5">
                      <div className="p-2 rounded-lg border text-center" style={{ borderColor: '#D9D3C5' }}>
                        <div className="text-[9px] font-semibold uppercase tracking-wider text-green-600">Bullish</div>
                        <div className="text-base font-bold text-green-600">62%</div>
                        <div className="w-full h-1 rounded-full mt-1 overflow-hidden" style={{ backgroundColor: '#E6E1D6' }}><div className="h-full rounded-full bg-green-500" style={{ width: '62%' }} /></div>
                      </div>
                      <div className="p-2 rounded-lg border text-center" style={{ borderColor: '#D9D3C5' }}>
                        <div className="text-[9px] font-semibold uppercase tracking-wider" style={{ color: '#6B6760' }}>Neutral</div>
                        <div className="text-base font-bold" style={{ color: '#6B6760' }}>23%</div>
                        <div className="w-full h-1 rounded-full mt-1 overflow-hidden" style={{ backgroundColor: '#E6E1D6' }}><div className="h-full rounded-full" style={{ width: '23%', backgroundColor: '#6B6760' }} /></div>
                      </div>
                      <div className="p-2 rounded-lg border text-center" style={{ borderColor: '#D9D3C5' }}>
                        <div className="text-[9px] font-semibold uppercase tracking-wider text-red-600">Bearish</div>
                        <div className="text-base font-bold text-red-600">15%</div>
                        <div className="w-full h-1 rounded-full mt-1 overflow-hidden" style={{ backgroundColor: '#E6E1D6' }}><div className="h-full rounded-full bg-red-500" style={{ width: '15%' }} /></div>
                      </div>
                    </div>
                    <div className="space-y-1">
                      {[
                        { u: '@crypto_analyst', msg: 'Strong accumulation pattern. $100K is the new floor for BTC. Next leg up incoming.', t: '2m ago', likes: 234 },
                        { u: '@whale_watcher', msg: '12K BTC just moved off exchanges. Largest daily outflow in 3 months. Bullish signal.', t: '8m ago', likes: 189 },
                        { u: '@tech_trader', msg: 'RSI cooling down after the pump. Healthy consolidation. Watching for the next move above resistance.', t: '15m ago', likes: 156 },
                        { u: '@defi_dad', msg: 'Institutional inflow data looking strong this week. ETFs accumulated 5K BTC yesterday.', t: '28m ago', likes: 98 },
                      ].map((post, i) => (
                        <div key={i} className="p-2 rounded-lg border" style={{ borderColor: '#D9D3C5' }}>
                          <div className="flex items-center gap-1.5 mb-0.5"><span className="text-[10px] font-semibold">{post.u}</span><span className="text-[9px]" style={{ color: '#6B6760' }}>{post.t}</span></div>
                          <p className="text-sm leading-relaxed">{post.msg}</p>
                          <div className="flex items-center gap-2 mt-1 text-[9px]" style={{ color: '#6B6760' }}>
                            <span className="flex items-center gap-1"><Heart className="w-2.5 h-2.5" />{post.likes}</span>
                            <span>Reply</span>
                            <span>Share</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>
              )}
            </div>
          </div>

          {/* ─── RIGHT SIDEBAR — ALWAYS ACTIVE ─── */}
          <div className="hidden xl:block w-[280px] shrink-0 space-y-2">
            {/* Community Activity */}
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5' }}>
              <div className="flex items-center gap-1.5 px-2 py-1.5 border-b" style={{ borderColor: '#D9D3C5' }}>
                <Users className="w-3 h-3" style={{ color: '#6B6760' }} />
                <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#6B6760' }}>Community</span>
                <div className="flex-1" />
                <span className="text-[11px] text-[#E25A2B]">Live</span>
              </div>
              <div className="px-1.5 py-1 space-y-1.5">
                {[
                  { u: '@crypto_analyst', msg: 'Strong accumulation pattern. Next leg up incoming.', t: '2m', react: '🔥 12', votes: '▲ 8' },
                  { u: '@whale_watcher', msg: '12K BTC moved off exchanges today.', t: '8m', react: '💬 5', votes: '▲ 3' },
                  { u: '@tech_trader', msg: 'RSI cooling down. Healthy consolidation.', t: '15m', react: '📈 8', votes: '▲ 6' },
                ].map((post, i) => (
                  <div key={i} className="group px-2 py-1.5 rounded-md hover:bg-black/[0.02]">
                    <div className="flex items-center gap-1.5">
                      <button onClick={e => { e.preventDefault(); }} className="text-[8px] opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: '#6B6760' }}>▲</button>
                      <span className="text-[10px] font-semibold">{post.u}</span>
                      <span className="text-[11px]" style={{ color: '#6B6760' }}>{post.t}</span>
                      <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: '#16a34a' }} />
                    </div>
                    <p className="text-xs leading-relaxed">{post.msg}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[11px]">{post.react}</span>
                      <span className="text-[11px]" style={{ color: '#6B6760' }}>{post.votes}</span>
                      <button onClick={e => { e.preventDefault(); }} className="text-[11px] hover:text-[#E25A2B] transition-colors" style={{ color: '#6B6760' }}>Reply</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Trending Discussions */}
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5' }}>
              <div className="flex items-center gap-1.5 px-2 py-1.5 border-b" style={{ borderColor: '#D9D3C5' }}>
                <TrendingUp className="w-3 h-3" style={{ color: '#6B6760' }} />
                <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#6B6760' }}>Trending</span>
              </div>
              <div className="px-1.5 py-1 space-y-0.5">
                {[{ s: `${coin.symbol}`, d: '$104K support holding', v: '▲ 12' }, { s: 'SOL', d: 'Solana ecosystem growth', v: '▲ 8' }, { s: 'AVAX', d: 'Avalanche subnet activity', v: '▲ 6' }, { s: 'ETH', d: 'ETF flow analysis', v: '▲ 5' }, { s: 'DOGE', d: 'Whale distribution', v: '▼ 2' }].map((item, i) => (
                  <Link key={item.s} href={`/markets/${item.s.toLowerCase()}`} className="group flex items-center gap-1.5 px-2 py-1.5 rounded-md hover:bg-black/[0.02] transition-colors">
                    <span className="text-[11px] font-mono" style={{ color: '#6B6760' }}>{i + 1}</span>
                    <button onClick={e => { e.preventDefault(); }} className="flex flex-col items-center leading-none opacity-0 group-hover:opacity-100 transition-opacity">
                      <span className="text-[7px]" style={{ color: '#6B6760' }}>▲</span>
                    </button>
                    <div className="flex-1"><div className="text-[11px] font-medium">{item.s}</div><div className="text-[10px]" style={{ color: '#6B6760' }}>{item.d}</div></div>
                    <span className="text-[9px]" style={{ color: '#6B6760' }}>{item.v}</span>
                  </Link>
                ))}
              </div>
            </div>

            {/* Recent News */}
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5' }}>
              <div className="flex items-center gap-1.5 px-2 py-1.5 border-b" style={{ borderColor: '#D9D3C5' }}>
                <Clock className="w-3 h-3" style={{ color: '#6B6760' }} />
                <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#6B6760' }}>Recent News</span>
              </div>
              <div className="px-1.5 py-1 space-y-1">
                {[
                  { h: `${coin.name} volume surges 240%`, tag: 'Bullish', tc: '#16a34a' },
                  { h: `Analyst: ${coin.symbol} key level at $105K`, tag: 'Neutral', tc: '#d97706' },
                  { h: 'Regulatory clarity expected soon', tag: 'Bullish', tc: '#16a34a' },
                ].map((item, i) => (
                  <div key={i} className="px-2 py-1.5 rounded-md hover:bg-black/[0.02] cursor-pointer">
                    <div className="flex items-center gap-1.5"><span className="text-[10px] leading-tight">{item.h}</span>                      <span className="text-[10px] font-bold px-1 py-0.5 rounded shrink-0" style={{ backgroundColor: `${item.tc}15`, color: item.tc }}>{item.tag}</span></div>
                  </div>
                ))}
              </div>
            </div>

            {/* Watchlist Activity */}
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5' }}>
              <div className="flex items-center gap-1.5 px-2 py-1.5 border-b" style={{ borderColor: '#D9D3C5' }}>
                <Bookmark className="w-3 h-3" style={{ color: '#6B6760' }} />
                <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#6B6760' }}>Watchlist</span>
              </div>
              <div className="px-1.5 py-1 space-y-0.5">
                {[{ s: 'BTC', p: '+2.35%', c: '#16a34a', r: '🔥 24' }, { s: 'ETH', p: '+1.82%', c: '#16a34a', r: '💬 18' }, { s: 'SOL', p: '+6.71%', c: '#16a34a', r: '📈 12' }, { s: 'AVAX', p: '+8.92%', c: '#16a34a', r: '⭐ 9' }].map(item => (
                  <Link key={item.s} href={`/markets/${item.s.toLowerCase()}`} className="flex items-center justify-between px-2 py-1.5 rounded-md hover:bg-black/[0.02]">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-medium">{item.s}</span>
                      <span className="text-[10px]" style={{ color: '#6B6760' }}>{item.r}</span>
                    </div>
                    <span className="text-[11px] font-medium" style={{ color: item.c }}>{item.p}</span>
                  </Link>
                ))}
              </div>
            </div>

            {/* Social Sentiment */}
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5' }}>
              <div className="flex items-center gap-1.5 px-2 py-1.5 border-b" style={{ borderColor: '#D9D3C5' }}>
                <MessageCircle className="w-3 h-3" style={{ color: '#6B6760' }} />
                <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#6B6760' }}>Social Sentiment</span>
              </div>
              <div className="p-2">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px]" style={{ color: '#6B6760' }}>Positive</span>
                  <span className="text-xs font-bold text-green-600">73%</span>
                </div>
                <div className="w-full h-1 rounded-full overflow-hidden" style={{ backgroundColor: '#E6E1D6' }}>
                  <div className="h-full rounded-full bg-green-500" style={{ width: '73%' }} />
                </div>
                <div className="flex items-center justify-between mt-1 text-[9px]"><span style={{ color: '#6B6760' }}>Mentions: 12.4K</span><span style={{ color: '#6B6760' }}>↑ 340%</span></div>
              </div>
            </div>

            {/* Whale Alerts */}
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5' }}>
              <div className="flex items-center gap-1.5 px-2 py-1.5 border-b" style={{ borderColor: '#D9D3C5' }}>
                <Activity className="w-3 h-3 text-blue-500" />
                <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#6B6760' }}>Whale Alerts</span>
              </div>
              <div className="px-1.5 py-1 space-y-0.5">
                {[{ a: '12,500 BTC moved', t: '12m ago' }, { a: '85,000 ETH accumulated', t: '34m ago' }, { a: '2.1M SOL staked', t: '1h ago' }].map((item, i) => (
                  <div key={i} className="flex items-center justify-between px-2 py-1.5 rounded-md">
                    <span className="text-[10px]">{item.a}</span>
                    <span className="text-[11px]" style={{ color: '#6B6760' }}>{item.t}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Signals */}
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5' }}>
              <div className="flex items-center gap-1.5 px-2 py-1.5 border-b" style={{ borderColor: '#D9D3C5' }}>
                <Zap className="w-3 h-3 text-[#E25A2B]" />
                <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#6B6760' }}>Recent Signals</span>
              </div>
              <div className="px-1.5 py-1 space-y-0.5">
                {[{ s: 'BTC', sig: 'BUY', conf: 87 }, { s: 'SOL', sig: 'BUY', conf: 84 }, { s: 'AVAX', sig: 'BUY', conf: 91 }, { s: 'DOGE', sig: 'SELL', conf: 72 }].map(item => (
                  <Link key={item.s} href={`/markets/${item.s.toLowerCase()}`} className="flex items-center justify-between px-2 py-1.5 rounded-md hover:bg-black/[0.02]">
                    <span className="text-[11px] font-medium">{item.s}</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] font-bold px-1 py-0.5 rounded" style={{ backgroundColor: `${signalColors[item.sig as Signal]}15`, color: signalColors[item.sig as Signal] }}>{item.sig}</span>
                      <span className="text-[11px] font-mono" style={{ color: '#6B6760' }}>{item.conf}%</span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════ BOTTOM: Newsletter + Footer ═══════════ */}
      <div className="w-full px-1.5 lg:px-2 mt-6" style={{ maxWidth: 1800, margin: '0 auto' }}>
        {/* Newsletter */}
        <div className="rounded-lg border overflow-hidden" style={{ borderColor: '#D9D3C5', backgroundColor: '#0E0E0C' }}>
          <div className="max-w-xl mx-auto text-center py-8 px-5">
            <h2 className="text-lg font-bold text-[#F4F1EA] mb-1">Stay Ahead of the Market</h2>
            <p className="text-xs mb-4" style={{ color: '#999' }}>Weekly crypto insights, AI analysis, and top opportunities.</p>
            <div className="flex max-w-sm mx-auto gap-2">
              <input type="email" placeholder="Enter your email" className="flex-1 px-3 py-2 text-xs rounded-md outline-none" style={{ backgroundColor: '#1a1a1a', color: '#F4F1EA', border: '1px solid #333' }} />
              <button className="px-4 py-2 text-xs font-semibold rounded-md text-white" style={{ backgroundColor: '#E25A2B' }}>Subscribe</button>
            </div>
            <p className="text-[9px] mt-2" style={{ color: '#666' }}>No spam. Unsubscribe anytime.</p>
          </div>
        </div>

        {/* Trending Assets */}
        <div className="mt-6">
          <h3 className="text-sm font-bold mb-3">Trending Assets</h3>
          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {[...COINS].sort((a, b) => b.change24h - a.change24h).slice(0, 8).map(c => (
              <Link key={c.symbol} href={`/markets/${c.symbol.toLowerCase()}`} className="flex items-center gap-2 px-3 py-2 rounded-lg border shrink-0 transition-colors hover:bg-black/[0.02]" style={{ borderColor: '#D9D3C5' }}>
                <CryptoIcon symbol={c.symbol} size={20} />
                <div><div className="text-[11px] font-medium">{c.symbol}</div><div className="text-[9px] font-medium" style={{ color: pctColor(c.change24h) }}>+{c.change24h.toFixed(2)}%</div></div>
              </Link>
            ))}
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-8 pt-6 pb-8 border-t" style={{ borderColor: '#D9D3C5' }}>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            <div>
              <span className="text-base font-bold tracking-tight" style={{ fontFamily: "'Archivo Black', sans-serif" }}><span className="text-black">SILVER</span><span className="text-[#E25A2B]">TRADE</span></span>
              <p className="text-[11px] mt-1.5" style={{ color: '#6B6760' }}>AI-powered crypto market intelligence.</p>
            </div>
            {[{ t: 'Products', l: ['Market Data', 'AI Signals', 'Portfolio', 'API'] }, { t: 'Company', l: ['About', 'Careers', 'Blog', 'Press'] }, { t: 'Support', l: ['Help Center', 'Docs', 'Community', 'Contact'] }].map(col => (
              <div key={col.t}><h4 className="text-[10px] font-semibold uppercase tracking-wider mb-2.5" style={{ color: '#6B6760' }}>{col.t}</h4><ul className="space-y-1.5">{col.l.map(l => <li key={l}><a href="#" className="text-[11px] transition-colors hover:text-[#E25A2B]" style={{ color: '#0E0E0C' }}>{l}</a></li>)}</ul></div>
            ))}
          </div>
          <div className="mt-6 pt-4 border-t flex flex-col sm:flex-row items-center justify-between gap-3" style={{ borderColor: '#D9D3C5' }}>
            <p className="text-[10px]" style={{ color: '#6B6760' }}>© 2026 SilverTrade. All rights reserved.</p>
            <div className="flex items-center gap-3">{['Terms', 'Privacy', 'Cookies'].map(item => <a key={item} href="#" className="text-[10px] transition-colors hover:text-[#E25A2B]" style={{ color: '#6B6760' }}>{item}</a>)}</div>
          </div>
        </footer>

        {/* Bottom padding */}
        <div className="h-6" />
      </div>
    </div>
  )
}
