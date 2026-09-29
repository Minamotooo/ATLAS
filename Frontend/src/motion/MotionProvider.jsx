/*
 * App-wide motion runtime.
 *
 *  - Lenis smooth scrolling, driven by GSAP's ticker and synced to ScrollTrigger.
 *    Any scrollable panel (overflow-auto) and anything marked data-lenis-prevent
 *    or data-native-cursor (the Cytoscape graphs) keeps native scrolling, so
 *    wheel-zoom on the mastery map still works.
 *  - In-page anchor links (#workflow) scroll smoothly.
 *  - Route changes jump to the top and refresh ScrollTrigger measurements.
 *  - Magnetic elements: anything with data-magnetic follows the pointer a little.
 *    It animates the CSS `translate` property, so it never fights the
 *    transform-based press animation on .btn.
 *  - Spotlight: .card-hover receives --mx/--my for its cursor-following glow.
 *
 * Everything motion-related switches off under prefers-reduced-motion, and the
 * pointer effects only run for a fine (mouse) pointer.
 */
import { createContext, useContext, useEffect, useMemo, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import Lenis from 'lenis';
import { gsap, ScrollTrigger } from './gsap';
import useReducedMotion from './useReducedMotion';

const MotionContext = createContext({ lenis: null, reduced: false });

export function useMotion() {
  return useContext(MotionContext);
}

const finePointer = () =>
  typeof window !== 'undefined' && window.matchMedia('(pointer: fine)').matches;

export default function MotionProvider({ children }) {
  const reduced = useReducedMotion();
  const lenisRef = useRef(null);
  const location = useLocation();

  // ---- smooth scroll -------------------------------------------------------
  useEffect(() => {
    if (reduced) return undefined;

    const lenis = new Lenis({
      duration: 1.1,
      easing: (t) => 1 - Math.pow(1 - t, 4),
      smoothWheel: true,
      // Nested scrollers and the graph canvases keep native wheel behaviour.
      prevent: (node) =>
        !!node?.closest?.(
          '[data-lenis-prevent], [data-native-cursor], .overflow-auto, .overflow-y-auto, .overflow-x-auto',
        ),
    });
    lenisRef.current = lenis;
    lenis.on('scroll', ScrollTrigger.update);

    const tick = (time) => lenis.raf(time * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);

    return () => {
      gsap.ticker.remove(tick);
      lenis.destroy();
      lenisRef.current = null;
    };
  }, [reduced]);

  // ---- anchor links ---------------------------------------------------------
  useEffect(() => {
    const onClick = (event) => {
      const link = event.target.closest?.('a[href^="#"]');
      if (!link) return;
      const id = link.getAttribute('href');
      if (!id || id === '#') return;
      const target = document.querySelector(id);
      if (!target) return;
      event.preventDefault();
      if (lenisRef.current) {
        lenisRef.current.scrollTo(target, { offset: -88 });
      } else {
        target.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
      }
      target.setAttribute('tabindex', '-1');
      target.focus({ preventScroll: true });
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, [reduced]);

  // ---- route change: back to top, re-measure triggers -------------------------
  useEffect(() => {
    if (lenisRef.current) lenisRef.current.scrollTo(0, { immediate: true });
    else window.scrollTo(0, 0);
    const id = window.requestAnimationFrame(() => ScrollTrigger.refresh());
    return () => window.cancelAnimationFrame(id);
  }, [location.pathname]);

  // ---- magnetic elements + card spotlight (fine pointer only) -----------------
  useEffect(() => {
    if (reduced || !finePointer()) return undefined;

    const state = new WeakMap();
    let current = null;

    const moveTo = (el, x, y, duration, ease) => {
      let s = state.get(el);
      if (!s) {
        s = { x: 0, y: 0 };
        state.set(el, s);
      }
      gsap.to(s, {
        x,
        y,
        duration,
        ease,
        overwrite: true,
        onUpdate: () => {
          el.style.translate = `${s.x.toFixed(2)}px ${s.y.toFixed(2)}px`;
        },
      });
    };

    const release = (el) => moveTo(el, 0, 0, 0.9, 'elastic.out(1, 0.4)');

    const onMove = (event) => {
      const target = event.target;

      const card = target.closest?.('.card-hover');
      if (card) {
        const r = card.getBoundingClientRect();
        card.style.setProperty('--mx', `${event.clientX - r.left}px`);
        card.style.setProperty('--my', `${event.clientY - r.top}px`);
      }

      const mag = target.closest?.('[data-magnetic]');
      if (current && current !== mag) {
        release(current);
        current = null;
      }
      if (!mag || mag.disabled) return;
      current = mag;
      const r = mag.getBoundingClientRect();
      const strength = parseFloat(mag.dataset.magnetic) || 0.3;
      const dx = event.clientX - (r.left + r.width / 2);
      const dy = event.clientY - (r.top + r.height / 2);
      moveTo(mag, dx * strength, dy * strength, 0.5, 'power3.out');
    };

    const onLeaveWindow = () => {
      if (current) release(current);
      current = null;
    };

    window.addEventListener('pointermove', onMove, { passive: true });
    document.documentElement.addEventListener('pointerleave', onLeaveWindow);
    return () => {
      window.removeEventListener('pointermove', onMove);
      document.documentElement.removeEventListener('pointerleave', onLeaveWindow);
    };
  }, [reduced]);

  const value = useMemo(() => ({ get lenis() { return lenisRef.current; }, reduced }), [reduced]);
  return <MotionContext.Provider value={value}>{children}</MotionContext.Provider>;
}
