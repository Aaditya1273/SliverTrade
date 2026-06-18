'use client'

import { useEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const stats = [
  { value: 30, suffix: '+', label: 'Broker Integrations' },
  { value: 7, suffix: '', label: 'Technical Indicators' },
  { value: 10, suffix: '', label: 'Pre-Trade Risk Checks' },
  { value: 5000, suffix: '+', label: 'Active Traders' },
]

export default function StatsSection() {
  const sectionRef = useRef<HTMLDivElement>(null)
  const [activeIndex, setActiveIndex] = useState(0)
  const [displayValue, setDisplayValue] = useState(0)

  useEffect(() => {
    if (!sectionRef.current) return

    const triggers: ScrollTrigger[] = []

    stats.forEach((stat, i) => {
      const trigger = ScrollTrigger.create({
        trigger: sectionRef.current,
        start: () => `${(i / stats.length) * 100}% top`,
        end: () => `${((i + 1) / stats.length) * 100}% top`,
        onEnter: () => setActiveIndex(i),
        onEnterBack: () => setActiveIndex(i),
        onUpdate: (self) => {
          const progress = self.progress
          setDisplayValue(Math.round(progress * stat.value))
        },
      })
      triggers.push(trigger)
    })

    return () => {
      triggers.forEach((t) => t.kill())
    }
  }, [])

  const currentStat = stats[activeIndex]
  const formattedValue = `${displayValue}${currentStat.suffix}`

  return (
    <section
      ref={sectionRef}
      className="relative z-[3]"
      style={{ height: `${stats.length * 100}vh`, backgroundColor: 'var(--background)' }}
    >
      <div className="sticky top-0 h-[100dvh] flex flex-col items-center justify-center px-6">
        {/* Label */}
        <div
          className="mb-12 border rounded-full px-5 py-2"
          style={{
            borderColor: 'var(--border)',
            fontSize: '12px',
            fontWeight: 600,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--foreground)',
          }}
        >
          THE NUMBERS SPEAK FOR THEMSELVES
        </div>

        {/* Counter */}
        <div className="relative flex flex-col items-center">
          {/* Progress dots */}
          <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-16 flex flex-col gap-2">
            {stats.map((_, i) => (
              <div
                key={i}
                className="w-2 h-2 rounded-full transition-all duration-300"
                style={{
                  backgroundColor: i === activeIndex ? 'var(--foreground)' : 'var(--border)',
                }}
              />
            ))}
          </div>

          {/* Counter index */}
          <div
            className="absolute left-0 top-0 -translate-x-16"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '13px',
              color: 'var(--muted-foreground)',
            }}
          >
            {String(activeIndex + 1).padStart(2, '0')} / {String(stats.length).padStart(2, '0')}
          </div>

          {/* Dashed ellipse */}
          <svg
            className="absolute inset-0 w-full h-full -z-10 opacity-[0.08] animate-lp-spin"
            viewBox="0 0 400 200"
          >
            <ellipse
              cx="200"
              cy="100"
              rx="180"
              ry="80"
              fill="none"
              stroke="currentColor"
              strokeWidth="1"
              strokeDasharray="8 8"
              style={{ color: 'var(--foreground)' }}
            />
          </svg>

          {/* Number */}
          <div
            className="text-center"
            style={{
              fontFamily: "'Archivo Black', sans-serif",
              fontSize: 'clamp(40px, 6vw, 100px)',
              letterSpacing: '-0.03em',
              lineHeight: 0.88,
              color: 'var(--foreground)',
            }}
          >
            {formattedValue}
          </div>

          {/* Label */}
          <p className="mt-6 text-lg" style={{ color: 'var(--muted-foreground)' }}>
            {currentStat.label}
          </p>
        </div>
      </div>
    </section>
  )
}
