import { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';

const navLinks = [
  { label: 'Products', href: '#products' },
  { label: 'Solutions', href: '#solutions' },
  { label: 'Knowledge Center', href: '#knowledge' },
  { label: 'Company', href: '#company' },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const navRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 100);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    if (navRef.current) {
      gsap.fromTo(
        navRef.current,
        { y: -20, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.6, ease: 'power2.out', delay: 0.1 }
      );
    }
  }, []);

  const handleNavClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    e.preventDefault();
    const target = document.querySelector(href);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <nav
      ref={navRef}
      className="fixed top-0 left-0 right-0 z-50 h-16 flex items-center transition-all duration-300"
      style={{
        backgroundColor: scrolled ? 'rgba(239, 237, 231, 0.92)' : 'transparent',
        backdropFilter: scrolled ? 'blur(12px)' : 'none',
      }}
    >
      <div className="w-full max-w-[1400px] mx-auto flex items-center justify-between px-6 lg:px-10">
        {/* Logo */}
        <a href="#" className="flex items-center">
          <svg width="100" height="24" viewBox="0 0 100 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <text
              x="0"
              y="19"
              fontFamily="Inter, sans-serif"
              fontWeight="900"
              fontSize="22"
              letterSpacing="-0.04em"
              fill="#111111"
            >
              CODA
            </text>
          </svg>
        </a>

        {/* Center Nav */}
        <div className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              onClick={(e) => handleNavClick(e, link.href)}
              className="group relative text-xs font-semibold uppercase tracking-[0.08em] text-[#111111] hover:text-[#111111] transition-colors duration-200"
            >
              {link.label}
              <span className="absolute left-1/2 -bottom-0.5 h-px w-0 bg-[#111111] transition-all duration-200 group-hover:w-full group-hover:left-0" />
            </a>
          ))}
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-4">
          <a
            href="#contact"
            onClick={(e) => handleNavClick(e, '#contact')}
            className="hidden sm:block text-xs font-semibold uppercase tracking-[0.08em] text-[#111111] hover:opacity-70 transition-opacity duration-200"
          >
            Contact us
          </a>
          <a
            href="#cta"
            onClick={(e) => handleNavClick(e, '#cta')}
            className="text-xs font-semibold uppercase tracking-[0.08em] text-white bg-[#111111] hover:bg-[#0A8F5C] px-6 py-2.5 rounded-full transition-colors duration-200"
          >
            Get Started
          </a>
        </div>
      </div>
    </nav>
  );
}
