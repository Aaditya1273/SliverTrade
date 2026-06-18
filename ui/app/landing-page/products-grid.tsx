'use client'

import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const products = [
  {
    title: 'TRADING SIGNALS',
    description: 'AI-powered BUY/SELL/HOLD decisions combining RSI, MACD, EMA, and Bollinger Bands.',
    gradient: 'linear-gradient(180deg, #2A1A0A 0%, #0E0E0C 100%)',
    icon: '◆',
  },
  {
    title: 'RISK ENGINE',
    description: '10 pre-trade safety checks per order — daily loss limits, position caps, stale signal rejection.',
    gradient: 'linear-gradient(180deg, #1A2A0A 0%, #0E0E0C 100%)',
    icon: '◈',
  },
  {
    title: 'BROKER INTEGRATION',
    description: '30+ brokers via OAuth, API Key, and TOTP — Zerodha, Angel One, Binance, Bybit.',
    gradient: 'linear-gradient(180deg, #2A0A0A 0%, #0E0E0C 100%)',
    icon: '◉',
  },
  {
    title: 'AI CHAT',
    description: 'Portfolio-aware GPT-4o assistant that knows your holdings, positions, and recent signals.',
    gradient: 'linear-gradient(180deg, #0A1A2A 0%, #0E0E0C 100%)',
    icon: '◇',
  },
]

export default function ProductsGrid() {
  const sectionRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    const cards = sectionRef.current.querySelectorAll('.product-grid-card')

    gsap.fromTo(
      cards,
      { y: 80, opacity: 0, rotateY: -15 },
      {
        y: 0,
        opacity: 1,
        rotateY: 0,
        duration: 1,
        ease: 'expo.out',
        stagger: 0.15,
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
      className="relative z-[3] py-32 px-6"
      style={{ backgroundColor: 'var(--foreground)' }}
    >
      <div className="max-w-[1400px] mx-auto">
        <h2
          className="text-center font-extrabold mb-16"
          style={{
            fontFamily: "'Archivo Black', sans-serif",
            fontSize: 'clamp(36px, 5vw, 72px)',
            letterSpacing: '-0.03em',
            lineHeight: 1.0,
            color: 'var(--inverse-fg)',
          }}
        >
          GROW WITH COINYC
        </h2>

        <div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"
          style={{ perspective: '1000px' }}
        >
          {products.map((product) => (
            <div
              key={product.title}
              className="product-grid-card opacity-0 rounded-[20px] overflow-hidden transition-all duration-300 hover:-translate-y-3 group"
              style={{
                background: product.gradient,
                boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
              }}
            >
              <div className="h-[200px] flex items-center justify-center">
                <span
                  style={{
                    fontSize: 48,
                    color: 'var(--accent)',
                    opacity: 0.3,
                  }}
                >
                  {product.icon}
                </span>
              </div>
              <div className="p-6">
                <h3
                  className="font-bold text-lg mb-2 flex items-center gap-2"
                  style={{ color: 'var(--inverse-fg)' }}
                >
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="10" cy="10" r="8" />
                    <circle cx="10" cy="10" r="3" />
                  </svg>
                  {product.title}
                </h3>
                <p className="text-[15px] leading-relaxed" style={{ color: 'rgba(244,241,234,0.5)' }}>
                  {product.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
