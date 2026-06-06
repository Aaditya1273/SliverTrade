'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { Search, Loader2, X } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { PLATFORM } from '@/lib/api-config'

interface SymbolResult {
  symbol: string
  exchange: string
  name?: string
  instrument_type?: string
  lot_size?: number
}

interface SymbolSearchProps {
  onSelect: (symbol: SymbolResult) => void
  placeholder?: string
  defaultExchange?: string
}

/**
 * Debounced symbol search component.
 *
 * Fetches matching symbols from the Platform's symbol search API.
 * NOTE: POST /api/v1/search may not exist on the Platform yet.
 *       It needs to be added — either as a route that queries the
 *       master_contract_cache for the user's connected broker, or
 *       using the existing symbol_utils search functions.
 * Results appear in a dropdown below the input.
 * Selected symbols are passed back via onSelect callback.
 */
export function SymbolSearch({
  onSelect,
  placeholder = 'Search symbols...',
  defaultExchange = 'NSE',
}: SymbolSearchProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SymbolResult[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [selectedExchange, setSelectedExchange] = useState(defaultExchange)
  const { apiKey } = useAuth()
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const exchanges = ['NSE', 'BSE', 'NFO', 'MCX', 'CRYPTO']

  const searchSymbols = useCallback(async (q: string, exchange: string) => {
    if (!q || q.length < 1) {
      setResults([])
      setIsOpen(false)
      return
    }

    setLoading(true)
    try {
      const response = await fetch(PLATFORM('/api/v1/search'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ query: q, exchange, ...(apiKey ? { apikey: apiKey } : {}) }),
      })
      const data = await response.json()
      const symbols = data?.data ?? data?.symbols ?? data?.results ?? []
      setResults(Array.isArray(symbols) ? symbols.slice(0, 10) : [])
      setIsOpen(true)
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (query.length < 1) {
      setResults([])
      setIsOpen(false)
      return
    }
    debounceRef.current = setTimeout(() => {
      searchSymbols(query, selectedExchange)
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query, selectedExchange, searchSymbols])

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (symbol: SymbolResult) => {
    onSelect(symbol)
    setQuery(`${symbol.symbol}`)
    setIsOpen(false)
  }

  const clearSearch = () => {
    setQuery('')
    setResults([])
    setIsOpen(false)
    inputRef.current?.focus()
  }

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
        <Input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className="pl-9 pr-8 bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50 text-sm"
          onFocus={() => { if (results.length > 0) setIsOpen(true) }}
        />
        {query && (
          <button onClick={clearSearch} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <X className="w-4 h-4" />}
          </button>
        )}
      </div>

      {/* Exchange filter */}
      <div className="flex gap-1 mt-2">
        {exchanges.map(ex => (
          <button
            key={ex}
            onClick={() => { setSelectedExchange(ex); setQuery('') }}
            className={`px-2 py-0.5 text-[10px] rounded font-medium uppercase tracking-wider transition-colors ${
              selectedExchange === ex
                ? 'bg-accent/20 text-accent'
                : 'text-muted-foreground hover:text-foreground border border-border'
            }`}
          >
            {ex}
          </button>
        ))}
      </div>

      {/* Results dropdown */}
      {isOpen && results.length > 0 && (
        <div className="absolute z-50 top-full mt-1 left-0 right-0 bg-card border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {results.map((result, i) => (
            <button
              key={`${result.symbol}-${result.exchange}-${i}`}
              onClick={() => handleSelect(result)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-accent/10 transition-colors text-left border-b border-border/50 last:border-b-0"
            >
              <div>
                <span className="font-medium text-sm">{result.symbol}</span>
                {result.name && (
                  <span className="text-xs text-muted-foreground ml-2">{result.name}</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider bg-card/50 px-1.5 py-0.5 rounded">
                  {result.exchange}
                </span>
                {result.instrument_type && (
                  <span className="text-[10px] text-muted-foreground">{result.instrument_type}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* No results */}
      {isOpen && query.length >= 1 && !loading && results.length === 0 && (
        <div className="absolute z-50 top-full mt-1 left-0 right-0 bg-card border border-border rounded-lg shadow-lg p-4 text-center">
          <p className="text-sm text-muted-foreground">No symbols found for &quot;{query}&quot;</p>
        </div>
      )}
    </div>
  )
}
