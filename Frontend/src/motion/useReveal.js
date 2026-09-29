/*
 * Scroll-triggered reveals for anything inside `scopeRef` marked data-reveal.
 *
 *   <div data-reveal>…</div>                rises and fades in
 *   <div data-reveal="scale">…</div>        grows from 94% instead
 *   <div data-reveal="fade">…</div>         opacity only
 *
 * Elements entering together are staggered (ScrollTrigger.batch). Pass the
 * values that change what is rendered (e.g. a loading flag) as `deps`, so
 * content that arrives later is picked up; already-revealed nodes are skipped.
 */
import { gsap, ScrollTrigger, useGSAP } from './gsap';
import { DUR, EASE, REVEAL_Y, STAGGER } from './tokens';
import { prefersReducedMotion } from './useReducedMotion';

export default function useReveal(scopeRef, deps = []) {
  useGSAP(
    () => {
      if (!scopeRef.current || prefersReducedMotion()) return;
      const nodes = gsap.utils
        .toArray(scopeRef.current.querySelectorAll('[data-reveal]'))
        .filter((n) => !n.dataset.revealed);
      if (!nodes.length) return;

      nodes.forEach((n) => {
        const kind = n.dataset.reveal;
        gsap.set(n, {
          opacity: 0,
          y: kind === 'fade' || kind === 'scale' ? 0 : REVEAL_Y,
          scale: kind === 'scale' ? 0.94 : 1,
        });
      });

      ScrollTrigger.batch(nodes, {
        start: 'top 88%',
        once: true,
        onEnter: (batch) => {
          batch.forEach((n) => {
            n.dataset.revealed = '1';
          });
          gsap.to(batch, {
            opacity: 1,
            y: 0,
            scale: 1,
            duration: DUR.slow,
            ease: EASE.out,
            stagger: STAGGER.base,
            clearProps: 'transform',
          });
        },
      });
    },
    { scope: scopeRef, dependencies: deps },
  );
}
