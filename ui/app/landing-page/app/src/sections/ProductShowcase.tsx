import { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const products = [
  {
    id: 'webstore',
    title: 'Coda Webstore',
    description: 'A 100% customizable web store to sell your content your way.',
    bg: '#A8C5A0',
    icon: (
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none" stroke="#111" strokeWidth="2">
        <circle cx="32" cy="32" r="28" />
        <circle cx="24" cy="26" r="3" fill="#111" stroke="none" />
        <circle cx="40" cy="26" r="3" fill="#111" stroke="none" />
        <path d="M20 38c4 6 20 6 24 0" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    id: 'codapay',
    title: 'Codapay',
    description: 'Plug into our network of over 400 payment methods and generate revenue from around the world.',
    bg: '#D4C4A8',
    icon: (
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none" stroke="#111" strokeWidth="2">
        <circle cx="32" cy="32" r="28" />
        <ellipse cx="32" cy="32" rx="12" ry="28" />
        <line x1="4" y1="32" x2="60" y2="32" />
        <path d="M8 20c8-4 40-4 48 0" />
        <path d="M8 44c8 4 40 4 48 0" />
      </svg>
    ),
  },
  {
    id: 'distribution',
    title: 'Coda Distribution',
    description: 'Tap into our extended network of e-commerce platforms and watch your reach and revenue grow.',
    bg: '#8B9A6D',
    icon: (
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none" stroke="#111" strokeWidth="2">
        <circle cx="20" cy="20" r="10" />
        <circle cx="44" cy="20" r="10" />
        <circle cx="32" cy="48" r="10" />
        <line x1="27" y1="28" x2="30" y2="39" />
        <line x1="37" y1="28" x2="34" y2="39" />
        <line x1="20" y1="20" x2="44" y2="20" />
      </svg>
    ),
  },
  {
    id: 'codashop',
    title: 'Codashop',
    description: "Codashop is a global marketplace where publishers can offer in-game currencies, content and bundles.",
    bg: '#A8C5A0',
    icon: (
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none" stroke="#111" strokeWidth="2">
        <path d="M16 48V24l8-8h16l8 8v24" />
        <path d="M24 16v-4a8 8 0 0116 0v4" />
        <line x1="20" y1="28" x2="44" y2="28" />
      </svg>
    ),
  },
];

export default function ProductShowcase() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const cardsRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState('webstore');

  useEffect(() => {
    if (!cardsRef.current || !sectionRef.current) return;

    const cards = cardsRef.current.querySelectorAll('.product-card');

    gsap.fromTo(
      cards,
      { y: 250, opacity: 0 },
      {
        y: 0,
        opacity: 1,
        duration: 0.8,
        ease: 'expo.out',
        stagger: 0.1,
        scrollTrigger: {
          trigger: sectionRef.current,
          start: 'top 80%',
          toggleActions: 'play none none none',
        },
      }
    );

    return () => {
      ScrollTrigger.getAll().forEach((t) => t.kill());
    };
  }, []);

  return (
    <section
      ref={sectionRef}
      id="products"
      className="relative z-[3] min-h-[150vh] flex flex-col items-center justify-center py-32 px-6"
    >
      {/* Floating Cards */}
      <div
        ref={cardsRef}
        className="flex flex-wrap justify-center gap-6 mb-16 max-w-[1400px] mx-auto"
      >
        {products.map((product) => (
          <div
            key={product.id}
            className="product-card opacity-0 w-[280px] rounded-[20px] p-8 flex flex-col"
            style={{
              backgroundColor: product.bg,
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
              aspectRatio: '4/5',
            }}
          >
            <div className="flex-1 flex items-center justify-center mb-6">
              {product.icon}
            </div>
            <p className="text-[15px] leading-relaxed text-black/45 mb-4">
              {product.description}
            </p>
            <a
              href="#"
              className="text-sm font-medium text-[#0A8F5C] hover:underline"
            >
              Learn more
            </a>
          </div>
        ))}
      </div>

      {/* Tab Bar */}
      <div
        className="flex items-center gap-1 p-1.5 rounded-full"
        style={{ backgroundColor: 'rgba(255,255,255,0.08)' }}
      >
        {products.map((product) => (
          <button
            key={product.id}
            onClick={() => setActiveTab(product.id)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-semibold uppercase tracking-wide transition-all duration-300"
            style={{
              backgroundColor: activeTab === product.id ? '#fff' : 'transparent',
              color: activeTab === product.id ? '#111' : 'rgba(255,255,255,0.5)',
            }}
          >
            <span className="text-sm">{product.icon}</span>
            {product.title}
          </button>
        ))}
      </div>
    </section>
  );
}
