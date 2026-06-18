import { useEffect, useRef } from 'react';
import Lenis from 'lenis';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

import AnnouncementBar from './sections/AnnouncementBar';
import Navbar from './sections/Navbar';
import HeroSection from './sections/HeroSection';
import ProductShowcase from './sections/ProductShowcase';
import VisionSection from './sections/VisionSection';
import StatsSection from './sections/StatsSection';
import GoalsSection from './sections/GoalsSection';
import SolutionCards from './sections/SolutionCards';
import BlogSection from './sections/BlogSection';
import ProductsGrid from './sections/ProductsGrid';
import PartnersSection from './sections/PartnersSection';
import CTASection from './sections/CTASection';
import Footer from './sections/Footer';

gsap.registerPlugin(ScrollTrigger);

export default function App() {
  const lenisRef = useRef<Lenis | null>(null);

  useEffect(() => {
    // Initialize Lenis smooth scrolling
    const lenis = new Lenis({
      lerp: 0.15,
      duration: 1.2,
      smoothWheel: true,
    });

    lenisRef.current = lenis;

    // Bridge Lenis to GSAP ScrollTrigger
    lenis.on('scroll', ScrollTrigger.update);

    gsap.ticker.add((time) => {
      lenis.raf(time * 1000);
    });

    gsap.ticker.lagSmoothing(0);

    return () => {
      lenis.destroy();
      gsap.ticker.remove(lenis.raf);
    };
  }, []);

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
  );
}
