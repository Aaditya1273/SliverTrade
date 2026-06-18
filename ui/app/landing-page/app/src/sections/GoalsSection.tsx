import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export default function GoalsSection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const stickyRef = useRef<HTMLDivElement>(null);
  const headlineRef = useRef<HTMLDivElement>(null);
  const line1Ref = useRef<HTMLDivElement>(null);
  const line2Ref = useRef<HTMLDivElement>(null);
  const underlineRef = useRef<HTMLDivElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    if (!sectionRef.current || !stickyRef.current) return;

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: sectionRef.current,
        start: 'top top',
        end: 'bottom bottom',
        scrub: true,
      },
    });

    // Headline scales down
    if (headlineRef.current) {
      tl.fromTo(
        headlineRef.current,
        { scale: 1.5 },
        { scale: 1, ease: 'none' },
        0
      );
    }

    // Lines separate
    if (line1Ref.current) {
      tl.fromTo(line1Ref.current, { y: 20 }, { y: -20, ease: 'none' }, 0);
    }
    if (line2Ref.current) {
      tl.fromTo(line2Ref.current, { y: -20 }, { y: 20, ease: 'none' }, 0);
    }

    // Underline appears
    if (underlineRef.current) {
      tl.fromTo(underlineRef.current, { scaleX: 0 }, { scaleX: 1, ease: 'none' }, 0.5);
    }

    // Subtitle fades in
    if (subtitleRef.current) {
      tl.fromTo(subtitleRef.current, { opacity: 0, y: 20 }, { opacity: 1, y: 0, ease: 'none' }, 0.6);
    }

    return () => {
      tl.kill();
    };
  }, []);

  return (
    <section
      ref={sectionRef}
      id="solutions"
      className="relative z-[3]"
      style={{ height: '200vh', backgroundColor: '#111111' }}
    >
      <div
        ref={stickyRef}
        className="sticky top-0 h-[100dvh] flex flex-col items-center justify-center px-6 overflow-hidden"
      >
        {/* Label */}
        <div
          className="mb-8"
          style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '11px',
            fontWeight: 500,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: 'rgba(255,255,255,0.5)',
          }}
        >
          WHAT'S YOUR GOAL
        </div>

        {/* Headline */}
        <div ref={headlineRef} className="text-center">
          <div
            ref={line1Ref}
            className="text-white font-black"
            style={{
              fontSize: 'clamp(40px, 9vw, 140px)',
              letterSpacing: '-0.04em',
              lineHeight: 0.85,
            }}
          >
            ACCEPT PAYMENTS
          </div>
          <div
            ref={line2Ref}
            className="text-white font-black flex items-center justify-center gap-4"
            style={{
              fontSize: 'clamp(40px, 9vw, 140px)',
              letterSpacing: '-0.04em',
              lineHeight: 0.85,
            }}
          >
            <svg
              width="0.5em"
              height="0.5em"
              viewBox="0 0 48 48"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="24" cy="24" r="20" />
              <ellipse cx="24" cy="24" rx="10" ry="20" />
              <line x1="4" y1="24" x2="44" y2="24" />
              <path d="M8 14c8-4 24-4 32 0" />
              <path d="M8 34c8 4 24 4 32 0" />
            </svg>
            EVERYWHERE
          </div>

          {/* Dashed underline */}
          <div
            ref={underlineRef}
            className="mt-6 mx-auto h-px w-48 origin-left"
            style={{
              background: 'repeating-linear-gradient(90deg, rgba(255,255,255,0.3) 0, rgba(255,255,255,0.3) 6px, transparent 6px, transparent 12px)',
              transform: 'scaleX(0)',
            }}
          />
        </div>

        {/* Subtitle */}
        <p
          ref={subtitleRef}
          className="mt-8 text-xl text-white/50 opacity-0"
        >
          Grow your paying audience
        </p>

        {/* Navigation arrows */}
        <div className="absolute left-6 top-1/2 -translate-y-1/2">
          <button
            className="w-12 h-12 rounded-full border border-white/20 flex items-center justify-center text-white hover:border-white transition-colors duration-200"
            aria-label="Previous"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
        </div>
        <div className="absolute right-6 top-1/2 -translate-y-1/2">
          <button
            className="w-12 h-12 rounded-full border border-white/20 flex items-center justify-center text-white hover:border-white transition-colors duration-200"
            aria-label="Next"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        </div>
      </div>
    </section>
  );
}
