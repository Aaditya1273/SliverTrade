'use client'

const footerColumns = [
  {
    title: 'PRODUCTS',
    links: ['Trading Signals', 'Risk Engine', 'Broker Integration', 'AI Chat', 'Charts', 'Analytics'],
  },
  {
    title: 'BROKERS',
    links: ['Zerodha', 'Angel One', 'Binance', 'Bybit', 'Dhan', 'Upstox'],
  },
  {
    title: 'RESOURCES',
    links: ['Documentation', 'Broker Guide', 'API Reference', 'Status', 'Pricing'],
  },
  {
    title: 'COMPANY',
    links: ['About', 'Security', 'Contact Us', 'Get Started'],
  },
]

const bottomLinks = [
  'Terms & Conditions',
  'Privacy Policy',
  'Risk Disclaimer',
  'Cookie Settings',
]

export default function Footer() {
  return (
    <footer
      id="contact"
      className="relative z-[3] pt-20 pb-10 px-6"
      style={{
        backgroundColor: '#0A0A0A',
        borderRadius: '24px 24px 0 0',
      }}
    >
      <div className="max-w-[1400px] mx-auto">
        <div className="flex items-center justify-between mb-10">
          <span
            style={{
              fontFamily: "'Archivo Black', sans-serif",
              fontSize: 28,
              fontWeight: 900,
              letterSpacing: '-0.04em',
              color: '#FFFFFF',
            }}
          >
            CoinYC
          </span>
        </div>

        <div className="h-px mb-10" style={{ backgroundColor: 'rgba(255,255,255,0.1)' }} />

        <div className="grid grid-cols-2 md:grid-cols-4 gap-10">
          {footerColumns.map((column) => (
            <div key={column.title}>
              <h4
                className="mb-4"
                style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: 'rgba(255,255,255,0.5)',
                }}
              >
                {column.title}
              </h4>
              <ul className="space-y-3">
                {column.links.map((link) => (
                  <li key={link}>
                    <a
                      href="#"
                      className="text-[15px] transition-colors duration-150 hover:text-white"
                      style={{ color: 'rgba(255,255,255,0.5)' }}
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-16 pt-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
          style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
        >
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            {bottomLinks.map((link, i) => (
              <span key={link} className="flex items-center gap-4">
                <a
                  href="#"
                  className="text-[11px] transition-colors duration-150 uppercase tracking-wide hover:text-white/60"
                  style={{ color: 'rgba(255,255,255,0.3)' }}
                >
                  {link}
                </a>
                {i < bottomLinks.length - 1 && (
                  <span className="hidden md:inline" style={{ color: 'rgba(255,255,255,0.2)' }}>·</span>
                )}
              </span>
            ))}
          </div>
          <p className="text-[11px] uppercase tracking-wide" style={{ color: 'rgba(255,255,255,0.3)' }}>
            © {new Date().getFullYear()} CoinYC. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  )
}
