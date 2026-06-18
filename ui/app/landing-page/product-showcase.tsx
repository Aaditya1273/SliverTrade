'use client'

import { useEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const products = [
  {
    id: 'signals',
    title: 'Trading Signals',
    description: 'AI-powered BUY/SELL/HOLD decisions combining RSI, MACD, EMA, and Bollinger Bands into a single confidence score.',
    bg: '#E6E1D6',
    icon: (
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="32" cy="32" r="28" />
        <circle cx="32" cy="32" r="16" />
        <circle cx="32" cy="32" r="6" />
        <line x1="32" y1="4" x2="32" y2="60" />
        <line x1="4" y1="32" x2="60" y2="32" />
      </svg>
    ),
  },
  {
    id: 'risk',
    title: 'Risk Engine',
    description: '10 pre-trade safety checks per order — daily loss limits, position caps, stale signal rejection, all in under 50ms.',
    bg: '#D9D3C5',
    icon: (
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M32 4 L56 16 V36 C56 50 32 60 32 60 C32 60 8 50 8 36 V16 Z" />
        <polyline points="22 32 30 40 42 24" />
      </svg>
    ),
  },
  {
    id: 'brokers',
    title: 'Broker Integration',
    description: '30+ brokers via OAuth, API Key, and TOTP — Zerodha, Angel One, Binance, Bybit, and more.',
    bg: '#E25A2B',
    icon: (
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="20" cy="20" r="10" />
        <circle cx="44" cy="20" r="10" />
        <circle cx="32" cy="48" r="10" />
        <line x1="27" y1="28" x2="30" y2="39" />
        <line x1="37" y1="28" x2="34" y2="39" />
        <line x1="20" y1="20" x2="44" y2="20" />
      </svg>
    ),
  },
  {
    id: 'chat',
    title: 'AI Chat',
    description: 'Portfolio-aware GPT-4o assistant that knows your holdings, positions, and recent signals.',
    bg: '#E6E1D6',
    icon: (
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M16 48V24l8-8h16l8 8v24" />
        <path d="M24 16v-4a8 8 0 0116 0v4" />
        <line x1="20" y1="28" x2="44" y2="28" />
      </svg>
    ),
  },
]

export default function ProductShowcase() {
  const sectionRef = useRef<HTMLDivElement>(null)
  const cardsRef = useRef<HTMLDivElement>(null)
  const [activeTab, setActiveTab] = useState('signals')

  useEffect(() => {
    if (!cardsRef.current || !sectionRef.current) return

    const cards = cardsRef.current.querySelectorAll('.product-card')

    gsap.fromTo(
      cards,
      { y: 250, opacity: 0 },
      {
        y: 0,
        opacity: 1,
        duration: 0.8,
        ease: 'expo.out',
        stagger: 0.1,
        scrollTrigger: {
          trigger: sectionRef.current,
          start: 'top 80%',
          toggleActions: 'play none none none',
        },
      }
    )

    return () => {
      ScrollTrigger.getAll().forEach((t) => t.kill())
    }
  }, [])

  return (
    <section
      ref={sectionRef}
      id="products"
      className="relative z-[3] min-h-[150vh] flex flex-col items-center justify-center py-32 px-6"
    >
      {/* Floating Cards */}
      <div
        ref={cardsRef}
        className="flex flex-wrap justify-center gap-6 mb-16 max-w-[1400px] mx-auto"
      >
        {products.map((product) => (
          <div
            key={product.id}
            className="product-card opacity-0 w-[280px] rounded-[20px] p-8 flex flex-col"
            style={{
              backgroundColor: product.bg,
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
              aspectRatio: '4/5',
              color: product.bg === '#E25A2B' ? '#F4F1EA' : 'var(--foreground)',
            }}
          >
            <div className="flex-1 flex items-center justify-center mb-6">
              {product.icon}
            </div>
            <p className="text-[15px] leading-relaxed mb-4" style={{ opacity: 0.6 }}>
              {product.description}
            </p>
            <a
              href="#features"
              className="text-sm font-medium hover:underline"
              style={{ color: product.bg === '#E25A2B' ? '#F4F1EA' : 'var(--accent)' }}
            >
              Learn more
            </a>
          </div>
        ))}
      </div>

      {/* Tab Bar */}
      <div
        className="flex items-center gap-1 p-1.5 rounded-full"
        style={{ backgroundColor: 'rgba(0,0,0,0.06)' }}
      >
        {products.map((product) => (
          <button
            key={product.id}
            onClick={() => setActiveTab(product.id)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-semibold uppercase tracking-wide transition-all duration-300"
            style={{
              backgroundColor: activeTab === product.id ? '#fff' : 'transparent',
              color: activeTab === product.id ? '#111' : 'rgba(0,0,0,0.4)',
            }}
          >
            <span className="text-sm">{product.icon}</span>
            {product.title}
          </button>
        ))}
      </div>
    </section>
  )
}
