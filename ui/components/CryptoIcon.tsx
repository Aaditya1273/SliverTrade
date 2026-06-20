'use client'

import { useState } from 'react'

interface CryptoIconProps {
  symbol: string
  size?: number
  className?: string
  fallback?: string
}

const FALLBACK_CHARS: Record<string, string> = {
  BTC: '₿', ETH: '⟠', SOL: '◎', XRP: '✕', BNB: '◆',
  ADA: '₳', DOGE: 'Ð', AVAX: '◈', DOT: '●', LINK: '⬡',
  MATIC: '⬠', TON: '◇', SHIB: '🐕', LTC: 'Ł', UNI: '🦄',
  ARB: '▲', NEAR: '◆', APT: '◈', XLM: '✳',
}

export default function CryptoIcon({ symbol, size = 24, className = '', fallback }: CryptoIconProps) {
  const [error, setError] = useState(false)
  const src = `/crypto-logos/${symbol.toLowerCase()}.svg`

  if (error) {
    const fallbackChar = fallback || FALLBACK_CHARS[symbol.toUpperCase()] || symbol.charAt(0)
    return (
      <span
        className={`rounded-full flex items-center justify-center font-bold shrink-0 ${className}`}
        style={{
          width: size,
          height: size,
          backgroundColor: '#E6E1D6',
          color: '#0E0E0C',
          fontSize: size * 0.45,
        }}
      >
        {fallbackChar}
      </span>
    )
  }

  return (
    <img
      src={src}
      alt={symbol}
      width={size}
      height={size}
      className={`shrink-0 ${className}`}
      style={{ width: size, height: size, objectFit: 'contain' }}
      onError={() => setError(true)}
      loading="lazy"
    />
  )
}
