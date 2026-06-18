'use client'

import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Link from 'next/link'

gsap.registerPlugin(ScrollTrigger)

const blogs = [
  {
    category: 'Product',
    title: 'How AI-powered signals reduce emotional trading decisions by 73%',
    date: 'Jun 10 2026',
    readTime: '3 mins',
  },
  {
    category: 'Insights',
    title: 'The state of algo-trading in Indian equity markets: 2026 report',
    date: 'May 28 2026',
    readTime: '6 mins',
  },
  {
    category: 'Product',
    title: 'Risk engine v2: 10 pre-trade checks now fire in under 50ms',
    date: 'May 15 2026',
    readTime: '4 mins',
  },
]

export default function BlogSection() {
  const sectionRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    const cards = sectionRef.current.querySelectorAll('.blog-card')

    gsap.fromTo(
      cards,
      { y: 40, opacity: 0 },
      {
        y: 0,
        opacity: 1,
        duration: 0.6,
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
      id="knowledge"
      className="relative z-[3] py-32 px-6"
      style={{ backgroundColor: 'var(--inverse-bg)' }}
    >
      <div className="max-w-[1400px] mx-auto">
        <div className="flex justify-center mb-8">
          <div
            className="border rounded-full px-5 py-2"
            style={{
              borderColor: 'rgba(244,241,234,0.2)',
              fontSize: '12px',
              fontWeight: 600,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: '#FFFFFF',
            }}
          >
            LET&apos;S DIVE IN
          </div>
        </div>

        <h2
          className="text-center font-extrabold mb-16"
          style={{
            fontFamily: "'Archivo Black', sans-serif",
            fontSize: 'clamp(36px, 5vw, 72px)',
            letterSpacing: '-0.03em',
            lineHeight: 1.0,
            color: '#FFFFFF',
          }}
        >
          HERE&apos;S WHAT YOU NEED TO KNOW
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {blogs.map((blog, i) => (
            <article
              key={i}
              className="blog-card opacity-0 group cursor-pointer"
            >
              <div className="relative overflow-hidden mb-5 aspect-[16/10]"
                style={{ background: 'var(--muted)', borderRadius: '12px' }}
              >
                <div className="w-full h-full flex items-center justify-center" style={{ color: 'var(--muted-foreground)', opacity: 0.3 }}>
                  <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="1">
                    <rect x="4" y="4" width="40" height="40" rx="4" />
                    <line x1="4" y1="20" x2="44" y2="20" />
                    <line x1="20" y1="4" x2="20" y2="44" />
                  </svg>
                </div>
              </div>

              <span className="text-[11px] font-medium uppercase tracking-[0.12em]" style={{ color: 'rgba(244,241,234,0.4)' }}>
                {blog.category}
              </span>
              <h3 className="mt-2 text-lg font-semibold leading-snug group-hover:underline transition-all duration-200" style={{ color: '#FFFFFF' }}>
                {blog.title}
              </h3>
              <p className="mt-3 text-[11px] uppercase tracking-wide" style={{ color: 'rgba(244,241,234,0.4)' }}>
                {blog.date} · {blog.readTime}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
