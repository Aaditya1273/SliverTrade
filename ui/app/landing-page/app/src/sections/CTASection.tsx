import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export default function CTASection() {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sectionRef.current) return;

    const label = sectionRef.current.querySelector('.cta-label');
    const words = sectionRef.current.querySelectorAll('.cta-word');
    const button = sectionRef.current.querySelector('.cta-button');

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: sectionRef.current,
        start: 'top 75%',
        toggleActions: 'play none none none',
      },
    });

    if (label) {
      tl.fromTo(label, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.4 }, 0);
    }

    if (words.length) {
      tl.fromTo(
        words,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.5, stagger: 0.08, ease: 'expo.out' },
        0.2
      );
    }

    if (button) {
      tl.fromTo(button, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5 }, 0.5);
    }

    return () => {
      tl.kill();
    };
  }, []);

  return (
    <section
      ref={sectionRef}
      id="cta"
      className="relative z-[3] py-40 px-6"
      style={{ backgroundColor: '#022B1F' }}
    >
      <div className="max-w-[1400px] mx-auto text-center">
        {/* Label */}
        <div
          className="cta-label opacity-0 mb-6"
          style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '11px',
            fontWeight: 500,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: 'rgba(255,255,255,0.5)',
          }}
        >
          READY TO GROW?
        </div>

        {/* Headline */}
        <h2
          className="text-white font-black mb-10"
          style={{
            fontSize: 'clamp(40px, 8vw, 120px)',
            letterSpacing: '-0.04em',
            lineHeight: 0.88,
          }}
        >
          <span className="cta-word inline-block opacity-0">WE'RE</span>{' '}
          <span className="cta-word inline-block opacity-0">READY</span>
          <br />
          <span className="cta-word inline-block opacity-0">TO</span>{' '}
          <span className="cta-word inline-block opacity-0" style={{ color: '#D4E8A8' }}>
            GO
          </span>
        </h2>

        {/* Button */}
        <a
          href="#"
          className="cta-button opacity-0 inline-block bg-white text-[#111111] font-semibold text-base px-10 py-4 rounded-full hover:bg-[#D4E8A8] transition-colors duration-200"
        >
          Get started
        </a>
      </div>
    </section>
  );
}
