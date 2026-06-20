export type Signal = 'BUY' | 'SELL' | 'WAIT'
export type Trend = 'bullish' | 'neutral' | 'bearish'

export interface CoinData {
  rank: number
  name: string
  symbol: string
  icon: string
  price: number
  change1h: number
  change24h: number
  change7d: number
  volume24h: number
  marketCap: number
  liquidity: number
  aiSignal: Signal
  confidence: number
  trend: Trend
  sparklineData: number[]
}

export const COINS: CoinData[] = [
  { rank: 1, name: 'Bitcoin', symbol: 'BTC', icon: '₿', price: 67432.18, change1h: 0.42, change24h: 2.35, change7d: 4.71, volume24h: 28.4e9, marketCap: 1.32e12, liquidity: 98.2, aiSignal: 'BUY', confidence: 87, trend: 'bullish', sparklineData: [62100, 63400, 64200, 63800, 65100, 65800, 66400, 66100, 66800, 67432] },
  { rank: 2, name: 'Ethereum', symbol: 'ETH', icon: '⟠', price: 3456.72, change1h: -0.18, change24h: 1.82, change7d: 5.23, volume24h: 15.2e9, marketCap: 415.6e9, liquidity: 97.1, aiSignal: 'BUY', confidence: 82, trend: 'bullish', sparklineData: [3210, 3280, 3340, 3300, 3380, 3420, 3440, 3410, 3430, 3456] },
  { rank: 3, name: 'Solana', symbol: 'SOL', icon: '◎', price: 148.23, change1h: 1.24, change24h: 6.71, change7d: 12.45, volume24h: 5.8e9, marketCap: 64.2e9, liquidity: 94.5, aiSignal: 'BUY', confidence: 84, trend: 'bullish', sparklineData: [124, 131, 135, 133, 138, 142, 144, 146, 147, 148] },
  { rank: 4, name: 'XRP', symbol: 'XRP', icon: '✕', price: 0.6234, change1h: -0.35, change24h: -1.24, change7d: 2.18, volume24h: 2.1e9, marketCap: 34.1e9, liquidity: 92.3, aiSignal: 'WAIT', confidence: 65, trend: 'neutral', sparklineData: [0.58, 0.59, 0.62, 0.61, 0.63, 0.62, 0.63, 0.62, 0.62, 0.623] },
  { rank: 5, name: 'BNB', symbol: 'BNB', icon: '◆', price: 587.35, change1h: -0.52, change24h: 3.24, change7d: 6.78, volume24h: 1.9e9, marketCap: 90.2e9, liquidity: 95.8, aiSignal: 'BUY', confidence: 76, trend: 'bullish', sparklineData: [534, 548, 555, 550, 562, 570, 578, 574, 582, 587] },
  { rank: 6, name: 'Cardano', symbol: 'ADA', icon: '₳', price: 0.4521, change1h: 0.85, change24h: 4.52, change7d: 8.34, volume24h: 840e6, marketCap: 15.9e9, liquidity: 89.1, aiSignal: 'BUY', confidence: 71, trend: 'bullish', sparklineData: [0.40, 0.41, 0.42, 0.41, 0.43, 0.43, 0.44, 0.44, 0.45, 0.452] },
  { rank: 7, name: 'Dogecoin', symbol: 'DOGE', icon: 'Ð', price: 0.1245, change1h: -1.42, change24h: -3.87, change7d: -1.23, volume24h: 1.2e9, marketCap: 17.8e9, liquidity: 91.2, aiSignal: 'SELL', confidence: 72, trend: 'bearish', sparklineData: [0.14, 0.13, 0.13, 0.12, 0.12, 0.12, 0.12, 0.12, 0.12, 0.124] },
  { rank: 8, name: 'Avalanche', symbol: 'AVAX', icon: '◈', price: 32.87, change1h: 2.14, change24h: 8.92, change7d: 18.45, volume24h: 680e6, marketCap: 12.4e9, liquidity: 87.6, aiSignal: 'BUY', confidence: 91, trend: 'bullish', sparklineData: [25.1, 26.4, 27.8, 27.2, 28.5, 29.8, 30.5, 31.2, 32.1, 32.8] },
  { rank: 9, name: 'Polkadot', symbol: 'DOT', icon: '●', price: 6.87, change1h: 0.12, change24h: 1.45, change7d: 3.67, volume24h: 320e6, marketCap: 9.2e9, liquidity: 85.4, aiSignal: 'WAIT', confidence: 58, trend: 'neutral', sparklineData: [6.4, 6.5, 6.6, 6.5, 6.6, 6.7, 6.8, 6.7, 6.8, 6.87] },
  { rank: 10, name: 'Chainlink', symbol: 'LINK', icon: '⬡', price: 14.23, change1h: -0.67, change24h: -2.18, change7d: 4.32, volume24h: 410e6, marketCap: 8.3e9, liquidity: 86.8, aiSignal: 'SELL', confidence: 63, trend: 'bearish', sparklineData: [14.8, 14.5, 14.3, 14.1, 14.4, 14.6, 14.2, 14.1, 14.1, 14.2] },
  { rank: 11, name: 'Polygon', symbol: 'MATIC', icon: '⬠', price: 0.7234, change1h: 0.34, change24h: 2.86, change7d: 7.12, volume24h: 280e6, marketCap: 7.1e9, liquidity: 83.2, aiSignal: 'BUY', confidence: 74, trend: 'bullish', sparklineData: [0.64, 0.66, 0.67, 0.66, 0.68, 0.69, 0.70, 0.71, 0.71, 0.723] },
  { rank: 12, name: 'Toncoin', symbol: 'TON', icon: '◇', price: 6.34, change1h: 1.82, change24h: 5.34, change7d: 11.24, volume24h: 390e6, marketCap: 15.8e9, liquidity: 82.1, aiSignal: 'BUY', confidence: 79, trend: 'bullish', sparklineData: [5.5, 5.7, 5.8, 5.7, 5.9, 6.0, 6.1, 6.2, 6.3, 6.34] },
  { rank: 13, name: 'Shiba Inu', symbol: 'SHIB', icon: '🐕', price: 0.00002345, change1h: -1.12, change24h: -4.23, change7d: -2.45, volume24h: 310e6, marketCap: 13.8e9, liquidity: 80.5, aiSignal: 'SELL', confidence: 68, trend: 'bearish', sparklineData: [0.000026, 0.000025, 0.000024, 0.000024, 0.000024, 0.000023, 0.000023, 0.000023, 0.000023, 0.000023] },
  { rank: 14, name: 'Litecoin', symbol: 'LTC', icon: 'Ł', price: 84.56, change1h: 0.23, change24h: 1.87, change7d: 3.45, volume24h: 290e6, marketCap: 6.3e9, liquidity: 88.9, aiSignal: 'WAIT', confidence: 55, trend: 'neutral', sparklineData: [80.1, 81.2, 82.0, 81.5, 82.4, 83.0, 83.5, 83.8, 84.1, 84.5] },
  { rank: 15, name: 'Uniswap', symbol: 'UNI', icon: '🦄', price: 7.89, change1h: -0.45, change24h: 0.89, change7d: 2.56, volume24h: 180e6, marketCap: 4.7e9, liquidity: 84.3, aiSignal: 'WAIT', confidence: 61, trend: 'neutral', sparklineData: [7.5, 7.6, 7.7, 7.6, 7.7, 7.8, 7.8, 7.8, 7.8, 7.89] },
  { rank: 16, name: 'Arbitrum', symbol: 'ARB', icon: '▲', price: 0.9123, change1h: 1.45, change24h: 4.78, change7d: 9.87, volume24h: 240e6, marketCap: 2.9e9, liquidity: 78.4, aiSignal: 'BUY', confidence: 81, trend: 'bullish', sparklineData: [0.78, 0.81, 0.83, 0.82, 0.85, 0.87, 0.88, 0.89, 0.90, 0.912] },
  { rank: 17, name: 'Optimism', symbol: 'OP', icon: '⬡', price: 2.34, change1h: -0.78, change24h: 2.12, change7d: 6.34, volume24h: 160e6, marketCap: 2.3e9, liquidity: 76.8, aiSignal: 'WAIT', confidence: 64, trend: 'neutral', sparklineData: [2.1, 2.2, 2.2, 2.2, 2.2, 2.3, 2.3, 2.3, 2.3, 2.34] },
  { rank: 18, name: 'NEAR', symbol: 'NEAR', icon: '◆', price: 4.67, change1h: 0.56, change24h: 3.45, change7d: 8.23, volume24h: 210e6, marketCap: 5.1e9, liquidity: 81.2, aiSignal: 'BUY', confidence: 77, trend: 'bullish', sparklineData: [4.1, 4.2, 4.3, 4.2, 4.3, 4.4, 4.5, 4.5, 4.6, 4.67] },
  { rank: 19, name: 'Aptos', symbol: 'APT', icon: '◈', price: 8.12, change1h: 2.34, change24h: 7.89, change7d: 15.67, volume24h: 190e6, marketCap: 3.8e9, liquidity: 77.5, aiSignal: 'BUY', confidence: 88, trend: 'bullish', sparklineData: [6.5, 6.8, 7.1, 6.9, 7.3, 7.5, 7.7, 7.9, 8.0, 8.12] },
  { rank: 20, name: 'Stellar', symbol: 'XLM', icon: '✳', price: 0.1123, change1h: -0.23, change24h: -0.87, change7d: 1.23, volume24h: 85e6, marketCap: 3.2e9, liquidity: 79.8, aiSignal: 'WAIT', confidence: 52, trend: 'neutral', sparklineData: [0.108, 0.109, 0.110, 0.109, 0.111, 0.111, 0.112, 0.111, 0.112, 0.112] },
]
