/*
 * Word-by-word mask reveal for headings.
 *
 * Splits by WORD, never by character: Bangla conjuncts (যুক্তাক্ষর) are built
 * from several code points and break visibly if split. Intl.Segmenter handles
 * both scripts; a whitespace split is the fallback.
 *
 * Screen readers get the full text through aria-label; the animated spans are
 * aria-hidden. With reduced motion the text simply appears.
 *
 * parts: [{ text, className }] lets one heading mix styles (a gradient word).
 * trigger: 'load' animates on mount, 'scroll' when the heading enters view.
 */
import { useMemo, useRef } from 'react';
import { gsap, ScrollTrigger, useGSAP } from './gsap';
import { DUR, EASE, STAGGER } from './tokens';
import useReducedMotion from './useReducedMotion';

function splitWords(text) {
  if (typeof Intl !== 'undefined' && Intl.Segmenter) {
    const seg = new Intl.Segmenter(undefined, { granularity: 'word' });
    const out = [];
    let buffer = '';
    for (const { segment } of seg.segment(text)) {
      if (/^\s+$/.test(segment)) {
        if (buffer) out.push(buffer);
        buffer = '';
        out.push(' ');
      } else {
        buffer += segment; // keep punctuation glued to its word
      }
    }
    if (buffer) out.push(buffer);
    return out;
  }
  return text.split(/(\s+)/).map((w) => (/^\s+$/.test(w) ? ' ' : w)).filter(Boolean);
}

export default function SplitText({
  as: Tag = 'h2',
  id,
  text,
  parts,
  className = '',
  trigger = 'scroll',
  delay = 0,
  stagger = STAGGER.base,
}) {
  const ref = useRef(null);
  const reduced = useReducedMotion();
  const segments = useMemo(() => parts || [{ text, className: '' }], [parts, text]);
  const label = segments.map((s) => s.text).join('');

  useGSAP(
    () => {
      if (reduced) return;
      const words = ref.current.querySelectorAll('[data-word]');
      gsap.set(words, { yPercent: 115, rotate: 4, opacity: 0 });
      const animate = () =>
        gsap.to(words, {
          yPercent: 0,
          rotate: 0,
          opacity: 1,
          duration: DUR.hero,
          ease: EASE.out,
          stagger,
          delay,
        });
      if (trigger === 'load') animate();
      else ScrollTrigger.create({ trigger: ref.current, start: 'top 85%', once: true, onEnter: animate });
    },
    { scope: ref, dependencies: [label, reduced] },
  );

  return (
    <Tag ref={ref} id={id} className={className} aria-label={label}>
      {segments.map((seg, si) =>
        splitWords(seg.text).map((word, wi) =>
          word === ' ' ? (
            <span key={`${si}-${wi}`} aria-hidden="true"> </span>
          ) : (
            <span
              key={`${si}-${wi}`}
              aria-hidden="true"
              className="inline-block overflow-hidden align-bottom"
              // the mask needs room above and below for ascenders, descenders and italic overhang
              style={{ paddingBlock: '0.14em', marginBlock: '-0.14em', paddingInline: '0.04em', marginInline: '-0.04em' }}
            >
              <span data-word className={`inline-block will-change-transform ${seg.className || ''}`}>
                {word}
              </span>
            </span>
          ),
        ),
      )}
    </Tag>
  );
}
