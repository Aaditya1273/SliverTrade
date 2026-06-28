# Landing Page Design Specification

A complete, opinionated design brief for a modern, editorial, motion-rich product landing page. Hand this file to any AI builder and it will produce a distinctive, non-generic result. Do not deviate from these tokens.

---

## 1. Brand Personality

- **Tone:** Editorial, confident, premium-minimal. Think Swiss design meets fintech meets gaming culture.
- **Energy:** Calm, oversized typography that *breathes*, punctuated by sharp motion moments.
- **Refusals:** No purple/indigo SaaS gradients. No rounded "friendly" illustrations. No stock hero photo of smiling people. No glassmorphism. No emoji icons.

---

## 2. Color System (use OKLCH or HEX exactly)

Warm off-white "paper" background with near-black ink. Single warm accent for emphasis. Light mode is primary.

| Token | Value (HEX) | Usage |
|---|---|---|
| `--background` | `#F4F1EA` | Page background (warm cream, NOT pure white) |
| `--foreground` | `#0E0E0C` | Headlines, body text, primary buttons |
| `--muted` | `#E6E1D6` | Card surfaces, dividers, faint fills |
| `--muted-foreground` | `#6B6760` | Secondary text, captions, eyebrows |
| `--border` | `#D9D3C5` | Hairline borders (always 1px) |
| `--accent` | `#E25A2B` | Single warm accent — links underline, dot indicators, highlights |
| `--inverse-bg` | `#0E0E0C` | Footer / CTA section background |
| `--inverse-fg` | `#F4F1EA` | Text on inverse sections |

Rules:
- Never use pure white (`#FFFFFF`) or pure black (`#000000`).
- One accent only. Do not introduce a second hue.
- No gradients on text or buttons. Gradients allowed ONLY as faint radial glows behind hero (10% opacity max).

---

## 3. Typography

Two families. No third font.

- **Display:** `Archivo Black` (Google Fonts) — tight letter-spacing `-0.02em`, used for all headlines.
- **Body:** `Inter` (Google Fonts) weights 400 / 500 — paragraphs, nav, buttons.
- **Mono accent:** `JetBrains Mono` weight 500, uppercase, letter-spacing `0.18em`, size `11px` — used ONLY for eyebrow labels above sections ("01 / Products", "Who we partner with", etc.).

### Type Scale
| Role | Size | Line-height | Notes |
|---|---|---|---|
| Hero H1 | `clamp(3.5rem, 11vw, 11rem)` | `0.88` | Display font, words appear on separate lines, each word animates in independently |
| Section H2 | `clamp(2.5rem, 6vw, 5rem)` | `0.95` | Display font |
| Oversized CTA | `clamp(4rem, 16vw, 15rem)` | `0.85` | Display font, two stacked lines, second line at 40% opacity |
| Stat number | `clamp(5rem, 18vw, 15rem)` | `1` | Display font, animated counter |
| Body large | `1.25rem` | `1.6` | For hero subtitle, intros |
| Body | `1rem` | `1.6` | Default |
| Eyebrow | `11px` | `1.2` | Mono, uppercase, `0.18em` tracking |

Rule: headlines are ALWAYS lowercase or sentence case. Never ALL CAPS in display font.

---

## 4. Layout & Grid

- **Max content width:** `1400px`, centered, with `24px` (mobile) → `48px` (desktop) horizontal padding.
- **Vertical rhythm:** Section padding `py-32` (128px) minimum between sections, `py-40` for the CTA section.
- **12-column grid** for hero and partner sections. Frequently use asymmetric splits: `col-span-5 col-start-7` (headline left, paragraph right-of-center) to create deliberate negative space.
- **Borders:** Hairline `1px solid var(--border)` between every major section. No box shadows, no card elevation.
- **Radius:** Pills only — `9999px` for buttons. Cards/sections are sharp corners (`0px`). No `rounded-lg`.

---

## 5. Components

### 5.1 Announcement Bar (top)
- Full-width strip, `--inverse-bg` background, `--inverse-fg` text.
- Single line of mono `11px` uppercase text + dismiss "×" icon on the right.
- Underlined inline link with `underline-offset-4`.

### 5.2 Navigation
- Sticky, transparent at top, fades to `background/85%` with `backdrop-blur(14px)` after `20px` scroll. Animate this transition over `250ms`.
- Left: brand wordmark in display font, size `36px`.
- Center: 4 nav links, Inter `14px` weight 500. Each link has an animated underline that grows from left on hover (`0 → 100%` width over `300ms`).
- Right: small flag/region chip + text link + filled pill CTA.

### 5.3 Hero
- Eyebrow row: small dot + mono label.
- Headline: 3–5 short words, each on its own visual line, each animates in with `y: 110% → 0` + `opacity: 0 → 1`, staggered `0.12s`, easing `[0.22, 1, 0.36, 1]`, duration `0.9s`.
- Subtitle paragraph offset to the right column (`md:col-start-7`).
- Two buttons: primary filled pill (dark) + ghost pill (border).
- Decorative dashed arc SVG at the bottom, `opacity-30`, stroked with `stroke-dasharray: 4 8`.
- Entire hero block parallax: translateY `0 → 200px` and opacity `1 → 0` as user scrolls past it.

### 5.4 Stats Section
- Centered chip "The numbers speak for themselves" with hairline border.
- Vertical thin divider line below it (`1px × 64px`).
- Counter `01 / 05` mono label.
- Auto-advancing carousel (every `2800ms`) of single oversized number + label.
- Each number animates from `0` to target value over `1.8s` with easing `[0.22, 1, 0.36, 1]`.
- Dashed arc SVG behind each number redraws its path (`pathLength: 0 → 1` over `1.4s`).
- Pagination dots at bottom: active dot is `32px × 6px` pill, inactive dots are `6px × 6px`.

### 5.5 Partners / Logo Marquee
- Two-column intro (eyebrow + display H2 on left, paragraph on right).
- Marquee row below: brand names in display font `text-6xl` → `text-8xl` separated by a faint accent-colored `✦` glyph.
- Infinite horizontal scroll, `40s` linear loop, duplicated content for seamless wrap.

### 5.6 Oversized CTA Section
- `--inverse-bg` background, `--inverse-fg` text.
- Eyebrow mono label at top.
- Two stacked display lines, each `clamp(4rem, 16vw, 15rem)`. First line drifts LEFT on scroll (`-15% → 10%`), second line drifts RIGHT (`10% → -15%`), opposing horizontal parallax tied to scrollYProgress.
- Second line at 40% opacity.
- Large pill button below, light fill on dark, with arrow icon that translates `+2px x / -2px y` on hover.

### 5.7 Footer
- 6-column grid: brand block (col-span-2) + 4 link columns.
- Each column has a mono eyebrow label and a vertical list of links, `2.5` line-height.
- Bottom row: copyright left, legal links right, separated by hairline border.

---

## 6. Motion System

Library: **Motion for React** (formerly Framer Motion).

### Global Easings
- Primary easing curve: `[0.22, 1, 0.36, 1]` (expo-out feel). Use everywhere unless noted.
- Snappy UI transitions: `0.25s` ease-out.
- Hero/headline reveals: `0.9s`.
- Counters and SVG path draws: `1.4s – 1.8s`.

### Required Animations
1. **Scroll-fade nav background** — `backdropFilter` and `backgroundColor` animate when `scrollY > 20`.
2. **Hero word stagger** — each word from `y: 110%, opacity: 0` to `y: 0, opacity: 1`, delay `0.15 + i * 0.12`.
3. **Hero parallax** — wrapper `y: 0 → 200px`, `opacity: 1 → 0` tied to `useScroll` on the hero ref.
4. **Stat counter** — `useMotionValue` animated to target, rounded each frame.
5. **Stat arc redraw** — SVG path `pathLength 0 → 1` on every index change.
6. **Marquee** — pure CSS keyframe `translateX(0) → translateX(-50%)`, `40s linear infinite`.
7. **CTA opposing drift** — two headlines with `useTransform(scrollYProgress, [0,1], [...])` in opposite directions.
8. **Underline-grow links** — `::after` pseudo-element scales width `0 → 100%` over `300ms`.
9. **Button hover** — `scale(1.03)` over `200ms`, arrow icon translates diagonally.

### Scroll Triggers
- Use `useInView` with `margin: "-20%"` so animations fire when the element is genuinely in view, not at the boundary.
- All scroll reveals are `once: true` — never replay on scroll-back.

---

## 7. Iconography & Imagery

- **Icons:** `lucide-react`, stroke width `1.5`, size `16–20px`. Only used inside buttons and the dismiss control. No decorative icons in content.
- **Imagery:** Avoid photography. Use generated SVG arcs, dashed curves, and oversized typography AS the visual. If product screenshots are needed, place them in sharp-cornered framed blocks with a `1px` border and the `--muted` background behind.
- **Decorative SVGs:** thin `1px` stroke, `currentColor`, dashed pattern `4 8`, opacity `0.15 – 0.30`.

---

## 8. Spacing Tokens

Use these increments only: `4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 160, 192` px.
Section gaps: `128px` minimum. Element gaps inside a section: `48–64px`. Inline gaps: `12–16px`.

---

## 9. Accessibility & Polish

- Maintain `WCAG AA` contrast — `#0E0E0C` on `#F4F1EA` passes at all sizes.
- Focus rings: `2px` solid `--accent`, offset `2px`.
- Respect `prefers-reduced-motion`: disable parallax and marquee, keep fade-ins under `0.3s`.
- All interactive pills have a min hit area of `44 × 44px`.

---

## 10. What "Done" Looks Like

The page should feel like a printed editorial spread that happens to move: enormous, calm typography, generous negative space, one warm accent, and motion that rewards scrolling without ever feeling busy. If the result reads as "another SaaS template," the brief was not followed.
