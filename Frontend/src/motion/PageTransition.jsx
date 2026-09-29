/*
 * Route transitions. On every navigation a violet-and-gold curtain covers the
 * viewport before the new page paints (useLayoutEffect), then sweeps up and off
 * while the page itself rises into place. The very first load of the site
 * plays a short brand intro instead. Under reduced motion both are skipped.
 *
 * Enter-only by design: the outgoing page is never held in the DOM, so routes
 * and their data logic behave exactly as before.
 */
import { useLayoutEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { gsap } from './gsap';
import { DUR, EASE } from './tokens';
import useReducedMotion from './useReducedMotion';

let introPlayed = false;

/**
 * Seconds until a freshly mounted page is uncovered, for pages that time their
 * own entrance to land just as the curtain lifts. Child layout effects run
 * before this component's, so on the very first load introPlayed is still false.
 */
export function enterDelay() {
  if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return 0;
  return introPlayed ? 0.45 : 1.35;
}

export default function PageTransition({ children }) {
  const location = useLocation();
  const reduced = useReducedMotion();
  const curtainRef = useRef(null);
  const accentRef = useRef(null);
  const brandRef = useRef(null);
  const contentRef = useRef(null);
  const firstRender = useRef(true);

  useLayoutEffect(() => {
    const curtain = curtainRef.current;
    const accent = accentRef.current;
    const brand = brandRef.current;
    const content = contentRef.current;
    const isFirst = firstRender.current;
    firstRender.current = false;

    if (reduced) {
      gsap.set([curtain, accent], { yPercent: -100 });
      gsap.set(content, { clearProps: 'all' });
      return undefined;
    }

    const playIntro = isFirst && !introPlayed;
    if (isFirst && !playIntro) {
      gsap.set([curtain, accent], { yPercent: -100 });
      return undefined;
    }
    introPlayed = true;

    const tl = gsap.timeline({ defaults: { ease: EASE.inOut } });
    tl.set([curtain, accent], { yPercent: 0 })
      .set(content, { opacity: 0, y: 28 });

    if (playIntro) {
      tl.fromTo(brand, { opacity: 0, yPercent: 60 }, { opacity: 1, yPercent: 0, duration: 0.6, ease: EASE.out })
        .to(brand, { opacity: 0, yPercent: -40, duration: 0.35, ease: 'power2.in' }, '+=0.25');
    } else {
      tl.set(brand, { opacity: 0 });
    }

    tl.to(curtain, { yPercent: -100, duration: DUR.slow })
      .to(accent, { yPercent: -100, duration: DUR.slow }, '<0.08')
      .to(content, { opacity: 1, y: 0, duration: DUR.slow, ease: EASE.out, clearProps: 'transform,opacity' }, '<0.15');

    return () => tl.kill();
  }, [location.pathname, reduced]);

  return (
    <>
      <div
        ref={accentRef}
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 z-[90] bg-gradient-to-br from-gold-300 via-coral-400 to-atlas-500"
        style={{ transform: 'translateY(-100%)' }}
      />
      <div
        ref={curtainRef}
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 z-[91] flex items-center justify-center bg-ink"
        style={{ transform: 'translateY(-100%)' }}
      >
        <span ref={brandRef} className="font-display text-display-lg italic text-paper opacity-0">
          ATLAS<span className="text-gold-400">.</span>
        </span>
      </div>
      <div ref={contentRef}>{children}</div>
    </>
  );
}
