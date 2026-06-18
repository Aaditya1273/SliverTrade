'use client'

import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const cards = [
  {
    number: '01',
    title: 'SIGNALS',
    subtitle: 'Multi-model AI engine',
    description:
      'Rule-based TA, Random Forest, and LSTM vote on every signal. When all 3 agree, confidence reaches 85–95%.',
    bg: 'var(--muted)',
  },
  {
    number: '02',
    title: 'EXECUTION',
    subtitle: 'One-click or fully automated',
    description:
      'Execute signals manually or enable auto-execute. Trades fire when confidence clears your threshold — under 50ms.',
    bg: 'var(--muted)',
  },
  {
    number: '03',
    title: 'RISK',
    subtitle: '10 safety checks per order',
    description:
      'Daily loss limits, position caps, stale signal rejection, duplicate prevention — all before touching your broker.',
    bg: 'var(--muted)',
  },
]

export default function SolutionCards() {
  const sectionRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    const cardEls = sectionRef.current.querySelectorAll('.solution-card')

    gsap.fromTo(
      cardEls,
      { y: 60, opacity: 0 },
      {
        y: 0,
        opacity: 1,
        duration: 0.8,
        ease: 'expo.out',
        stagger: 0.12,
        scrollTrigger: {
          trigger: sectionRef.current,
          start: 'top 85%',
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
      className="relative z-[3] py-20 px-6"
      style={{ backgroundColor: 'var(--background)' }}
    >
      <div className="max-w-[1400px] mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
        {cards.map((card) => (
          <div
            key={card.number}
            className="solution-card opacity-0 rounded-[20px] p-10 transition-all duration-300 hover:-translate-y-2"
            style={{
              backgroundColor: card.bg,
              border: '1px solid var(--border)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
            }}
          >
            <div className="flex items-start justify-between mb-6">
              <h3
                style={{
                  fontFamily: "'Archivo Black', sans-serif",
                  fontSize: 'clamp(24px, 3vw, 36px)',
                  letterSpacing: '-0.02em',
                  color: 'var(--foreground)',
                }}
              >
                {card.title}
              </h3>
              <span
                className="flex-shrink-0 w-8 h-8 rounded-full border flex items-center justify-center text-xs"
                style={{
                  borderColor: 'var(--border)',
                  color: 'var(--muted-foreground)',
                  fontFamily: "'JetBrains Mono', monospace",
                }}
              >
                {card.number}
              </span>
            </div>
            <h4 className="font-semibold text-lg mb-4" style={{ color: 'var(--foreground)' }}>
              {card.subtitle}
            </h4>
            <p className="text-[15px] leading-relaxed" style={{ color: 'var(--muted-foreground)' }}>
              {card.description}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}
