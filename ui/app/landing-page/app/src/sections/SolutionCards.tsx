import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const cards = [
  {
    number: '01',
    title: 'EXPAND WITH CODA',
    subtitle: 'Maximize your global reach',
    description:
      'Integrate Codapay, customize your web store, and access a global distribution network—grow your audience across multiple markets, effortlessly.',
    bg: '#1A2B4A',
  },
  {
    number: '02',
    title: 'EARN WITH CODA',
    subtitle: 'Monetize globally',
    description:
      "Monetizing with Coda means you aren't limited to card payments. Access 90% of the world's preferred payment methods—from e-wallets to direct carrier billing and more.",
    bg: '#1A1A1A',
  },
  {
    number: '03',
    title: 'COMPLY WITH CODA',
    subtitle: 'Stress-free global growth',
    description:
      'As your Merchant of Record, we take on the risks of operating in multiple markets, and handle regulatory and tax compliance. Scale confidently across markets minus the stress.',
    bg: '#0A2B1F',
  },
];

export default function SolutionCards() {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sectionRef.current) return;

    const cardEls = sectionRef.current.querySelectorAll('.solution-card');

    gsap.fromTo(
      cardEls,
      { y: 60, opacity: 0 },
      {
        y: 0,
        opacity: 1,
        duration: 0.8,
        ease: 'expo.out',
        stagger: 0.12,
        scrollTrigger: {
          trigger: sectionRef.current,
          start: 'top 85%',
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
      className="relative z-[3] py-20 px-6"
      style={{ backgroundColor: '#111111' }}
    >
      <div className="max-w-[1400px] mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
        {cards.map((card) => (
          <div
            key={card.number}
            className="solution-card opacity-0 rounded-[20px] p-10 transition-all duration-300 hover:-translate-y-2"
            style={{
              backgroundColor: card.bg,
              boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.boxShadow = '0 20px 60px rgba(0,0,0,0.3)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.boxShadow = '0 8px 32px rgba(0,0,0,0.2)';
            }}
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-6">
              <h3
                className="text-white font-extrabold text-2xl md:text-3xl"
                style={{ letterSpacing: '-0.02em' }}
              >
                {card.title}
              </h3>
              <span
                className="flex-shrink-0 w-8 h-8 rounded-full border border-white/20 flex items-center justify-center text-white/60 text-xs"
                style={{ fontFamily: "'IBM Plex Mono', monospace" }}
              >
                {card.number}
              </span>
            </div>

            {/* Subtitle */}
            <h4 className="text-white font-semibold text-lg mb-4">{card.subtitle}</h4>

            {/* Description */}
            <p className="text-white/50 text-[15px] leading-relaxed">{card.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
