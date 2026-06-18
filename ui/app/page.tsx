'use client'

import { useEffect } from 'react'
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
  useEffect(() => {
    const lenis = new Lenis({
      lerp: 0.15,
      duration: 1.2,
      smoothWheel: true,
    })

    lenis.on('scroll', ScrollTrigger.update)

    gsap.ticker.add((time) => {
      lenis.raf(time * 1000)
    })

    gsap.ticker.lagSmoothing(0)

    return () => {
      lenis.destroy()
    }
  }, [])

  return (
    <div className="relative">
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
