'use client'

import { useEffect, useRef } from 'react'
import Lenis from 'lenis'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

import AnnouncementBar from './landing-page/announcement-bar'
import Navbar from './landing-page/navbar'
import HeroSection from './landing-page/hero'
import ProductShowcase from './landing-page/product-showcase'
import VisionSection from './landing-page/vision-section'
import StatsSection from './landing-page/stats-section'
import GoalsSection from './landing-page/goals-section'
import SolutionCards from './landing-page/solution-cards'
import BlogSection from './landing-page/blog-section'
import ProductsGrid from './landing-page/products-grid'
import PartnersSection from './landing-page/partners-section'
import CTASection from './landing-page/cta-section'
import Footer from './landing-page/footer'

gsap.registerPlugin(ScrollTrigger)

export default function LandingPage() {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const lenis = new Lenis({
      lerp: prefersReduced ? 1 : 0.15,
      duration: prefersReduced ? 0 : 1.2,
      smoothWheel: !prefersReduced,
    })

    lenis.on('scroll', ScrollTrigger.update)

    const tickerCallback = (time: number) => {
      lenis.raf(time * 1000)
    }
    gsap.ticker.add(tickerCallback)
    gsap.ticker.lagSmoothing(0)

    return () => {
      gsap.ticker.remove(tickerCallback)
      lenis.destroy()
    }
  }, [])

  return (
    <div ref={containerRef} className="relative">
      <AnnouncementBar />
      <Navbar />
      <HeroSection />

      {/* Content sections below hero */}
      <div className="relative z-[3]">
        <ProductShowcase />
        <VisionSection />
        <StatsSection />
        <GoalsSection />
        <SolutionCards />
        <BlogSection />
        <ProductsGrid />
        <PartnersSection />
        <CTASection />
        <Footer />
      </div>
    </div>
  )
}
