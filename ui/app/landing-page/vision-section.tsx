'use client'

import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const words = ['YOUR', 'VISION', 'MADE', 'REAL']

export default function VisionSection() {
  const sectionRef = useRef<HTMLDivElement>(null)
  const stickyRef = useRef<HTMLDivElement>(null)
  const wordsRef = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    if (!sectionRef.current || !stickyRef.current) return

    const wordElements = wordsRef.current.filter(Boolean) as HTMLDivElement[]

    wordElements.forEach((word) => {
      gsap.set(word, { y: '100%' })
    })

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: sectionRef.current,
        start: 'top top',
        end: 'bottom bottom',
        scrub: true,
      },
    })

    wordElements.forEach((word, i) => {
      const start = i / wordElements.length
      tl.to(word, { y: '0%', ease: 'none' }, start)
    })

    return () => {
      tl.kill()
      ScrollTrigger.getAll().forEach((t) => t.kill())
    }
  }, [])

  return (
    <section
      ref={sectionRef}
      className="relative z-[3]"
      style={{ height: '300vh', backgroundColor: 'var(--inverse-bg)' }}
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
          YOUR VISION, BROUGHT TO LIFE.
        </div>

        <div className="flex flex-col items-center">
          {words.map((word, i) => (
            <div key={i} className="overflow-hidden">
              <div
                ref={(el) => { wordsRef.current[i] = el }}
                className="flex items-center justify-center"
                style={{
                  fontFamily: "'Archivo Black', sans-serif",
                  fontSize: 'clamp(60px, 10vw, 160px)',
                  fontWeight: 900,
                  letterSpacing: '-0.04em',
                  lineHeight: 0.85,
                  color: i === words.length - 1 ? 'var(--accent)' : 'var(--inverse-fg)',
                }}
              >
                {word}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
