'use client'

import { useState, useMemo, useEffect } from 'react'
import Link from 'next/link'
import {
  Search, TrendingUp, TrendingDown, BarChart3, Bell, Bookmark, Users, Brain, Menu, X,
  ArrowRight, ChevronLeft, ChevronRight, ChevronUp, ChevronDown, ExternalLink,
  Info, ArrowUpDown, Filter, LayoutGrid, Newspaper, Sparkles, Flame,
} from 'lucide-react'
import { COINS } from '@/lib/market-data'
import CryptoIcon from '@/components/CryptoIcon'
import { MiniSparkline, formatCompact, formatPrice, pctColor } from '@/lib/market-utils'

// ── Generate 120 coins from the 20 base coins ────────────────────────
// (loosely typed on purpose — this is mock/demo data generation)

const ALL_COINS: any[] = (() => {
  const result: any[] = [...COINS]
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
    const price = base.price * (0.01 + Math.random() * 3)
    const marketCap = base.marketCap * (0.0001 + Math.random() * 1.5)
    const supplyEst = marketCap / price
    const capped = i % 3 === 0
    result.push({
      rank,
      name: names[nameIdx],
      symbol: symbols[nameIdx],
      icon: String.fromCodePoint(0x1F7E0 + (i % 6)),
      price,
      marketCap,
      change1h: -5 + Math.random() * 10,
      change24h: -15 + Math.random() * 30,
      change7d: -30 + Math.random() * 60,
      volume24h: base.volume24h * (0.001 + Math.random() * 2),
      liquidity: 30 + Math.random() * 60,
      aiSignal: (['BUY', 'SELL', 'WAIT'] as const)[Math.floor(Math.random() * 3)],
      confidence: 40 + Math.random() * 55,
      trend: (['bullish', 'neutral', 'bearish'] as const)[Math.floor(Math.random() * 3)],
      sparklineData: Array.from({ length: 10 }, () => base.price * (0.8 + Math.random() * 0.4)),
      // ~1 in 3 synthetic coins gets a capped max supply, like real capped-supply assets
      maxSupply: capped ? supplyEst * (1.1 + (i % 5) * 0.15) : undefined,
    })
  }
  return result
})()

type TabKey = 'all' | 'trending' | 'gainers' | 'losers' | 'mostVisited' | 'new'
type SortKey = 'rank' | 'name' | 'price' | 'change1h' | 'change24h' | 'change7d' | 'marketCap' | 'volume24h' | 'supply'

const TAB_DEFAULT_SORT: Record<TabKey, { key: SortKey; dir: 'asc' | 'desc' }> = {
  all: { key: 'rank', dir: 'asc' },
  trending: { key: 'volume24h', dir: 'desc' },
  gainers: { key: 'change24h', dir: 'desc' },
  losers: { key: 'change24h', dir: 'asc' },
  mostVisited: { key: 'volume24h', dir: 'desc' },
  new: { key: 'rank', dir: 'desc' },
}

function getValue(c: any, key: SortKey): number | string {
  if (key === 'supply') return c.marketCap / c.price
  return c[key]
}

function tabFilter(list: any[], tab: TabKey) {
  switch (tab) {
    case 'gainers': return list.filter(c => c.change24h > 0)
    case 'losers': return list.filter(c => c.change24h < 0)
    case 'new': return list.filter(c => c.rank > 20)
    default: return list
  }
}

// Column padding helpers — tighter inner gaps between 1h/24h/7d so they
// read as one "performance" cluster, wider gaps on either side of it.
const TIGHT = { paddingLeft: 8, paddingRight: 8 }
const TIGHT_END = { paddingLeft: 8, paddingRight: 20 }
const ZONE_START = { paddingRight: 20 }
const ZONE_END = { paddingLeft: 20 }

export default function MarketsPage() {
  const [search, setSearch] = useState('')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [hoveredRow, setHoveredRow] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<TabKey>('all')
  const [page, setPage] = useState(1)
  const [rowsPerPage, setRowsPerPage] = useState(50)
  const [starred, setStarred] = useState<Set<string>>(new Set())
  const [sortOverride, setSortOverride] = useState<{ key: SortKey; dir: 'asc' | 'desc' } | null>(null)
  const [openMenu, setOpenMenu] = useState<'filters' | 'columns' | null>(null)
  const [hideLowLiquidity, setHideLowLiquidity] = useState(false)
  const [pillDismissed, setPillDismissed] = useState(false)
  const [visibleCols, setVisibleCols] = useState({ marketCap: true, volume: true, supply: true, chart: true })

  const activeSort = sortOverride || TAB_DEFAULT_SORT[activeTab]

  const baseFiltered = useMemo(() => tabFilter(ALL_COINS, activeTab), [activeTab])

  const searched = useMemo(() => {
    if (!search.trim()) return baseFiltered
    const q = search.toLowerCase()
    return baseFiltered.filter(c => c.name.toLowerCase().includes(q) || c.symbol.toLowerCase().includes(q))
  }, [search, baseFiltered])

  const filteredFinal = useMemo(() => {
    if (!hideLowLiquidity) return searched
    return searched.filter(c => c.liquidity >= 50)
  }, [searched, hideLowLiquidity])

  const sortedFinal = useMemo(() => {
    const list = [...filteredFinal]
    const { key, dir } = activeSort
    list.sort((a, b) => {
      const av = getValue(a, key), bv = getValue(b, key)
      if (typeof av === 'string') return dir === 'asc' ? av.localeCompare(bv as string) : (bv as string).localeCompare(av)
      return dir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number)
    })
    return list
  }, [filteredFinal, activeSort])

  const totalPages = Math.max(1, Math.ceil(sortedFinal.length / rowsPerPage))
  const paged = sortedFinal.slice((page - 1) * rowsPerPage, page * rowsPerPage)

  const indexStats = useMemo(() => {
    const top20 = ALL_COINS.slice(0, 20)
    const totalMcap = top20.reduce((s, c) => s + c.marketCap, 0)
    const totalVol = top20.reduce((s, c) => s + c.volume24h, 0)
    const w1h = top20.reduce((s, c) => s + c.change1h * c.marketCap, 0) / totalMcap
    const w24h = top20.reduce((s, c) => s + c.change24h * c.marketCap, 0) / totalMcap
    const w7d = top20.reduce((s, c) => s + c.change7d * c.marketCap, 0) / totalMcap
    return { totalMcap, totalVol, w1h, w24h, w7d, price: 1000 * (1 + w7d / 100), spark: top20[0]?.sparklineData }
  }, [])

  useEffect(() => { setPage(1) }, [search, activeTab, rowsPerPage, hideLowLiquidity])
  useEffect(() => { setSortOverride(null) }, [activeTab])

  const toggleStar = (sym: string) => {
    const next = new Set(starred)
    if (next.has(sym)) next.delete(sym)
    else next.add(sym)
    setStarred(next)
  }

  const handleSort = (key: SortKey) => {
    setSortOverride(prev =>
      prev && prev.key === key
        ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
        : { key, dir: key === 'name' ? 'asc' : 'desc' }
    )
  }

  const PILLS = [
    { icon: Brain, text: 'Ask AI: why is the market down today?' },
    { icon: TrendingDown, text: "Today's top losers, ranked by 24h drop" },
    { icon: Bell, text: 'Set a price alert for your watchlist' },
  ]

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

        {/* ═══════════ MARKET STATS + GAUGES (mirrors CMC's mixed stat-card row) ═══════════ */}
        <div className="flex flex-col sm:flex-row gap-px mb-5 rounded-xl overflow-hidden border" style={{ borderColor: '#D9D3C5', backgroundColor: '#D9D3C5' }}>
          <StatCard className="flex-1 min-w-[150px]" label="Total Market Cap" value="$3.42T" sub="▲ 2.3%" color="#16a34a" spark={ALL_COINS[0]?.sparklineData} />
          <StatCard className="flex-1 min-w-[150px]" label="24h Volume" value="$124.8B" sub="▼ 1.2%" color="#dc2626" spark={ALL_COINS[2]?.sparklineData} />
          <GaugeCard className="flex-[1.5] min-w-[180px]" title="Fear &amp; Greed" pct={19} displayValue="19" sublabel="Extreme Fear"
            leftLabel="Fear" rightLabel="Greed" colors={['#dc2626', '#E25A2B', '#16a34a']} gradientId="gaugeFG" />
          <GaugeCard className="flex-[1.5] min-w-[180px]" title="Altcoin Season" pct={46} displayValue="46/100" sublabel="Neutral"
            leftLabel="Bitcoin" rightLabel="Altcoin" colors={['#E25A2B', '#D9D3C5', '#0E0E0C']} gradientId="gaugeAlt" />
          <GaugeCard className="flex-[1.5] min-w-[180px]" title="Average RSI" pct={44.32} displayValue="44.32" sublabel="Neutral"
            leftLabel="Oversold" rightLabel="Overbought" colors={['#16a34a', '#D9D3C5', '#dc2626']} gradientId="gaugeRSI" />
          <NewsCard className="flex-[1.7] min-w-[200px]" />
        </div>

        {/* ═══════════ INSIGHT PILL STRIP ═══════════ */}
        <div className="flex items-center gap-2 mb-5 overflow-x-auto pb-0.5">
          {!pillDismissed && (
            <div className="flex items-center gap-1.5 pl-3 pr-2 py-1.5 text-xs font-semibold rounded-full whitespace-nowrap shrink-0 text-white" style={{ backgroundColor: '#0E0E0C' }}>
              <Sparkles className="w-3 h-3" style={{ color: '#E25A2B' }} />
              New: AI Signal Engine is live
              <button onClick={() => setPillDismissed(true)} aria-label="Dismiss" className="ml-1 p-0.5 rounded hover:bg-white/10">
                <X className="w-3 h-3 opacity-70" />
              </button>
            </div>
          )}
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap shrink-0 border transition-colors hover:bg-black/5"
            style={{ backgroundColor: 'rgba(226,90,43,0.1)', borderColor: '#E25A2B', color: '#E25A2B' }}>
            <Flame className="w-3 h-3" />BTC reclaims $62K as momentum builds
          </button>
          {PILLS.map((p, i) => {
            const Icon = p.icon
            return (
              <button key={i}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap shrink-0 border transition-colors hover:bg-black/5"
                style={{ borderColor: '#D9D3C5', color: '#6B6760' }}>
                <Icon className="w-3 h-3" />{p.text}
              </button>
            )
          })}
        </div>

        {/* ═══════════ CATEGORY TABS + FILTERS/COLUMNS ═══════════ */}
        <div className="flex items-center gap-2 mb-5">
          <div className="flex items-center gap-1 overflow-x-auto flex-1">
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
                  activeTab === tab.key ? 'text-white' : 'text-[#6B6760] hover:text-[#0E0E0C] hover:bg-black/5'
                }`}
                style={activeTab === tab.key ? { backgroundColor: '#0E0E0C' } : {}}>
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 shrink-0 relative">
            <div className="relative">
              <button onClick={() => setOpenMenu(openMenu === 'filters' ? null : 'filters')}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border transition-colors hover:bg-black/5"
                style={{ borderColor: '#D9D3C5', color: hideLowLiquidity ? '#E25A2B' : '#6B6760' }}>
                <Filter className="w-3.5 h-3.5" /> Filters
              </button>
              {openMenu === 'filters' && (
                <>
                  <div className="fixed inset-0 z-20" onClick={() => setOpenMenu(null)} />
                  <div className="absolute right-0 top-full mt-1.5 w-60 rounded-lg border shadow-lg z-30 p-3" style={{ backgroundColor: '#F4F1EA', borderColor: '#D9D3C5' }}>
                    <label className="flex items-center gap-2 text-xs font-medium cursor-pointer" style={{ color: '#0E0E0C' }}>
                      <input type="checkbox" checked={hideLowLiquidity} onChange={e => setHideLowLiquidity(e.target.checked)} />
                      Hide low-liquidity assets
                    </label>
                  </div>
                </>
              )}
            </div>
            <div className="relative">
              <button onClick={() => setOpenMenu(openMenu === 'columns' ? null : 'columns')}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border transition-colors hover:bg-black/5"
                style={{ borderColor: '#D9D3C5', color: '#6B6760' }}>
                <LayoutGrid className="w-3.5 h-3.5" /> Columns
              </button>
              {openMenu === 'columns' && (
                <>
                  <div className="fixed inset-0 z-20" onClick={() => setOpenMenu(null)} />
                  <div className="absolute right-0 top-full mt-1.5 w-52 rounded-lg border shadow-lg z-30 p-3 space-y-2" style={{ backgroundColor: '#F4F1EA', borderColor: '#D9D3C5' }}>
                    {([['marketCap', 'Market Cap'], ['volume', 'Volume (24h)'], ['supply', 'Circulating Supply'], ['chart', 'Chart (7d)']] as const).map(([k, l]) => (
                      <label key={k} className="flex items-center gap-2 text-xs font-medium cursor-pointer" style={{ color: '#0E0E0C' }}>
                        <input type="checkbox" checked={visibleCols[k]} onChange={e => setVisibleCols(v => ({ ...v, [k]: e.target.checked }))} />
                        {l}
                      </label>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* ═══════════ MARKET TABLE ═══════════ */}
        <div className="rounded-xl overflow-hidden border" style={{ borderColor: '#D9D3C5' }}>
          <div className="overflow-x-auto">
            <table className="w-full" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr className="sticky top-14 z-20 text-[11px] font-semibold uppercase tracking-wider"
                  style={{ backgroundColor: '#F4F1EA', color: '#6B6760' }}>
                  <TH>#</TH>
                  <TH align="left" sortKey="name" activeSort={activeSort} onSort={handleSort}>Name</TH>
                  <TH />
                  <TH align="right" sortKey="price" activeSort={activeSort} onSort={handleSort} style={ZONE_START}>Price</TH>
                  <TH align="right" sortKey="change1h" activeSort={activeSort} onSort={handleSort} style={TIGHT}>1h</TH>
                  <TH align="right" sortKey="change24h" activeSort={activeSort} onSort={handleSort} style={TIGHT}>24h</TH>
                  <TH align="right" sortKey="change7d" activeSort={activeSort} onSort={handleSort} style={TIGHT_END}>7d</TH>
                  {visibleCols.marketCap && (
                    <TH align="right" className="hidden md:table-cell" sortKey="marketCap" activeSort={activeSort} onSort={handleSort} style={ZONE_END} info="Total value of all coins currently in circulation">Market Cap</TH>
                  )}
                  {visibleCols.volume && (
                    <TH align="right" className="hidden lg:table-cell" sortKey="volume24h" activeSort={activeSort} onSort={handleSort} info="Total traded value across exchanges in the last 24h">Volume(24h)</TH>
                  )}
                  {visibleCols.supply && (
                    <TH align="right" className="hidden xl:table-cell" sortKey="supply" activeSort={activeSort} onSort={handleSort} info="Coins currently in public circulation, vs. max supply where capped">Circulating Supply</TH>
                  )}
                  {visibleCols.chart && (
                    <TH align="right" className="hidden sm:table-cell">Chart (7d)</TH>
                  )}
                </tr>
              </thead>
              <tbody>
                {/* ─── Pinned composite index row, CMC-style ─── */}
                {page === 1 && activeTab === 'all' && !search.trim() && (
                  <tr className="cursor-default text-sm" style={{ backgroundColor: 'rgba(226,90,43,0.06)', borderBottom: '1px solid', borderColor: '#D9D3C5' }}>
                    <TD><BarChart3 className="w-3.5 h-3.5 mx-auto" style={{ color: '#E25A2B' }} /></TD>
                    <TD align="left">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0" style={{ backgroundColor: '#E25A2B' }}>20</div>
                        <div>
                          <div className="font-semibold text-[13px]" style={{ color: '#0E0E0C' }}>ST20</div>
                          <div className="text-[11px]" style={{ color: '#6B6760' }}>SilverTrade Composite Index</div>
                        </div>
                      </div>
                    </TD>
                    <TD />
                    <TD align="right" style={ZONE_START}><span className="font-semibold text-[13px]" style={{ color: '#0E0E0C' }}>{formatPrice(indexStats.price)}</span></TD>
                    <TD align="right" style={TIGHT}><PctCell value={indexStats.w1h} /></TD>
                    <TD align="right" style={TIGHT}><PctCell value={indexStats.w24h} /></TD>
                    <TD align="right" style={TIGHT_END}><PctCell value={indexStats.w7d} /></TD>
                    {visibleCols.marketCap && <TD align="right" className="hidden md:table-cell" style={ZONE_END}><span className="text-xs" style={{ color: '#6B6760' }}>{formatCompact(indexStats.totalMcap)}</span></TD>}
                    {visibleCols.volume && <TD align="right" className="hidden lg:table-cell"><span className="text-xs" style={{ color: '#6B6760' }}>{formatCompact(indexStats.totalVol)}</span></TD>}
                    {visibleCols.supply && <TD align="right" className="hidden xl:table-cell"><span className="text-xs" style={{ color: '#6B6760' }}>—</span></TD>}
                    {visibleCols.chart && <TD align="right" className="hidden sm:table-cell"><div className="flex justify-end">{indexStats.spark && <MiniSparkline data={indexStats.spark} />}</div></TD>}
                  </tr>
                )}

                {paged.map((coin, idx) => {
                  const globalIdx = (page - 1) * rowsPerPage + idx
                  const supply = coin.marketCap / coin.price
                  const supplyPct = coin.maxSupply ? Math.min(100, (supply / coin.maxSupply) * 100) : null
                  return (
                    <tr key={`${coin.symbol}-${globalIdx}`}
                      className="cursor-pointer transition-colors text-sm"
                      style={{
                        backgroundColor: hoveredRow === globalIdx ? 'rgba(0,0,0,0.03)' : 'transparent',
                        borderBottom: globalIdx < sortedFinal.length - 1 ? '1px solid' : 'none',
                        borderColor: '#D9D3C5',
                      }}
                      onMouseEnter={() => setHoveredRow(globalIdx)}
                      onMouseLeave={() => setHoveredRow(null)}
                      onClick={() => window.location.href = `/markets/${coin.symbol.toLowerCase()}`}
                    >
                      <TD>
                        <div className="flex items-center gap-2">
                          <button onClick={(e) => { e.stopPropagation(); toggleStar(coin.symbol) }}
                            aria-label="Toggle watchlist"
                            className="p-1 -m-1 rounded hover:bg-black/10 transition-colors shrink-0">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill={starred.has(coin.symbol) ? '#E25A2B' : 'none'}
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
                      <TD>
                        <button onClick={(e) => e.stopPropagation()}
                          className="px-4 py-1 text-xs font-semibold rounded-md border transition-colors hover:bg-[#E25A2B] hover:text-white"
                          style={{ borderColor: '#E25A2B', color: '#E25A2B' }}>
                          Buy
                        </button>
                      </TD>
                      <TD align="right" style={ZONE_START}>
                        <span className="font-semibold text-[13px]" style={{ color: '#0E0E0C' }}>{formatPrice(coin.price)}</span>
                      </TD>
                      <TD align="right" style={TIGHT}><PctCell value={coin.change1h} /></TD>
                      <TD align="right" style={TIGHT}><PctCell value={coin.change24h} /></TD>
                      <TD align="right" style={TIGHT_END}><PctCell value={coin.change7d} /></TD>
                      {visibleCols.marketCap && (
                        <TD align="right" className="hidden md:table-cell" style={ZONE_END}>
                          <span className="text-xs" style={{ color: '#6B6760' }}>{formatCompact(coin.marketCap)}</span>
                        </TD>
                      )}
                      {visibleCols.volume && (
                        <TD align="right" className="hidden lg:table-cell">
                          <span className="text-xs" style={{ color: '#6B6760' }}>{formatCompact(coin.volume24h)}</span>
                        </TD>
                      )}
                      {visibleCols.supply && (
                        <TD align="right" className="hidden xl:table-cell">
                          <div className="flex flex-col items-end gap-1">
                            <span className="text-xs font-mono" style={{ color: '#6B6760' }}>
                              {supply > 1e9 ? `${(supply / 1e9).toFixed(2)}B` : supply > 1e6 ? `${(supply / 1e6).toFixed(2)}M` : `${(supply / 1e3).toFixed(1)}K`} {coin.symbol}
                            </span>
                            {supplyPct !== null && (
                              <div className="w-16 h-[3px] rounded-full overflow-hidden" style={{ backgroundColor: '#D9D3C5' }}>
                                <div className="h-full rounded-full" style={{ width: `${supplyPct}%`, backgroundColor: '#9B958A' }} />
                              </div>
                            )}
                          </div>
                        </TD>
                      )}
                      {visibleCols.chart && (
                        <TD align="right" className="hidden sm:table-cell">
                          <div className="flex justify-end">
                            <MiniSparkline data={coin.sparklineData} />
                          </div>
                        </TD>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* ═══════════ PAGINATION ═══════════ */}
        <div className="flex items-center justify-between mt-4 text-xs flex-wrap gap-3" style={{ color: '#6B6760' }}>
          <span>Showing {(page - 1) * rowsPerPage + 1} – {Math.min(page * rowsPerPage, sortedFinal.length)} of {sortedFinal.length} cryptocurrencies</span>
          <div className="flex items-center gap-3">
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
            <select value={rowsPerPage} onChange={e => setRowsPerPage(Number(e.target.value))}
              className="text-xs font-medium rounded-md border px-2 py-1.5 outline-none"
              style={{ borderColor: '#D9D3C5', color: '#0E0E0C', backgroundColor: '#F4F1EA' }}>
              <option value={20}>Show 20</option>
              <option value={50}>Show 50</option>
              <option value={100}>Show 100</option>
            </select>
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
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-8">
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
              { title: 'Socials', links: ['X (Twitter)', 'Discord', 'Telegram', 'Reddit'] },
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

function StatCard({ label, value, sub, color, spark, className }: { label: string; value: string; sub: string; color: string; spark?: number[]; className?: string }) {
  return (
    <div className={`min-w-0 px-3.5 py-3 flex flex-col justify-between ${className || ''}`} style={{ backgroundColor: '#F4F1EA' }}>
      <div>
        <div className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: '#6B6760' }}>{label}</div>
        <div className="text-sm font-bold" style={{ color: '#0E0E0C' }}>{value}</div>
        <div className="text-[11px] mt-0.5" style={{ color }}>{sub}</div>
      </div>
      {spark && <div className="mt-1.5"><MiniSparkline data={spark} /></div>}
    </div>
  )
}

function GaugeDial({ pct, displayValue, sublabel, leftLabel, rightLabel, colors, gradientId }: {
  pct: number; displayValue: string; sublabel: string; leftLabel: string; rightLabel: string; colors: string[]; gradientId: string
}) {
  const clamped = Math.max(0, Math.min(100, pct))
  const angle = 180 - (clamped / 100) * 180
  const rad = (angle * Math.PI) / 180
  const cx = 100, cy = 92, r = 76
  const dotX = cx + r * Math.cos(rad)
  const dotY = cy - r * Math.sin(rad)
  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 100" className="w-full" style={{ maxWidth: 170 }}>
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
            {colors.map((c, i) => <stop key={i} offset={`${(i / (colors.length - 1)) * 100}%`} stopColor={c} />)}
          </linearGradient>
        </defs>
        <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`} fill="none" stroke={`url(#${gradientId})`} strokeWidth="9" strokeLinecap="round" />
        <circle cx={dotX} cy={dotY} r="5.5" fill="#0E0E0C" stroke="#F4F1EA" strokeWidth="2" />
      </svg>
      <div className="text-center -mt-3">
        <div className="text-base font-bold leading-none" style={{ color: '#0E0E0C' }}>{displayValue}</div>
        <div className="text-[9px] mt-1" style={{ color: '#6B6760' }}>{sublabel}</div>
      </div>
      <div className="flex justify-between w-full text-[8px] font-medium uppercase tracking-wide mt-1" style={{ color: '#9B958A', maxWidth: 170 }}>
        <span>{leftLabel}</span><span>{rightLabel}</span>
      </div>
    </div>
  )
}

function GaugeCard({ className, title, pct, displayValue, sublabel, leftLabel, rightLabel, colors, gradientId }: {
  className?: string; title: string; pct: number; displayValue: string; sublabel: string; leftLabel: string; rightLabel: string; colors: string[]; gradientId: string
}) {
  return (
    <div className={`px-3.5 py-3 flex flex-col ${className || ''}`} style={{ backgroundColor: '#F4F1EA' }}>
      <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider mb-0.5" style={{ color: '#6B6760' }}>
        <span>{title}</span><ChevronRight className="w-3 h-3" />
      </div>
      <GaugeDial pct={pct} displayValue={displayValue} sublabel={sublabel} leftLabel={leftLabel} rightLabel={rightLabel} colors={colors} gradientId={gradientId} />
    </div>
  )
}

function NewsCard({ className }: { className?: string }) {
  return (
    <div className={`px-3.5 py-3 flex flex-col justify-center gap-1.5 ${className || ''}`} style={{ backgroundColor: '#F4F1EA' }}>
      <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#E25A2B' }}>
        <Newspaper className="w-3 h-3" /> Market News <span className="font-normal normal-case" style={{ color: '#9B958A' }}>· 7h ago</span>
      </div>
      <div className="text-xs font-medium leading-snug" style={{ color: '#0E0E0C' }}>Fed signals possible rate pause as crypto inflows hit a 6-month high</div>
      <a href="#" className="flex items-center gap-1 text-[10px] font-semibold" style={{ color: '#E25A2B' }}>Read more <ArrowRight className="w-3 h-3" /></a>
    </div>
  )
}

function PctCell({ value }: { value: number }) {
  const positive = value >= 0
  return (
    <span className="inline-flex items-center gap-0.5 text-xs font-medium" style={{ color: pctColor(value) }}>
      {positive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      {Math.abs(value).toFixed(2)}%
    </span>
  )
}

function TH({ children, align, className, sortKey, activeSort, onSort, info, style }: {
  children?: React.ReactNode; align?: string; className?: string
  sortKey?: SortKey; activeSort?: { key: SortKey; dir: 'asc' | 'desc' }; onSort?: (key: SortKey) => void
  info?: string; style?: React.CSSProperties
}) {
  const isActive = !!sortKey && activeSort?.key === sortKey
  return (
    <th className={`sticky top-14 z-20 px-3 py-3 text-[11px] font-semibold uppercase tracking-wider select-none ${sortKey ? 'cursor-pointer' : ''} ${className || ''}`}
      style={{ backgroundColor: '#F4F1EA', color: isActive ? '#0E0E0C' : '#6B6760', textAlign: (align || 'center') as any, ...style }}
      onClick={sortKey && onSort ? () => onSort(sortKey) : undefined}>
      <span className="inline-flex items-center gap-1" style={{ justifyContent: align === 'right' ? 'flex-end' : align === 'left' ? 'flex-start' : 'center' }}>
        {children}
        {info && <span title={info}><Info className="w-3 h-3 opacity-50" /></span>}
        {sortKey && (
          isActive
            ? (activeSort!.dir === 'asc' ? <ChevronUp className="w-3 h-3" style={{ color: '#E25A2B' }} /> : <ChevronDown className="w-3 h-3" style={{ color: '#E25A2B' }} />)
            : <ArrowUpDown className="w-2.5 h-2.5 opacity-30" />
        )}
      </span>
    </th>
  )
}

function TD({ children, align, className, style }: { children?: React.ReactNode; align?: string; className?: string; style?: React.CSSProperties }) {
  return (
    <td className={`px-3 py-2.5 text-sm ${className || ''}`} style={{ textAlign: (align || 'center') as any, ...style }}>
      {children}
    </td>
  )
}