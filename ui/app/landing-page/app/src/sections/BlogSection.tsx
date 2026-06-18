import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const blogs = [
  {
    image: '/images/blog-paypay.jpg',
    category: 'Product',
    title: 'Coda partners with PayPay to offer more payment choice to gamers in Japan',
    date: 'Aug 05 2024',
    readTime: '3 mins',
  },
  {
    image: '/images/blog-visa.jpg',
    category: 'Product',
    title: 'Expanding global reach with new Visa partnership for seamless payments',
    date: 'Jul 22 2024',
    readTime: '4 mins',
  },
  {
    image: '/images/blog-insights.jpg',
    category: 'Insights',
    title: 'The state of digital payments in emerging markets: 2024 report',
    date: 'Jul 10 2024',
    readTime: '6 mins',
  },
];

export default function BlogSection() {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sectionRef.current) return;

    const cards = sectionRef.current.querySelectorAll('.blog-card');

    gsap.fromTo(
      cards,
      { y: 40, opacity: 0 },
      {
        y: 0,
        opacity: 1,
        duration: 0.6,
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
      id="knowledge"
      className="relative z-[3] py-32 px-6"
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
            LET'S DIVE IN
          </div>
        </div>

        {/* Headline */}
        <h2
          className="text-center text-white font-extrabold mb-16"
          style={{
            fontSize: 'clamp(36px, 5vw, 72px)',
            letterSpacing: '-0.03em',
            lineHeight: 1.0,
          }}
        >
          HERE'S WHAT YOU NEED TO KNOW
        </h2>

        {/* Blog Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {blogs.map((blog, i) => (
            <article
              key={i}
              className="blog-card opacity-0 group cursor-pointer"
            >
              {/* Image */}
              <div className="relative overflow-hidden rounded-xl mb-5 aspect-[16/10]">
                <img
                  src={blog.image}
                  alt={blog.title}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                />
              </div>

              {/* Content */}
              <span
                className="text-[11px] font-medium uppercase tracking-[0.12em] text-white/40"
              >
                {blog.category}
              </span>
              <h3 className="mt-2 text-lg font-semibold text-white leading-snug group-hover:underline transition-all duration-200">
                {blog.title}
              </h3>
              <p className="mt-3 text-[11px] text-white/40 uppercase tracking-wide">
                {blog.date} · {blog.readTime}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
