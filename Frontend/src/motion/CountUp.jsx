/*
 * Animates a number from 0 when it scrolls into view. The final value is in
 * the DOM from the first render (and in aria-label), so screen readers and
 * reduced-motion users always get the real figure.
 */
import { useRef } from 'react';
import { gsap, ScrollTrigger, useGSAP } from './gsap';
import useReducedMotion from './useReducedMotion';

export default function CountUp({ value, locale = 'en-US', decimals = 0, suffix = '', className = '' }) {
  const ref = useRef(null);
  const reduced = useReducedMotion();
  const format = (n) =>
    `${Number(n).toLocaleString(locale, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}${suffix}`;

  useGSAP(
    () => {
      if (reduced || value == null || Number.isNaN(Number(value))) return;
      const el = ref.current;
      const counter = { n: 0 };
      el.textContent = format(0);
      ScrollTrigger.create({
        trigger: el,
        start: 'top 90%',
        once: true,
        onEnter: () =>
          gsap.to(counter, {
            n: Number(value),
            duration: 1.6,
            ease: 'expo.out',
            onUpdate: () => {
              el.textContent = format(counter.n);
            },
          }),
      });
    },
    { dependencies: [value, reduced, locale] },
  );

  const shown = value == null ? '—' : format(value);
  // Keyed on the value: the tween writes textContent directly, so a new value
  // gets a fresh node instead of React patching one GSAP has already replaced.
  return (
    <span key={`${value}-${locale}`} ref={ref} className={`tabular-nums ${className}`} aria-label={shown}>
      {shown}
    </span>
  );
}
