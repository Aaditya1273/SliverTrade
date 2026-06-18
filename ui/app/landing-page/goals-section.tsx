'use client'

import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export default function GoalsSection() {
  const sectionRef = useRef<HTMLDivElement>(null)
  const stickyRef = useRef<HTMLDivElement>(null)
  const headlineRef = useRef<HTMLDivElement>(null)
  const line1Ref = useRef<HTMLDivElement>(null)
  const line2Ref = useRef<HTMLDivElement>(null)
  const underlineRef = useRef<HTMLDivElement>(null)
  const subtitleRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    if (!sectionRef.current || !stickyRef.current) return

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: sectionRef.current,
        start: 'top top',
        end: 'bottom bottom',
        scrub: true,
      },
    })

    if (headlineRef.current) {
      tl.fromTo(headlineRef.current, { scale: 1.5 }, { scale: 1, ease: 'none' }, 0)
    }

    if (line1Ref.current) {
      tl.fromTo(line1Ref.current, { y: 20 }, { y: -20, ease: 'none' }, 0)
    }
    if (line2Ref.current) {
      tl.fromTo(line2Ref.current, { y: -20 }, { y: 20, ease: 'none' }, 0)
    }

    if (underlineRef.current) {
      tl.fromTo(underlineRef.current, { scaleX: 0 }, { scaleX: 1, ease: 'none' }, 0.5)
    }

    if (subtitleRef.current) {
      tl.fromTo(subtitleRef.current, { opacity: 0, y: 20 }, { opacity: 1, y: 0, ease: 'none' }, 0.6)
    }

    return () => {
      tl.kill()
    }
  }, [])

  return (
    <section
      ref={sectionRef}
      id="goals"
      className="relative z-[3]"
      style={{ height: '200vh', backgroundColor: 'var(--foreground)' }}
    >
      <div
        ref={stickyRef}
        className="sticky top-0 h-[100dvh] flex flex-col items-center justify-center px-6 overflow-hidden"
      >
        <div
          className="mb-8"
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '11px',
            fontWeight: 500,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: 'rgba(244,241,234,0.5)',
          }}
        >
          WHAT&apos;S YOUR GOAL
        </div>

        <div ref={headlineRef} className="text-center">
          <div
            ref={line1Ref}
            style={{
              fontFamily: "'Archivo Black', sans-serif",
              fontSize: 'clamp(40px, 9vw, 140px)',
              letterSpacing: '-0.04em',
              lineHeight: 0.85,
              color: 'var(--inverse-fg)',
            }}
          >
            TRADE SMARTER
          </div>
          <div
            ref={line2Ref}
            className="flex items-center justify-center gap-4"
            style={{
              fontFamily: "'Archivo Black', sans-serif",
              fontSize: 'clamp(40px, 9vw, 140px)',
              letterSpacing: '-0.04em',
              lineHeight: 0.85,
              color: 'var(--inverse-fg)',
            }}
          >
            <svg width="0.5em" height="0.5em" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="24" cy="24" r="20" />
              <circle cx="24" cy="24" r="12" />
              <circle cx="24" cy="24" r="4" />
            </svg>
            WIN MORE
          </div>

          <div
            ref={underlineRef}
            className="mt-6 mx-auto h-px w-48 origin-left"
            style={{
              background: 'repeating-linear-gradient(90deg, rgba(244,241,234,0.3) 0, rgba(244,241,234,0.3) 6px, transparent 6px, transparent 12px)',
              transform: 'scaleX(0)',
            }}
          />
        </div>

        <p ref={subtitleRef} className="mt-8 text-xl opacity-0" style={{ color: 'rgba(244,241,234,0.5)' }}>
          Stop guessing. Start deciding.
        </p>
      </div>
    </section>
  )
}
