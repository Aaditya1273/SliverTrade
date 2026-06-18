import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const VERTEX_SHADER = `
attribute vec2 a_pos;
void main() {
  gl_Position = vec4(a_pos, 0.0, 1.0);
}
`;

const PASS1_FRAGMENT_SHADER = `
precision highp float;

uniform float u_time;
uniform vec2 u_res;
uniform float u_scroll;
uniform vec2 u_mouse;
uniform float u_speed;
uniform float u_colorShift;
uniform float u_blobCount;
uniform float u_metaball;

#define PI 3.14159265359
#define CIRCLE_COUNT 25
#define baseRadius 0.045
#define radiusVar 0.018
#define speed 0.4

vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec3 permute(vec3 x) { return mod289(((x * 34.0) + 1.0) * x); }

float snoise(vec2 v) {
  const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
  vec2 i = floor(v + dot(v, C.yy));
  vec2 x0 = v - i + dot(i, C.xx);
  vec2 i1;
  i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod289(i);
  vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
  vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
  m = m * m;
  m = m * m;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
  vec3 g;
  g.x = a0.x * x0.x + h.x * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}

float smoothMin(float a, float b, float k) {
  return -(k) * log(exp(-a / (k)) + exp(-b / (k)));
}

void main() {
  vec2 uv = gl_FragCoord.xy / u_res;
  float aspect = u_res.x / u_res.y;
  float t = u_time * u_speed;
  float scrollOffset = u_scroll * 0.15;
  float sum = 0.0;
  float influence = 0.0;

  for (int i = 0; i < CIRCLE_COUNT; i++) {
    float fi = float(i);
    float phaseX = fi * 1.618 + scrollOffset;
    float phaseY = fi * 2.718 + scrollOffset * 0.7;
    float cx = snoise(vec2(phaseX * 0.3, t * 0.15 + fi * 0.1)) * 0.38;
    float cy = snoise(vec2(phaseY * 0.3, t * 0.12 + fi * 0.15 + 50.0)) * 0.32;
    float r = baseRadius + radiusVar * sin(t * 0.2 + fi * 0.5);
    float dx = (uv.x - (cx + 0.5)) * aspect;
    float dy = uv.y - (cy + 0.5);
    float dist = sqrt(dx * dx + dy * dy);
    if (u_metaball > 0.5) {
      sum = smoothMin(sum, dist - r, 0.5);
    } else {
      sum += dist - r;
    }
    influence += max(0.0, 1.0 - dist / (r * 3.0));
  }

  float edge = 1.0 - smoothstep(-0.008, 0.012, sum);
  float field = edge * 0.8 + influence * 0.08;
  gl_FragColor = vec4(field, edge, influence, 1.0);
}
`;

const PASS2_FRAGMENT_SHADER = `
precision highp float;

uniform float u_time;
uniform vec2 u_res;
uniform float u_colorShift;
uniform vec2 u_mouse;
uniform float u_blobCount;
uniform float u_speed;
uniform sampler2D u_pass1;

vec3 col0 = vec3(2.0 / 255.0, 43.0 / 255.0, 31.0 / 255.0);
vec3 col1 = vec3(10.0 / 255.0, 143.0 / 255.0, 92.0 / 255.0);
vec3 col2 = vec3(212.0 / 255.0, 232.0 / 255.0, 168.0 / 255.0);
vec3 col3 = vec3(245.0 / 255.0, 245.0 / 255.0, 240.0 / 255.0);

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void main() {
  vec2 uv = gl_FragCoord.xy / u_res;
  vec4 raw = texture2D(u_pass1, uv);
  float field = raw.r;
  float edge = raw.g;
  float influence = raw.b;
  float t = u_time * 0.3;

  vec3 baseColor = mix(col0, col1, smoothstep(0.05, 0.25, field));
  baseColor = mix(baseColor, col2, smoothstep(0.25, 0.45, field) * 0.6);
  baseColor = mix(baseColor, col3, smoothstep(0.45, 0.7, field) * 0.35);

  float noise = hash(uv * u_res + t);
  baseColor += (noise - 0.5) * 0.025;

  float mouseMask = 1.0;
  if (u_mouse.x > 0.0) {
    vec2 mUV = u_mouse / u_res;
    float mDist = length(uv - mUV);
    mouseMask = 1.0 - smoothstep(0.0, 0.25, mDist);
  }

  float colorShift = u_colorShift * mouseMask;

  vec2 lightPos = vec2(0.3 + sin(t * 0.4) * 0.15, 0.4 + cos(t * 0.35) * 0.1);
  vec2 lightDir = normalize(lightPos - uv);
  float dx = dFdx(field);
  float dy = dFdy(field);
  vec3 normal = normalize(vec3(-dx, -dy, 1.0));
  float diffuse = max(dot(normal, vec3(lightDir, 0.3)), 0.0);
  float specular = pow(max(dot(normal, vec3(0.5, 0.5, 0.8)), 0.0), 30.0) * 0.15;
  baseColor += (diffuse * 0.12 + specular) * colorShift;

  float edgeGlow = edge * (0.08 + 0.04 * sin(t * 1.5));
  baseColor += col1 * edgeGlow;

  float rim = pow(1.0 - max(dot(normal, vec3(0.0, 0.0, 1.0)), 0.0), 4.0) * 0.1;
  baseColor += col2 * rim * edge;

  float vignette = smoothstep(0.0, 1.0, 1.0 - dot(uv - 0.5, uv - 0.5) * 1.8);
  baseColor *= vignette;

  baseColor = baseColor / (1.0 + baseColor * 0.15);

  gl_FragColor = vec4(baseColor, 1.0);
}
`;

function initShader(canvas: HTMLCanvasElement) {
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const planeGeo = new THREE.PlaneGeometry(2, 2);

  const rtOptions = {
    minFilter: THREE.LinearFilter,
    magFilter: THREE.LinearFilter,
    format: THREE.RGBAFormat,
    type: THREE.UnsignedByteType,
  };

  let rt1 = new THREE.WebGLRenderTarget(
    window.innerWidth * Math.min(window.devicePixelRatio, 2),
    window.innerHeight * Math.min(window.devicePixelRatio, 2),
    rtOptions
  );
  let rt2 = new THREE.WebGLRenderTarget(
    window.innerWidth * Math.min(window.devicePixelRatio, 2),
    window.innerHeight * Math.min(window.devicePixelRatio, 2),
    rtOptions
  );

  const uniforms = {
    u_time: { value: 0.0 },
    u_res: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
    u_scroll: { value: 0.0 },
    u_mouse: { value: new THREE.Vector2(-1.0, -1.0) },
    u_speed: { value: 1.0 },
    u_colorShift: { value: 1.0 },
    u_blobCount: { value: 25.0 },
    u_metaball: { value: 1.0 },
  };

  const pass1Material = new THREE.ShaderMaterial({
    vertexShader: VERTEX_SHADER,
    fragmentShader: PASS1_FRAGMENT_SHADER,
    uniforms,
  });

  const pass2Material = new THREE.ShaderMaterial({
    vertexShader: VERTEX_SHADER,
    fragmentShader: PASS2_FRAGMENT_SHADER,
    uniforms: {
      ...uniforms,
      u_pass1: { value: null },
    },
  });

  const scene1 = new THREE.Scene();
  const mesh1 = new THREE.Mesh(planeGeo, pass1Material);
  scene1.add(mesh1);

  const scene2 = new THREE.Scene();
  const mesh2 = new THREE.Mesh(planeGeo, pass2Material);
  scene2.add(mesh2);

  const handleMouseMove = (e: MouseEvent) => {
    const dpr = Math.min(window.devicePixelRatio, 2);
    uniforms.u_mouse.value.set(e.clientX * dpr, (window.innerHeight - e.clientY) * dpr);
  };

  const handleMouseLeave = () => {
    uniforms.u_mouse.value.set(-1.0, -1.0);
  };

  canvas.addEventListener('mousemove', handleMouseMove);
  canvas.addEventListener('mouseleave', handleMouseLeave);

  let animId: number;

  const animate = (time: number) => {
    const t = time * 0.001;
    uniforms.u_time.value = t;
    uniforms.u_res.value.set(renderer.domElement.width, renderer.domElement.height);
    uniforms.u_scroll.value = THREE.MathUtils.clamp(window.scrollY / (window.innerHeight * 3), 0, 3);

    renderer.setRenderTarget(rt1);
    renderer.render(scene1, camera);

    pass2Material.uniforms.u_pass1.value = rt1.texture;
    renderer.setRenderTarget(null);
    renderer.render(scene2, camera);

    animId = requestAnimationFrame(animate);
  };

  animId = requestAnimationFrame(animate);

  const handleResize = () => {
    renderer.setSize(window.innerWidth, window.innerHeight);
    const dpr = Math.min(window.devicePixelRatio, 2);
    rt1.dispose();
    rt2.dispose();
    rt1 = new THREE.WebGLRenderTarget(window.innerWidth * dpr, window.innerHeight * dpr, rtOptions);
    rt2 = new THREE.WebGLRenderTarget(window.innerWidth * dpr, window.innerHeight * dpr, rtOptions);
  };

  window.addEventListener('resize', handleResize);

  return () => {
    cancelAnimationFrame(animId);
    canvas.removeEventListener('mousemove', handleMouseMove);
    canvas.removeEventListener('mouseleave', handleMouseLeave);
    window.removeEventListener('resize', handleResize);
    renderer.dispose();
    rt1.dispose();
    rt2.dispose();
    planeGeo.dispose();
    pass1Material.dispose();
    pass2Material.dispose();
  };
}

export default function HeroSection() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const canvasWrapRef = useRef<HTMLDivElement>(null);
  const heroRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const bgOverlayRef = useRef<HTMLDivElement>(null);
  const eyebrowRef = useRef<HTMLDivElement>(null);
  const pillRef = useRef<HTMLAnchorElement>(null);
  const headlineRef = useRef<HTMLDivElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    const cleanup = initShader(canvasRef.current);

    // Canvas fade on scroll
    if (canvasWrapRef.current) {
      gsap.to(canvasWrapRef.current, {
        opacity: 0,
        ease: 'none',
        scrollTrigger: {
          trigger: heroRef.current,
          start: '50% top',
          end: '150% top',
          scrub: true,
        },
      });
    }

    // Background color transition
    if (bgOverlayRef.current) {
      gsap.fromTo(
        bgOverlayRef.current,
        { opacity: 0 },
        {
          opacity: 1,
          ease: 'none',
          scrollTrigger: {
            trigger: heroRef.current,
            start: '50% top',
            end: '150% top',
            scrub: true,
          },
        }
      );
    }

    // Hero content scroll animation
    if (contentRef.current) {
      gsap.to(contentRef.current, {
        rotateX: 70,
        y: 100,
        opacity: 0.3,
        ease: 'none',
        scrollTrigger: {
          trigger: heroRef.current,
          start: 'top top',
          end: 'bottom top',
          scrub: true,
        },
      });
    }

    // Load animations
    const tl = gsap.timeline({ delay: 0.5 });

    if (eyebrowRef.current) {
      tl.fromTo(eyebrowRef.current, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.6 }, 0.2);
    }

    if (pillRef.current) {
      tl.fromTo(pillRef.current, { opacity: 0 }, { opacity: 1, duration: 0.6 }, 0.4);
    }

    // Headline 3D rotation
    if (headlineRef.current) {
      const words = headlineRef.current.querySelectorAll('.hero-word');
      tl.fromTo(
        words,
        { rotateX: -90, opacity: 0 },
        {
          rotateX: 0,
          opacity: 1,
          duration: 1.2,
          ease: 'expo.out',
          stagger: 0.15,
        },
        0.5
      );
    }

    if (subtitleRef.current) {
      tl.fromTo(
        subtitleRef.current,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.8 },
        0.8
      );
    }

    return () => {
      cleanup();
      ScrollTrigger.getAll().forEach((t) => t.kill());
    };
  }, []);

  return (
    <>
      {/* Shader Canvas */}
      <div
        ref={canvasWrapRef}
        className="fixed inset-0 z-0"
        style={{ pointerEvents: 'auto' }}
      >
        <canvas
          ref={canvasRef}
          style={{
            width: '100%',
            height: '100%',
            display: 'block',
          }}
        />
      </div>

      {/* Background Color Overlay */}
      <div
        ref={bgOverlayRef}
        className="fixed inset-0 z-[1] pointer-events-none"
        style={{ backgroundColor: '#022B1F', opacity: 0 }}
      />

      {/* Hero Content */}
      <section
        ref={heroRef}
        className="relative z-[2] min-h-[100dvh] flex items-center justify-center px-6"
        style={{ backgroundColor: 'transparent', perspective: '1000px' }}
      >
        <div
          ref={contentRef}
          className="text-center flex flex-col items-center"
          style={{ transformStyle: 'preserve-3d' }}
        >
          {/* Eyebrow */}
          <div
            ref={eyebrowRef}
            className="opacity-0 mb-6"
            style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: '11px',
              fontWeight: 500,
              letterSpacing: '0.12em',
              textTransform: 'uppercase' as const,
              color: 'rgba(0,0,0,0.45)',
            }}
          >
            GROW WITH US
          </div>

          {/* Pill CTA */}
          <a
            ref={pillRef}
            href="#cta"
            className="opacity-0 mb-8 inline-flex items-center gap-2 border border-black/20 rounded-full px-5 py-2 text-[13px] font-medium text-[#111111] hover:bg-[#111111] hover:text-white transition-all duration-200"
          >
            Ready to grow? We're ready to go
            <span className="text-sm">→</span>
          </a>

          {/* Main Headline */}
          <div ref={headlineRef} className="mb-8">
            <div className="overflow-hidden">
              <div
                className="hero-word flex items-center justify-center gap-2"
                style={{
                  fontSize: 'clamp(48px, 12vw, 180px)',
                  fontWeight: 900,
                  letterSpacing: '-0.04em',
                  lineHeight: 0.85,
                  color: '#111111',
                  transformOrigin: 'center bottom',
                }}
              >
                CUSTOMIZE
                <svg width="0.6em" height="0.6em" viewBox="0 0 48 48" fill="none" stroke="#111111" strokeWidth="2">
                  <circle cx="24" cy="24" r="20" />
                  <circle cx="24" cy="24" r="12" />
                  <circle cx="24" cy="24" r="4" />
                  <line x1="24" y1="0" x2="24" y2="48" />
                  <line x1="0" y1="24" x2="48" y2="24" />
                </svg>
                MONETIZE
                <svg width="0.6em" height="0.6em" viewBox="0 0 48 48" fill="none" stroke="#111111" strokeWidth="2">
                  <circle cx="24" cy="24" r="20" />
                  <text x="24" y="30" textAnchor="middle" fontSize="20" fontWeight="700" fill="#111111" stroke="none">$</text>
                </svg>
              </div>
            </div>
            <div className="overflow-hidden">
              <div
                className="hero-word"
                style={{
                  fontSize: 'clamp(48px, 12vw, 180px)',
                  fontWeight: 900,
                  letterSpacing: '-0.04em',
                  lineHeight: 0.85,
                  color: '#111111',
                  transformOrigin: 'center bottom',
                }}
              >
                MAXIMIZE
              </div>
            </div>
          </div>

          {/* Subtitle */}
          <p
            ref={subtitleRef}
            className="opacity-0 max-w-[480px] text-lg text-black/45 leading-relaxed"
          >
            Accelerate Growth with Coda's Merchant of Record and Payment Solutions
          </p>
        </div>
      </section>
    </>
  );
}
