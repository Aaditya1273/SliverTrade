import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const products = [
  {
    title: 'CODAPAY',
    description: 'Plug into our network of 400+ payment methods and generate revenue from around the world.',
    image: '/images/crystal-blue.jpg',
    gradient: 'linear-gradient(180deg, #1A2B4A 0%, #0F1F35 100%)',
  },
  {
    title: 'CODA WEBSTORE',
    description: 'A 100% customizable web store to sell your content your way.',
    image: '/images/leaf-green.jpg',
    gradient: 'linear-gradient(180deg, #1A3A2A 0%, #0F2A1A 100%)',
  },
  {
    title: 'CODA DISTRIBUTION',
    description: 'Tap into our extended network of e-commerce platforms and watch your reach and revenue grow.',
    image: '/images/spiral-pink.jpg',
    gradient: 'linear-gradient(180deg, #3A1A2A 0%, #2A0F1A 100%)',
  },
  {
    title: 'CODASHOP',
    description: 'Fast-track your audience reach on our global marketplace.',
    image: '/images/flower-purple.jpg',
    gradient: 'linear-gradient(180deg, #2A1A4A 0%, #1A0F3A 100%)',
  },
];

export default function ProductsGrid() {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sectionRef.current) return;

    const cards = sectionRef.current.querySelectorAll('.product-grid-card');

    gsap.fromTo(
      cards,
      { y: 80, opacity: 0, rotateY: -15 },
      {
        y: 0,
        opacity: 1,
        rotateY: 0,
        duration: 1,
        ease: 'expo.out',
        stagger: 0.15,
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
      className="relative z-[3] py-32 px-6"
      style={{ backgroundColor: '#111111' }}
    >
      <div className="max-w-[1400px] mx-auto">
        {/* Headline */}
        <h2
          className="text-center text-white font-extrabold mb-16"
          style={{
            fontSize: 'clamp(36px, 5vw, 72px)',
            letterSpacing: '-0.03em',
            lineHeight: 1.0,
          }}
        >
          GROW WITH CODA
        </h2>

        {/* Cards Grid */}
        <div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"
          style={{ perspective: '1000px' }}
        >
          {products.map((product) => (
            <div
              key={product.title}
              className="product-grid-card opacity-0 rounded-[20px] overflow-hidden transition-all duration-400 hover:-translate-y-3 group"
              style={{
                background: product.gradient,
                boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.boxShadow = '0 24px 80px rgba(0,0,0,0.4)';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.boxShadow = '0 8px 32px rgba(0,0,0,0.3)';
              }}
            >
              {/* Image */}
              <div className="relative h-[280px] overflow-hidden">
                <img
                  src={product.image}
                  alt={product.title}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                />
              </div>

              {/* Content */}
              <div className="p-6">
                <h3 className="text-white font-bold text-lg mb-2 flex items-center gap-2">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="10" cy="10" r="8" />
                    <circle cx="10" cy="10" r="3" />
                  </svg>
                  {product.title}
                </h3>
                <p className="text-white/50 text-[15px] leading-relaxed">
                  {product.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
