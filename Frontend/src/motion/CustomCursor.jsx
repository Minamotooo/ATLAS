/*
 * Custom cursor: an ink dot that tracks the pointer exactly and a ring that
 * trails it. Over anything interactive the ring swells; an element can show a
 * short label in the ring with data-cursor="Open". Form fields, canvases and
 * data-native-cursor zones (the Cytoscape graphs) get the native cursor back
 * and the custom one fades out, so precise work never fights an effect.
 *
 * Only mounted for a fine pointer with motion allowed; it is aria-hidden and
 * purely decorative.
 */
import { useEffect, useRef, useState } from 'react';
import { gsap } from './gsap';
import useReducedMotion from './useReducedMotion';

const INTERACTIVE = 'a, button, [role="button"], label, summary, [data-cursor], [data-magnetic]';
const NATIVE = 'input, textarea, select, [contenteditable="true"], canvas, [data-native-cursor]';

export default function CustomCursor() {
  const reduced = useReducedMotion();
  const [enabled, setEnabled] = useState(false);
  const dotRef = useRef(null);
  const ringRef = useRef(null);
  const labelRef = useRef(null);

  useEffect(() => {
    const fine = window.matchMedia('(pointer: fine)');
    const update = () => setEnabled(fine.matches && !reduced);
    update();
    fine.addEventListener('change', update);
    return () => fine.removeEventListener('change', update);
  }, [reduced]);

  useEffect(() => {
    if (!enabled) return undefined;
    const root = document.documentElement;
    root.classList.add('has-cursor');

    const dot = dotRef.current;
    const ring = ringRef.current;
    const label = labelRef.current;
    gsap.set([dot, ring], { xPercent: -50, yPercent: -50, opacity: 0 });

    const dotX = gsap.quickTo(dot, 'x', { duration: 0.08, ease: 'power3.out' });
    const dotY = gsap.quickTo(dot, 'y', { duration: 0.08, ease: 'power3.out' });
    const ringX = gsap.quickTo(ring, 'x', { duration: 0.45, ease: 'power3.out' });
    const ringY = gsap.quickTo(ring, 'y', { duration: 0.45, ease: 'power3.out' });

    let mode = '';
    const setMode = (next, text = '') => {
      if (next === mode && text === label.textContent) return;
      mode = next;
      label.textContent = text;
      const hidden = next === 'native';
      gsap.to(dot, { opacity: hidden ? 0 : 1, scale: next === 'hover' ? 0.4 : 1, duration: 0.25 });
      gsap.to(ring, {
        opacity: hidden ? 0 : 1,
        scale: next === 'hover' ? (text ? 2.4 : 1.7) : 1,
        backgroundColor: next === 'hover' ? 'rgba(255, 209, 92, 0.35)' : 'rgba(255, 209, 92, 0)',
        duration: 0.35,
        ease: 'expo.out',
      });
      gsap.to(label, { opacity: text ? 1 : 0, duration: 0.2 });
    };

    const onMove = (event) => {
      dotX(event.clientX);
      dotY(event.clientY);
      ringX(event.clientX);
      ringY(event.clientY);
      const target = event.target;
      if (target.closest?.(NATIVE)) {
        setMode('native');
        return;
      }
      const hit = target.closest?.(INTERACTIVE);
      if (hit) setMode('hover', hit.getAttribute('data-cursor') || '');
      else setMode('idle');
    };
    const onDown = () => gsap.to(ring, { scale: 0.8, duration: 0.15 });
    const onUp = () => gsap.to(ring, { scale: mode === 'hover' ? 1.7 : 1, duration: 0.4, ease: 'back.out(2)' });
    const onLeave = () => gsap.to([dot, ring], { opacity: 0, duration: 0.2 });

    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerdown', onDown);
    window.addEventListener('pointerup', onUp);
    root.addEventListener('pointerleave', onLeave);
    return () => {
      root.classList.remove('has-cursor');
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerdown', onDown);
      window.removeEventListener('pointerup', onUp);
      root.removeEventListener('pointerleave', onLeave);
    };
  }, [enabled]);

  if (!enabled) return null;
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-[100]">
      <div
        ref={ringRef}
        className="fixed left-0 top-0 flex h-10 w-10 items-center justify-center rounded-full border-2 border-ink/80"
      >
        <span ref={labelRef} className="text-[5px] font-bold uppercase tracking-widest text-ink opacity-0" />
      </div>
      <div ref={dotRef} className="fixed left-0 top-0 h-2 w-2 rounded-full bg-ink" />
    </div>
  );
}
