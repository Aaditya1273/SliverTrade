import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const words = ['YOUR', 'WEB', 'STORE', 'YOUR', 'WAY'];

export default function VisionSection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const stickyRef = useRef<HTMLDivElement>(null);
  const wordsRef = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (!sectionRef.current || !stickyRef.current) return;

    const wordElements = wordsRef.current.filter(Boolean) as HTMLDivElement[];

    // Set initial state
    wordElements.forEach((word) => {
      gsap.set(word, { y: '100%' });
    });

    // Create scroll-driven reveal
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: sectionRef.current,
        start: 'top top',
        end: 'bottom bottom',
        scrub: true,
      },
    });

    wordElements.forEach((word, i) => {
      const start = i / wordElements.length;
      tl.to(word, { y: '0%', ease: 'none' }, start);
    });

    return () => {
      tl.kill();
      ScrollTrigger.getAll().forEach((t) => t.kill());
    };
  }, []);

  return (
    <section
      ref={sectionRef}
      className="relative z-[3]"
      style={{ height: '300vh', backgroundColor: '#022B1F' }}
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
          YOUR VISION, BROUGHT TO LIFE.
        </div>

        {/* Words */}
        <div className="flex flex-col items-center">
          {words.map((word, i) => (
            <div key={i} className="overflow-hidden">
              <div
                ref={(el) => { wordsRef.current[i] = el; }}
                className="flex items-center justify-center"
                style={{
                  fontSize: 'clamp(60px, 10vw, 160px)',
                  fontWeight: 900,
                  letterSpacing: '-0.04em',
                  lineHeight: 0.85,
                  color: i === words.length - 1 ? '#D4E8A8' : '#FFFFFF',
                }}
              >
                {word}
                {i === 2 && (
                  <svg
                    width="0.5em"
                    height="0.5em"
                    viewBox="0 0 48 48"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    className="ml-3 inline-block"
                  >
                    <circle cx="24" cy="24" r="20" />
                    <ellipse cx="24" cy="24" rx="10" ry="20" />
                    <line x1="4" y1="24" x2="44" y2="24" />
                    <path d="M8 14c8-4 24-4 32 0" />
                    <path d="M8 34c8 4 24 4 32 0" />
                  </svg>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
