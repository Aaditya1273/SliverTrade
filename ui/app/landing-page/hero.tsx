'use client'

import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export default function HeroSection() {
  const heroRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const canvasWrapRef = useRef<HTMLDivElement>(null)
  const bgOverlayRef = useRef<HTMLDivElement>(null)
  const eyebrowRef = useRef<HTMLDivElement>(null)
  const pillRef = useRef<HTMLAnchorElement>(null)
  const headlineRef = useRef<HTMLDivElement>(null)
  const subtitleRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    // Canvas fade on scroll
    if (canvasWrapRef.current) {
      gsap.to(canvasWrapRef.current, {
        opacity: 0,
        ease: 'none',
        scrollTrigger: {
          trigger: heroRef.current,
          start: '50% top',
          end: '150% top',
          scrub: true,
        },
      })
    }

    // Background color transition
    if (bgOverlayRef.current) {
      gsap.fromTo(
        bgOverlayRef.current,
        { opacity: 0 },
        {
          opacity: 1,
          ease: 'none',
          scrollTrigger: {
            trigger: heroRef.current,
            start: '50% top',
            end: '150% top',
            scrub: true,
          },
        }
      )
    }

    // Hero content scroll animation
    if (contentRef.current) {
      gsap.to(contentRef.current, {
        rotateX: 70,
        y: 100,
        opacity: 0.3,
        ease: 'none',
        scrollTrigger: {
          trigger: heroRef.current,
          start: 'top top',
          end: 'bottom top',
          scrub: true,
        },
      })
    }

    // Load animations
    const tl = gsap.timeline({ delay: 0.5 })

    if (eyebrowRef.current) {
      tl.fromTo(eyebrowRef.current, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.6 }, 0.2)
    }

    if (pillRef.current) {
      tl.fromTo(pillRef.current, { opacity: 0 }, { opacity: 1, duration: 0.6 }, 0.4)
    }

    // Headline 3D rotation
    if (headlineRef.current) {
      const words = headlineRef.current.querySelectorAll('.hero-word')
      tl.fromTo(
        words,
        { rotateX: -90, opacity: 0 },
        {
          rotateX: 0,
          opacity: 1,
          duration: 1.2,
          ease: 'expo.out',
          stagger: 0.15,
        },
        0.5
      )
    }

    if (subtitleRef.current) {
      tl.fromTo(
        subtitleRef.current,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.8 },
        0.8
      )
    }

    return () => {
      ScrollTrigger.getAll().forEach((t) => t.kill())
    }
  }, [])

  return (
    <>
      {/* Decorative background canvas */}
      <div
        ref={canvasWrapRef}
        className="fixed inset-0 z-0 pointer-events-none"
      >
        <div
          style={{
            width: '100%',
            height: '100%',
            background: 'radial-gradient(ellipse at 30% 40%, rgba(226,90,43,0.06) 0%, transparent 60%), radial-gradient(ellipse at 70% 60%, rgba(14,14,12,0.04) 0%, transparent 50%)',
          }}
        />
      </div>

      {/* Background Color Overlay */}
      <div
        ref={bgOverlayRef}
        className="fixed inset-0 z-[1] pointer-events-none"
        style={{ backgroundColor: 'var(--background)', opacity: 0 }}
      />

      {/* Hero Content */}
      <section
        ref={heroRef}
        className="relative z-[2] min-h-[100dvh] flex items-center justify-center px-6"
        style={{ backgroundColor: 'transparent', perspective: '1000px' }}
      >
        <div
          ref={contentRef}
          className="text-center flex flex-col items-center"
          style={{ transformStyle: 'preserve-3d' }}
        >
          {/* Eyebrow */}
          <div
            ref={eyebrowRef}
            className="opacity-0 mb-6"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '11px',
              fontWeight: 500,
              letterSpacing: '0.12em',
              textTransform: 'uppercase' as const,
              color: 'var(--muted-foreground)',
            }}
          >
            AI-POWERED TRADING
          </div>

          {/* Pill CTA */}
          <a
            ref={pillRef}
            href="/signup"
            className="opacity-0 mb-8 inline-flex items-center gap-2 border rounded-full px-5 py-2 text-[13px] font-medium transition-all duration-200"
            style={{
              borderColor: 'var(--border)',
              color: 'var(--foreground)',
            }}
          >
            Start trading with precision
            <span className="text-sm">→</span>
          </a>

          {/* Main Headline */}
          <div ref={headlineRef} className="mb-8">
            <div className="overflow-hidden">
              <div
                className="hero-word flex items-center justify-center gap-2"
                style={{
                  fontFamily: "'Archivo Black', sans-serif",
                  fontSize: 'clamp(48px, 12vw, 180px)',
                  fontWeight: 900,
                  letterSpacing: '-0.04em',
                  lineHeight: 0.85,
                  color: 'var(--foreground)',
                  transformOrigin: 'center bottom',
                }}
              >
                TRADE
                <svg width="0.6em" height="0.6em" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="24" cy="24" r="20" />
                  <circle cx="24" cy="24" r="12" />
                  <circle cx="24" cy="24" r="4" />
                  <line x1="24" y1="0" x2="24" y2="48" />
                  <line x1="0" y1="24" x2="48" y2="24" />
                </svg>
                WITH
                <svg width="0.6em" height="0.6em" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="24" cy="24" r="20" />
                  <text x="24" y="30" textAnchor="middle" fontSize="20" fontWeight="700" fill="currentColor" stroke="none">$</text>
                </svg>
              </div>
            </div>
            <div className="overflow-hidden">
              <div
                className="hero-word"
                style={{
                  fontFamily: "'Archivo Black', sans-serif",
                  fontSize: 'clamp(48px, 12vw, 180px)',
                  fontWeight: 900,
                  letterSpacing: '-0.04em',
                  lineHeight: 0.85,
                  color: 'var(--accent)',
                  transformOrigin: 'center bottom',
                }}
              >
                PRECISION
              </div>
            </div>
          </div>

          {/* Subtitle */}
          <p
            ref={subtitleRef}
            className="opacity-0 max-w-[480px] text-lg leading-relaxed"
            style={{ color: 'var(--muted-foreground)' }}
          >
            RSI, MACD, EMA and Bollinger Bands combined into a single BUY, SELL or HOLD decision. 30+ brokers. Real execution.
          </p>
        </div>
      </section>
    </>
  )
}
