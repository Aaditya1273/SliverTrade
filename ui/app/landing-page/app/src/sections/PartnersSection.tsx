import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const partnerNames = ['tinder', 'Activision', 'Riot Games', 'Netflix', 'Spotify', 'Epic Games'];

export default function PartnersSection() {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sectionRef.current) return;

    const headlineWords = sectionRef.current.querySelectorAll('.partner-word');
    const showcase = sectionRef.current.querySelector('.partner-showcase');

    gsap.fromTo(
      headlineWords,
      { y: 30, opacity: 0 },
      {
        y: 0,
        opacity: 1,
        duration: 0.6,
        ease: 'expo.out',
        stagger: 0.08,
        scrollTrigger: {
          trigger: sectionRef.current,
          start: 'top 80%',
          toggleActions: 'play none none none',
        },
      }
    );

    if (showcase) {
      gsap.fromTo(
        showcase,
        { scale: 0.95, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 1,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: sectionRef.current,
            start: 'top 70%',
            toggleActions: 'play none none none',
          },
        }
      );
    }

    return () => {
      ScrollTrigger.getAll().forEach((t) => t.kill());
    };
  }, []);

  return (
    <section
      ref={sectionRef}
      id="company"
      className="relative z-[3] pt-40 pb-32 px-6"
      style={{ backgroundColor: '#022B1F' }}
    >
      <div className="max-w-[1400px] mx-auto">
        {/* Label */}
        <div className="flex justify-center mb-8">
          <div
            className="border border-white/20 rounded-full px-5 py-2"
            style={{
              fontSize: '12px',
              fontWeight: 600,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: '#FFFFFF',
            }}
          >
            WHO WE PARTNER WITH
          </div>
        </div>

        {/* Headline */}
        <div className="text-center mb-12">
          <h2
            className="text-white font-extrabold"
            style={{
              fontSize: 'clamp(36px, 5vw, 72px)',
              letterSpacing: '-0.03em',
              lineHeight: 1.0,
            }}
          >
            <span className="partner-word inline-block opacity-0">OUR</span>{' '}
            <span className="partner-word inline-block opacity-0">PARTNERS</span>
          </h2>
          <h2
            className="text-white font-extrabold flex items-center justify-center gap-3"
            style={{
              fontSize: 'clamp(36px, 5vw, 72px)',
              letterSpacing: '-0.03em',
              lineHeight: 1.0,
            }}
          >
            <span className="partner-word inline-block opacity-0">THE</span>{' '}
            <span className="partner-word inline-block opacity-0">BEST</span>{' '}
            <span className="partner-word inline-block opacity-0">IN</span>{' '}
            <span className="partner-word inline-flex items-center gap-2 opacity-0">
              <svg
                width="0.5em"
                height="0.5em"
                viewBox="0 0 48 48"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="24" cy="24" r="20" />
                <circle cx="24" cy="20" r="3" fill="currentColor" stroke="none" />
                <circle cx="24" cy="20" r="3" fill="currentColor" stroke="none" />
                <path d="M14 30c4 5 16 5 20 0" strokeLinecap="round" />
              </svg>
              CONTENT
            </span>
          </h2>
        </div>

        {/* Showcase */}
        <div
          className="partner-showcase relative rounded-3xl overflow-hidden mb-12 opacity-0"
          style={{ aspectRatio: '16/9' }}
        >
          <img
            src="/images/partner-showcase.jpg"
            alt="Partner showcase"
            className="w-full h-full object-cover"
          />
          {/* Gradient overlay */}
          <div
            className="absolute inset-0"
            style={{
              background: 'linear-gradient(to top, rgba(0,0,0,0.5) 0%, transparent 50%)',
            }}
          />

          {/* Partner logo */}
          <div className="absolute bottom-10 left-10">
            <span className="text-white text-3xl font-bold tracking-tight">tinder</span>
          </div>

          {/* Play button */}
          <button
            className="absolute bottom-10 right-10 w-16 h-16 rounded-full bg-white flex items-center justify-center transition-transform duration-200 hover:scale-110"
            aria-label="Play video"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="#111">
              <polygon points="5,3 19,12 5,21" />
            </svg>
          </button>
        </div>

        {/* Partner logos row */}
        <div className="flex flex-wrap items-center justify-center gap-12">
          {partnerNames.map((name) => (
            <span
              key={name}
              className="text-white/40 hover:text-white/80 transition-opacity duration-200 text-lg font-semibold tracking-tight cursor-pointer"
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
