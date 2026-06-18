'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import gsap from 'gsap'

const navLinks = [
  { label: 'Products', href: '#products' },
  { label: 'Brokers', href: '#brokers' },
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Pricing', href: '/pricing' },
]

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const navRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 100)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    if (navRef.current) {
      gsap.fromTo(
        navRef.current,
        { y: -20, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.6, ease: 'power2.out', delay: 0.1 }
      )
    }
  }, [])

  return (
    <nav
      ref={navRef}
      className="fixed top-0 left-0 right-0 z-50 h-16 flex items-center transition-all duration-300"
      style={{
        backgroundColor: scrolled ? 'rgba(244,241,234,0.92)' : 'transparent',
        backdropFilter: scrolled ? 'blur(12px)' : 'none',
      }}
    >
      <div className="w-full max-w-[1400px] mx-auto flex items-center justify-between px-6 lg:px-10">
        {/* Logo */}
        <Link href="/" className="flex items-center">
          <span
            style={{
              fontFamily: "'Archivo Black', sans-serif",
              fontSize: 28,
              fontWeight: 900,
              letterSpacing: '-0.04em',
              color: 'var(--foreground)',
            }}
          >
            CoinYC
          </span>
        </Link>

        {/* Center Nav */}
        <div className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className="group relative text-xs font-semibold uppercase tracking-[0.08em] transition-colors duration-200"
              style={{ color: 'var(--foreground)' }}
            >
              {link.label}
              <span
                className="absolute left-1/2 -bottom-0.5 h-px w-0 transition-all duration-200 group-hover:w-full group-hover:left-0"
                style={{ background: 'var(--foreground)' }}
              />
            </Link>
          ))}
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-4">
          <Link
            href="/login"
            className="hidden sm:block text-xs font-semibold uppercase tracking-[0.08em] hover:opacity-70 transition-opacity duration-200"
            style={{ color: 'var(--foreground)' }}
          >
            Sign in
          </Link>
          <Link
            href="/signup"
            className="text-xs font-semibold uppercase tracking-[0.08em] text-white px-6 py-2.5 rounded-full transition-colors duration-200"
            style={{ backgroundColor: 'var(--foreground)' }}
          >
            Get Started
          </Link>
        </div>
      </div>
    </nav>
  )
}
