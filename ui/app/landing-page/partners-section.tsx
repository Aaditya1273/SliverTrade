'use client'

import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const partnerNames = [
  'Zerodha', 'Angel One', 'Binance', 'Bybit', 'Dhan', 'Upstox',
]

export default function PartnersSection() {
  const sectionRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    const words = sectionRef.current.querySelectorAll('.partner-word')
    const showcase = sectionRef.current.querySelector('.partner-showcase')

    gsap.fromTo(
      words,
      { y: 40, opacity: 0 },
      {
        y: 0,
        opacity: 1,
        duration: 0.8,
        ease: 'expo.out',
        stagger: 0.05,
        scrollTrigger: {
          trigger: sectionRef.current,
          start: 'top 70%',
          toggleActions: 'play none none none',
        },
      }
    )

    if (showcase) {
      gsap.fromTo(
        showcase,
        { scale: 0.95, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 1,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: sectionRef.current,
            start: 'top 70%',
            toggleActions: 'play none none none',
          },
        }
      )
    }

    return () => {
      ScrollTrigger.getAll().forEach((t) => t.kill())
    }
  }, [])

  return (
    <section
      ref={sectionRef}
      id="company"
      className="relative z-[3] pt-40 pb-32 px-6"
      style={{ backgroundColor: 'var(--background)' }}
    >
      <div className="max-w-[1400px] mx-auto">
        <div className="flex justify-center mb-8">
          <div
            className="border rounded-full px-5 py-2"
            style={{
              borderColor: 'var(--border)',
              fontSize: '12px',
              fontWeight: 600,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--foreground)',
            }}
          >
            WHO WE PARTNER WITH
          </div>
        </div>

        <div className="text-center mb-12">
          <h2
            style={{
              fontFamily: "'Archivo Black', sans-serif",
              fontSize: 'clamp(36px, 5vw, 72px)',
              letterSpacing: '-0.03em',
              lineHeight: 1.0,
              color: 'var(--foreground)',
            }}
          >
            <span className="partner-word inline-block opacity-0">OUR</span>{' '}
            <span className="partner-word inline-block opacity-0">PARTNERS</span>
          </h2>
          <h2
            className="flex items-center justify-center gap-3"
            style={{
              fontFamily: "'Archivo Black', sans-serif",
              fontSize: 'clamp(36px, 5vw, 72px)',
              letterSpacing: '-0.03em',
              lineHeight: 1.0,
              color: 'var(--foreground)',
            }}
          >
            <span className="partner-word inline-block opacity-0">THE</span>{' '}
            <span className="partner-word inline-block opacity-0">BEST</span>{' '}
            <span className="partner-word inline-block opacity-0">IN</span>{' '}
            <span className="partner-word inline-flex items-center gap-2 opacity-0" style={{ color: 'var(--accent)' }}>
              MARKETS
            </span>
          </h2>
        </div>

        <div className="partner-showcase relative rounded-3xl overflow-hidden mb-12 opacity-0"
          style={{ aspectRatio: '16/9', background: 'var(--muted)' }}
        >
          <div className="w-full h-full flex items-center justify-center" style={{ color: 'var(--muted-foreground)', opacity: 0.2 }}>
            <svg width="120" height="120" viewBox="0 0 120 120" fill="none" stroke="currentColor" strokeWidth="1">
              <circle cx="60" cy="60" r="50" />
              <circle cx="40" cy="50" r="8" />
              <circle cx="80" cy="50" r="8" />
              <path d="M30 80c12-16 48-16 60 0" strokeLinecap="round" />
            </svg>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-12">
          {partnerNames.map((name) => (
            <span
              key={name}
              className="transition-opacity duration-200 text-lg font-semibold tracking-tight cursor-pointer"
              style={{ color: 'var(--muted-foreground)' }}
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
