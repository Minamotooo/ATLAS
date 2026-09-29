/** @type {import('tailwindcss').Config} */
/*
 * Design tokens. The raw values live here (so Tailwind's opacity modifiers such
 * as bg-atlas-50/50 keep working) and are mirrored as CSS custom properties in
 * src/index.css for hand-written CSS and the WebGL scene.
 *
 * Palette brief: a light theme that survives a low-quality projector. Every text
 * colour below clears WCAG AA on white and on `paper`; accents are saturated so
 * they don't wash out, and the grey scale is warmer and one step darker than
 * Tailwind's default, which lifts contrast on every existing page at once.
 */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Brand violet. 600+ are text-safe on white (>= 6:1).
        atlas: {
          50: '#F4F1FF',
          100: '#E9E4FF',
          200: '#D2C9FF',
          300: '#B1A3FF',
          400: '#8C78FF',
          500: '#6C4DFF',
          600: '#5533F0',
          700: '#4424CC',
          800: '#35209E',
          900: '#221463',
        },
        ink: {
          DEFAULT: '#17132E',
          soft: '#3A355A',
          muted: '#58537A',
        },
        paper: {
          DEFAULT: '#FBF8F3',
          deep: '#F3EDE3',
        },
        gold: {
          100: '#FFF1C7',
          200: '#FFE08A',
          300: '#FFD15C',
          400: '#FFC233',
          500: '#F5A800',
          600: '#B87D00',
        },
        coral: {
          50: '#FFF1EC',
          100: '#FFE0D6',
          200: '#FFC0AD',
          300: '#FF9A7F',
          400: '#FF7A5C',
          500: '#FF5A36',
          600: '#D93A18',
        },
        mint: {
          50: '#E8FBF4',
          100: '#C8F4E4',
          200: '#93E8CA',
          300: '#56D6AB',
          400: '#1FC99A',
          500: '#0EA57D',
          600: '#0A7F60',
        },
        // Legacy names still used by some pages; mapped onto the new palette.
        warm: {
          50: '#FFFAEB',
          100: '#FFF1C7',
          200: '#FFE08A',
          300: '#FFD15C',
          400: '#FFC233',
          500: '#F5A800',
        },
        plum: {
          50: '#FDF4FF',
          100: '#FAE8FF',
          200: '#F5D0FE',
          300: '#E879F9',
          400: '#C026D3',
          500: '#A21CAF',
        },
        // Warm neutral, a step darker than Tailwind's gray for projector contrast.
        gray: {
          50: '#FAF8F5',
          100: '#F2EFEA',
          200: '#E4E0D8',
          300: '#CBC6BD',
          400: '#8C8698',
          500: '#645F74',
          600: '#4B465C',
          700: '#37334A',
          800: '#252136',
          900: '#17132E',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '"Noto Sans Bengali"', 'system-ui', 'sans-serif'],
        display: ['Fraunces', '"Noto Serif Bengali"', 'Georgia', 'serif'],
      },
      fontSize: {
        // Fluid display sizes; body sizes come from Tailwind defaults.
        'display-sm': ['clamp(1.75rem, 1.2rem + 1.8vw, 2.5rem)', { lineHeight: '1.08', letterSpacing: '-0.025em' }],
        'display-md': ['clamp(2.25rem, 1.4rem + 3vw, 3.75rem)', { lineHeight: '1.02', letterSpacing: '-0.035em' }],
        'display-lg': ['clamp(2.75rem, 1.2rem + 5.5vw, 6rem)', { lineHeight: '0.98', letterSpacing: '-0.045em' }],
        'display-xl': ['clamp(3.25rem, 1rem + 7.5vw, 8rem)', { lineHeight: '0.92', letterSpacing: '-0.05em' }],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(23,19,46,0.06), 0 8px 24px -8px rgba(23,19,46,0.12)',
        lift: '0 2px 4px rgba(23,19,46,0.06), 0 24px 48px -16px rgba(23,19,46,0.22)',
        glow: '0 0 0 1px rgba(85,51,240,0.18), 0 12px 40px -10px rgba(85,51,240,0.45)',
        gold: '0 12px 32px -10px rgba(245,168,0,0.6)',
      },
      transitionTimingFunction: {
        'out-expo': 'cubic-bezier(0.16, 1, 0.3, 1)',
        spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        'in-out-quart': 'cubic-bezier(0.76, 0, 0.24, 1)',
      },
      transitionDuration: {
        fast: '180ms',
        base: '420ms',
        slow: '900ms',
      },
    },
  },
  plugins: [],
};
