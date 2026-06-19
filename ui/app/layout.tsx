import type { Metadata, Viewport } from 'next'
import { Toaster } from '@/components/ui/sonner'
import QueryProvider from '@/components/providers/query-provider'
import { CookieConsent } from '@/components/legal/cookie-consent'
import './globals.css'

export const metadata: Metadata = {
  title: 'SilverTrade — AI-Powered Trading Signals & Broker Execution',
  description: 'Multi-indicator trading signals (RSI, MACD, EMA, Bollinger Bands) combined into clear BUY/SELL/HOLD decisions. 10+ broker integrations across India and Crypto markets.',
  icons: { icon: '/icon.svg', apple: '/apple-icon.png' },
}

export const viewport: Viewport = {
  themeColor: '#0A0A0B',
  colorScheme: 'dark',
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
