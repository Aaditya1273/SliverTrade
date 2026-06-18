const footerColumns = [
  {
    title: 'PRODUCTS',
    links: ['Codapay', 'Coda Links', 'Coda Webstore', 'Codashop', 'Coda Distribution', 'Giftcloud ↗', 'Recharge App ↗'],
  },
  {
    title: 'SERVICES',
    links: ['Marketing', 'Market Expansion'],
  },
  {
    title: 'KNOWLEDGE CENTER',
    links: ['Case Studies', 'Resources', 'Blog', 'Press', 'Documentation ↗', 'Publisher Support ↗'],
  },
  {
    title: 'COMPANY',
    links: ['About', 'Careers', 'Security', 'Events', 'Contact Us', 'Get Started ↗'],
  },
];

const bottomLinks = [
  'Terms & Conditions',
  'Privacy Policy',
  'Prohibited Content Policy',
  'Cookie Settings',
  'Become an Affiliate',
  'ISO 27001 Certification',
];

export default function Footer() {
  return (
    <footer
      id="contact"
      className="relative z-[3] pt-20 pb-10 px-6"
      style={{
        backgroundColor: '#0A0A0A',
        borderRadius: '24px 24px 0 0',
      }}
    >
      <div className="max-w-[1400px] mx-auto">
        {/* Top Row */}
        <div className="flex items-center justify-between mb-10">
          {/* Logo */}
          <svg width="100" height="24" viewBox="0 0 100 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <text
              x="0"
              y="19"
              fontFamily="Inter, sans-serif"
              fontWeight="900"
              fontSize="22"
              letterSpacing="-0.04em"
              fill="#FFFFFF"
            >
              CODA
            </text>
          </svg>

          {/* LinkedIn */}
          <a
            href="#"
            className="text-white/40 hover:text-white transition-colors duration-200"
            aria-label="LinkedIn"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
            </svg>
          </a>
        </div>

        {/* Divider */}
        <div className="h-px bg-white/10 mb-10" />

        {/* Link Columns */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10">
          {footerColumns.map((column) => (
            <div key={column.title}>
              <h4
                className="mb-4"
                style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: 'rgba(255,255,255,0.5)',
                }}
              >
                {column.title}
              </h4>
              <ul className="space-y-3">
                {column.links.map((link) => (
                  <li key={link}>
                    <a
                      href="#"
                      className="text-[15px] text-white/50 hover:text-white transition-colors duration-150"
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom Bar */}
        <div className="mt-16 pt-8 border-t border-white/5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            {bottomLinks.map((link, i) => (
              <span key={link} className="flex items-center gap-4">
                <a
                  href="#"
                  className="text-[11px] text-white/30 hover:text-white/60 transition-colors duration-150 uppercase tracking-wide"
                >
                  {link}
                </a>
                {i < bottomLinks.length - 1 && (
                  <span className="text-white/20 hidden md:inline">·</span>
                )}
              </span>
            ))}
          </div>
          <p className="text-[11px] text-white/30 uppercase tracking-wide">
            © 2026 Coda Payments Pte. Ltd · Site Credits
          </p>
        </div>
      </div>
    </footer>
  );
}
