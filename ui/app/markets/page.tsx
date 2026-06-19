'use client'

import { useState, useMemo, useEffect } from 'react'
import Link from 'next/link'
import { Search, TrendingUp, TrendingDown, BarChart3, Bell, Bookmark, Users, Brain, Menu, X, ArrowRight, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react'
import { COINS } from '@/lib/market-data'
import CryptoIcon from '@/components/CryptoIcon'
import { MiniSparkline, formatCompact, formatPrice, pctColor } from '@/lib/market-utils'

// ── Generate 120 coins from the 20 base coins ────────────────────────

const ALL_COINS = (() => {
  const result = [...COINS]
  const names = [
    'Filecoin', 'Theta', 'Hedera', 'VeChain', 'Internet Computer', 'EOS', 'Algorand',
    'Quant', 'Flow', 'MultiversX', 'Tezos', 'Theta Fuel', 'Aave', 'Maker', 'Compound',
    'Synthetix', 'Yearn Finance', 'Curve DAO', 'Balancer', 'PancakeSwap',
    'SushiSwap', '1inch', 'dYdX', 'Gnosis', 'ENS', 'Chiliz', 'Enjin',
    'Decentraland', 'Sandbox', 'Axie Infinity', 'Gala', 'Illuvium',
    'Immutable X', 'Fetch.ai', 'SingularityNET', 'Ocean Protocol',
    'Render', 'Akash Network', 'Livepeer', 'Theta Network',
    'Celo', 'NEO', 'Ontology', 'IOST', 'Zilliqa', 'Harmony',
    'Cronos', 'Fantom', 'Moonbeam', 'Moonriver'
  ]
  const symbols = [
    'FIL', 'THETA', 'HBAR', 'VET', 'ICP', 'EOS', 'ALGO',
    'QNT', 'FLOW', 'EGLD', 'XTZ', 'TFUEL', 'AAVE', 'MKR', 'COMP',
    'SNX', 'YFI', 'CRV', 'BAL', 'CAKE', 'SUSHI', '1INCH', 'DYDX', 'GNO',
    'ENS', 'CHZ', 'ENJ', 'MANA', 'SAND', 'AXS', 'GALA', 'ILV',
    'IMX', 'FET', 'AGIX', 'OCEAN', 'RNDR', 'AKT', 'LPT', 'THETA',
    'CELO', 'NEO', 'ONT', 'IOST', 'ZIL', 'ONE',
    'CRO', 'FTM', 'GLMR', 'MOVR'
  ]
  for (let i = 0; i < 100; i++) {
    const base = result[i % result.length]
    const idx = result.length + i
    const nameIdx = i % names.length
    const rank = idx + 1
    const multiplier = 0.3 + Math.random() * 2.5
    result.push({
      rank,
      name: names[nameIdx],
      symbol: symbols[nameIdx],
      icon: String.fromCodePoint(0x1F7E0 + (i % 6)),
      price: base.price * (0.01 + Math.random() * 3),
      change1h: -5 + Math.random() * 10,
      change24h: -15 + Math.random() * 30,
      change7d: -30 + Math.random() * 60,
      volume24h: base.volume24h * (0.001 + Math.random() * 2),
      marketCap: base.marketCap * (0.0001 + Math.random() * 1.5),
      liquidity: 30 + Math.random() * 60,
      aiSignal: (['BUY', 'SELL', 'WAIT'] as const)[Math.floor(Math.random() * 3)],
      confidence: 40 + Math.random() * 55,
      trend: (['bullish', 'neutral', 'bearish'] as const)[Math.floor(Math.random() * 3)],
      sparklineData: Array.from({ length: 10 }, () => base.price * (0.8 + Math.random() * 0.4)),
    })
  }
  return result
})()

const ROWS_PER_PAGE = 50

export default function MarketsPage() {
  const [search, setSearch] = useState('')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [hoveredRow, setHoveredRow] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'all' | 'trending' | 'gainers' | 'losers' | 'mostVisited' | 'new'>('all')
  const [page, setPage] = useState(1)
  const [starred, setStarred] = useState<Set<string>>(new Set())

  const sorted = useMemo(() => {
    let list = [...ALL_COINS]
    switch (activeTab) {
      case 'trending':
        list.sort((a, b) => b.volume24h - a.volume24h)
        break
      case 'gainers':
        list.sort((a, b) => b.change24h - a.change24h)
        break
      case 'losers':
        list.sort((a, b) => a.change24h - b.change24h)
        break
      case 'mostVisited':
        list.sort((a, b) => b.volume24h - a.volume24h)
        break
      case 'new':
        list.sort((a, b) => b.rank - a.rank)
        list = list.slice(0, 100)
        break
      default:
        list.sort((a, b) => a.rank - b.rank)
    }
    return list
  }, [activeTab])

  const filtered = useMemo(() => {
    if (!search.trim()) return sorted
    const q = search.toLowerCase()
    return sorted.filter(c => c.name.toLowerCase().includes(q) || c.symbol.toLowerCase().includes(q))
  }, [search, sorted])

  const totalPages = Math.ceil(filtered.length / ROWS_PER_PAGE)
  const paged = filtered.slice((page - 1) * ROWS_PER_PAGE, page * ROWS_PER_PAGE)

  // Reset to page 1 on filter change
  useEffect(() => { setPage(1) }, [search, activeTab])

  const toggleStar = (sym: string) => {
    const next = new Set(starred)
    if (next.has(sym)) next.delete(sym)
    else next.add(sym)
    setStarred(next)
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#F4F1EA' }}>
      {/* ═══════════ TOP NAV ═══════════ */}
      <header className="sticky top-0 z-50 border-b" style={{ backgroundColor: '#F4F1EA', borderColor: '#D9D3C5' }}>
        <div className="w-full px-3 lg:px-4" style={{ maxWidth: 1800, margin: '0 auto' }}>
          <div className="flex items-center justify-between h-12">
            <Link href="/" className="flex items-center gap-2 shrink-0">
              <span className="text-xl font-bold tracking-tight" style={{ fontFamily: "'Archivo Black', sans-serif" }}>
                <span className="text-black">SILVER</span><span className="text-[#E25A2B]">TRADE</span>
              </span>
            </Link>
            <nav className="hidden lg:flex items-center gap-1">
              {[
                { href: '/markets', label: 'Markets', icon: BarChart3, active: true },
                { href: '/dashboard', label: 'Portfolio', icon: Users },
                { href: '/dashboard/watchlist', label: 'Watchlist', icon: Bookmark },
                { href: '/dashboard/chat', label: 'AI Signals', icon: Brain },
                { href: '/dashboard/settings/alerts', label: 'Alerts', icon: Bell },
              ].map(item => {
                const Icon = item.icon
                return (
                  <Link key={item.href} href={item.href}
                    className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors ${
                      item.active ? 'text-white bg-[#E25A2B]' : 'text-[#6B6760] hover:text-[#0E0E0C] hover:bg-black/5'
                    }`}>
                    <Icon className="w-4 h-4" />{item.label}
                  </Link>
                )
              })}
            </nav>
            <div className="flex items-center gap-2 lg:gap-3">
              <div className="hidden sm:block relative w-48 lg:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: '#6B6760' }} />
                <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search markets..."
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg outline-none"
                  style={{ backgroundColor: '#E6E1D6', color: '#0E0E0C' }} />
              </div>
              <Link href="/login" className="px-4 py-2 text-sm font-medium rounded-lg" style={{ color: '#6B6760' }}>Sign In</Link>
              <Link href="/signup" className="px-4 py-2 text-sm font-semibold rounded-lg text-white" style={{ backgroundColor: '#0E0E0C' }}>Get Started</Link>
              <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="lg:hidden p-2 rounded-lg hover:bg-black/5">
                {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
            </div>
          </div>
          {mobileMenuOpen && (
            <div className="lg:hidden pb-4 pt-2 border-t space-y-1" style={{ borderColor: '#D9D3C5' }}>
              {[{ href: '/markets', label: 'Markets', icon: BarChart3 }, { href: '/dashboard', label: 'Portfolio', icon: Users }, { href: '/dashboard/chat', label: 'AI Signals', icon: Brain }].map(item => {
                const Icon = item.icon
                return <Link key={item.href} href={item.href} className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium" style={{ color: '#6B6760' }}><Icon className="w-4 h-4" />{item.label}</Link>
              })}
            </div>
          )}
        </div>
      </header>

      <div className="w-full px-3 lg:px-4 py-4" style={{ maxWidth: 1800, margin: '0 auto' }}>
        {/* ═══════════ MARKET STATISTICS BAR ═══════════ */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-px mb-6 rounded-xl overflow-hidden border" style={{ borderColor: '#D9D3C5', backgroundColor: '#D9D3C5' }}>
          <StatCard label="Total Market Cap" value="$3.42T" sub="+2.3%" color="#16a34a" />
          <StatCard label="24h Volume" value="$124.8B" sub="-1.2%" color="#dc2626" />
          <StatCard label="BTC Dominance" value="51.2%" sub="+0.4%" color="#16a34a" />
          <StatCard label="ETH Dominance" value="16.8%" sub="-0.2%" color="#dc2626" />
          <StatCard label="Fear & Greed" value="72" sub="Greed" color="#16a34a" />
          <StatCard label="Active Coins" value="12,483" sub="+124 today" color="#16a34a" />
          <StatCard label="Total Exchanges" value="254" sub="+3 active" color="#16a34a" />
          <StatCard label="24h Liquidations" value="$342M" sub="Long: $218M" color="#dc2626" />
        </div>

        {/* ═══════════ TRENDING / CATEGORY TABS ═══════════ */}
        <div className="flex items-center gap-1 mb-5 overflow-x-auto">
          {([
            { key: 'all', label: 'All Cryptocurrencies' },
            { key: 'trending', label: 'Trending' },
            { key: 'gainers', label: 'Top Gainers' },
            { key: 'losers', label: 'Top Losers' },
            { key: 'mostVisited', label: 'Most Visited' },
            { key: 'new', label: 'Newly Added' },
          ] as const).map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-xs font-semibold rounded-lg whitespace-nowrap transition-colors ${
                activeTab === tab.key
                  ? 'text-white'
                  : 'text-[#6B6760] hover:text-[#0E0E0C] hover:bg-black/5'
              }`}
              style={activeTab === tab.key ? { backgroundColor: '#0E0E0C' } : {}}>
              {tab.label}
            </button>
          ))}
        </div>

        {/* ═══════════ MARKET TABLE (FULL WIDTH — NO SIDEBAR) ═══════════ */}
        <div className="rounded-xl overflow-hidden border" style={{ borderColor: '#D9D3C5' }}>
          <div className="overflow-x-auto">
            <table className="w-full" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr className="sticky top-14 z-20 text-[11px] font-semibold uppercase tracking-wider"
                  style={{ backgroundColor: '#F4F1EA', color: '#6B6760' }}>
                  <TH>#</TH>
                  <TH align="left">Name</TH>
                  <TH align="right">Price</TH>
                  <TH align="right">1h</TH>
                  <TH align="right">24h</TH>
                  <TH align="right">7d</TH>
                  <TH align="right" className="hidden md:table-cell">Market Cap</TH>
                  <TH align="right" className="hidden lg:table-cell">Volume (24h)</TH>
                  <TH align="right" className="hidden xl:table-cell">Circulating Supply</TH>
                  <TH align="right" className="hidden sm:table-cell">Chart (7d)</TH>
                </tr>
              </thead>
              <tbody>
                {paged.map((coin, idx) => {
                  const globalIdx = (page - 1) * ROWS_PER_PAGE + idx
                  const supply = (coin.marketCap / coin.price)
                  return (
                    <tr key={`${coin.symbol}-${globalIdx}`}
                      className="cursor-pointer transition-colors text-sm"
                      style={{
                        backgroundColor: hoveredRow === globalIdx ? 'rgba(0,0,0,0.03)' : 'transparent',
                        borderBottom: globalIdx < filtered.length - 1 ? '1px solid' : 'none',
                        borderColor: '#D9D3C5',
                      }}
                      onMouseEnter={() => setHoveredRow(globalIdx)}
                      onMouseLeave={() => setHoveredRow(null)}
                      onClick={() => window.location.href = `/markets/${coin.symbol.toLowerCase()}`}
                    >
                      <TD>
                        <div className="flex items-center gap-2">
                          <button onClick={(e) => { e.stopPropagation(); toggleStar(coin.symbol) }}
                            className="p-0.5 rounded hover:bg-black/10 transition-colors shrink-0">
                            <svg width="10" height="10" viewBox="0 0 24 24" fill={starred.has(coin.symbol) ? '#E25A2B' : 'none'}
                              stroke={starred.has(coin.symbol) ? '#E25A2B' : '#999'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                            </svg>
                          </button>
                          <span className="font-mono" style={{ color: '#6B6760' }}>{coin.rank}</span>
                        </div>
                      </TD>
                      <TD align="left">
                        <div className="flex items-center gap-2.5">
                          <CryptoIcon symbol={coin.symbol} size={28} />
                          <div>
                            <div className="font-semibold text-[13px]" style={{ color: '#0E0E0C' }}>{coin.symbol}</div>
                            <div className="text-[11px]" style={{ color: '#6B6760' }}>{coin.name}</div>
                          </div>
                        </div>
                      </TD>
                      <TD align="right">
                        <span className="font-semibold text-[13px]" style={{ color: '#0E0E0C' }}>{formatPrice(coin.price)}</span>
                      </TD>
                      <TD align="right">
                        <span className="text-xs font-medium" style={{ color: pctColor(coin.change1h) }}>
                          {coin.change1h >= 0 ? '+' : ''}{coin.change1h.toFixed(2)}%
                        </span>
                      </TD>
                      <TD align="right">
                        <span className="text-xs font-medium" style={{ color: pctColor(coin.change24h) }}>
                          {coin.change24h >= 0 ? '+' : ''}{coin.change24h.toFixed(2)}%
                        </span>
                      </TD>
                      <TD align="right">
                        <span className="text-xs font-medium" style={{ color: pctColor(coin.change7d) }}>
                          {coin.change7d >= 0 ? '+' : ''}{coin.change7d.toFixed(2)}%
                        </span>
                      </TD>
                      <TD align="right" className="hidden md:table-cell">
                        <span className="text-xs" style={{ color: '#6B6760' }}>{formatCompact(coin.marketCap)}</span>
                      </TD>
                      <TD align="right" className="hidden lg:table-cell">
                        <span className="text-xs" style={{ color: '#6B6760' }}>{formatCompact(coin.volume24h)}</span>
                      </TD>
                      <TD align="right" className="hidden xl:table-cell">
                        <span className="text-xs font-mono" style={{ color: '#6B6760' }}>
                          {supply > 1e9 ? `${(supply / 1e9).toFixed(2)}B` : supply > 1e6 ? `${(supply / 1e6).toFixed(2)}M` : `${(supply / 1e3).toFixed(1)}K`}
                        </span>
                      </TD>
                      <TD align="right" className="hidden sm:table-cell">
                        <div className="flex justify-end">
                          <MiniSparkline data={coin.sparklineData} />
                        </div>
                      </TD>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* ═══════════ PAGINATION ═══════════ */}
        <div className="flex items-center justify-between mt-4 text-xs" style={{ color: '#6B6760' }}>
          <span>Showing {(page - 1) * ROWS_PER_PAGE + 1} – {Math.min(page * ROWS_PER_PAGE, filtered.length)} of {filtered.length} cryptocurrencies</span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1}
              className="p-1.5 rounded-md transition-colors disabled:opacity-30 hover:bg-black/5">
              <ChevronLeft className="w-4 h-4" />
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const start = Math.max(1, Math.min(page - 2, totalPages - 4))
              const pageNum = start + i
              if (pageNum > totalPages) return null
              return (
                <button key={pageNum} onClick={() => setPage(pageNum)}
                  className={`w-7 h-7 rounded-md text-xs font-medium transition-colors ${
                    page === pageNum ? 'text-white' : 'hover:bg-black/5'
                  }`}
                  style={page === pageNum ? { backgroundColor: '#E25A2B' } : {}}>
                  {pageNum}
                </button>
              )
            })}
            <button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page >= totalPages}
              className="p-1.5 rounded-md transition-colors disabled:opacity-30 hover:bg-black/5">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* ═══════════ NEWSLETTER SECTION ═══════════ */}
        <div className="mt-12 rounded-xl border overflow-hidden" style={{ borderColor: '#D9D3C5', backgroundColor: '#0E0E0C' }}>
          <div className="max-w-2xl mx-auto text-center py-10 px-6">
            <h2 className="text-2xl font-bold text-[#F4F1EA] mb-2">Stay Ahead of the Market</h2>
            <p className="text-sm mb-6" style={{ color: '#999' }}>
              Get weekly crypto market insights, AI analysis, and top opportunities delivered to your inbox.
            </p>
            <div className="flex max-w-md mx-auto gap-2">
              <input type="email" placeholder="Enter your email"
                className="flex-1 px-4 py-2.5 text-sm rounded-lg outline-none"
                style={{ backgroundColor: '#1a1a1a', color: '#F4F1EA', border: '1px solid #333' }} />
              <button className="px-5 py-2.5 text-sm font-semibold rounded-lg text-white transition-all hover:opacity-90 shrink-0"
                style={{ backgroundColor: '#E25A2B' }}>
                Subscribe
              </button>
            </div>
            <p className="text-[10px] mt-3" style={{ color: '#666' }}>No spam. Unsubscribe anytime.</p>
          </div>
        </div>

        {/* ═══════════ COMMUNITY SECTION ═══════════ */}
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { title: 'Join Our Community', desc: 'Connect with 50,000+ traders in our Discord', icon: '💬', href: '#' },
            { title: 'Follow on Twitter', desc: 'Real-time market alerts and updates', icon: '🐦', href: '#' },
            { title: 'Read Our Blog', desc: 'In-depth market analysis and guides', icon: '📝', href: '#' },
          ].map(item => (
            <a key={item.title} href={item.href}
              className="flex items-center gap-4 p-4 rounded-xl border transition-all hover:bg-black/[0.02] group"
              style={{ borderColor: '#D9D3C5' }}>
              <span className="text-2xl shrink-0">{item.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold">{item.title}</div>
                <div className="text-xs mt-0.5" style={{ color: '#6B6760' }}>{item.desc}</div>
              </div>
              <ExternalLink className="w-4 h-4 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: '#6B6760' }} />
            </a>
          ))}
        </div>

        {/* ═══════════ FOOTER ═══════════ */}
        <footer className="mt-12 pt-8 pb-10 border-t" style={{ borderColor: '#D9D3C5' }}>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-8">
            <div>
              <span className="text-lg font-bold tracking-tight" style={{ fontFamily: "'Archivo Black', sans-serif" }}>
                <span className="text-black">SILVER</span><span className="text-[#E25A2B]">TRADE</span>
              </span>
              <p className="text-xs mt-2" style={{ color: '#6B6760' }}>AI-powered crypto market intelligence platform.</p>
            </div>
            {[
              { title: 'Products', links: ['Market Data', 'AI Signals', 'Portfolio Tracker', 'API Access'] },
              { title: 'Company', links: ['About', 'Careers', 'Blog', 'Press Kit'] },
              { title: 'Support', links: ['Help Center', 'Documentation', 'Community', 'Contact'] },
            ].map(col => (
              <div key={col.title}>
                <h4 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: '#6B6760' }}>{col.title}</h4>
                <ul className="space-y-2">
                  {col.links.map(link => (
                    <li key={link}>
                      <a href="#" className="text-xs transition-colors hover:text-[#E25A2B]" style={{ color: '#0E0E0C' }}>{link}</a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="mt-8 pt-6 border-t flex flex-col sm:flex-row items-center justify-between gap-4" style={{ borderColor: '#D9D3C5' }}>
            <p className="text-[11px]" style={{ color: '#6B6760' }}>© 2026 SilverTrade. All rights reserved.</p>
            <div className="flex items-center gap-4">
              {['Terms', 'Privacy', 'Cookies'].map(item => (
                <a key={item} href="#" className="text-[11px] transition-colors hover:text-[#E25A2B]" style={{ color: '#6B6760' }}>{item}</a>
              ))}
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}

// ── Sub-components ──────────────────────────────────────────────────

function StatCard({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div className="min-w-0 px-3.5 py-3" style={{ backgroundColor: '#F4F1EA' }}>
      <div className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: '#6B6760' }}>{label}</div>
      <div className="text-sm font-bold" style={{ color: '#0E0E0C' }}>{value}</div>
      <div className="text-[11px] mt-0.5" style={{ color }}>{sub}</div>
    </div>
  )
}

function TH({ children, align, className }: { children: React.ReactNode; align?: string; className?: string }) {
  return (
    <th className={`sticky top-14 z-20 px-3 py-3 text-[11px] font-semibold uppercase tracking-wider ${className || ''}`}
      style={{ backgroundColor: '#F4F1EA', color: '#6B6760', textAlign: (align || 'center') as any }}>
      {children}
    </th>
  )
}

function TD({ children, align, className }: { children: React.ReactNode; align?: string; className?: string }) {
  return (
    <td className={`px-3 py-2.5 text-sm ${className || ''}`} style={{ textAlign: (align || 'center') as any }}>
      {children}
    </td>
  )
}
