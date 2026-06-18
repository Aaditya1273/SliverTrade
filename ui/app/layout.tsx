import type { Metadata, Viewport } from 'next'
import { Toaster } from '@/components/ui/sonner'
import QueryProvider from '@/components/providers/query-provider'
import { CookieConsent } from '@/components/legal/cookie-consent'
import './globals.css'

export const metadata: Metadata = {
  title: 'CoinYC — AI-Powered Crypto Trading Signals',
  description: 'RSI, MACD, EMA and Bollinger Bands combined into clear BUY/SELL/HOLD signals. 30+ broker integrations. Real execution.',
  icons: { icon: '/icon.svg', apple: '/apple-icon.png' },
}

export const viewport: Viewport = {
  themeColor: '#F4F1EA',
  colorScheme: 'light',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body style={{ margin: 0, padding: 0 }}>
        <QueryProvider>
          {children}
          <Toaster position="bottom-right" theme="light" />
          <CookieConsent />
        </QueryProvider>
      </body>
    </html>
  )
}
