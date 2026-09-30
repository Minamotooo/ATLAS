/*
 * Motion tokens: the single source of timing for GSAP. The CSS mirror is the
 * --ease-* and --dur-* custom properties in src/index.css; keep them in step.
 *
 * Rules of the system:
 *  - entrances use EASE.out (expo): fast start, long soft landing
 *  - things that cover and uncover (curtains, drawers) use EASE.inOut
 *  - presses and small pops use EASE.spring (a little overshoot = playful)
 *  - only transform and opacity are animated
 */
export const EASE = {
  out: 'expo.out',
  outSoft: 'power3.out',
  inOut: 'power4.inOut',
  spring: 'back.out(1.6)',
};

export const DUR = {
  fast: 0.18,
  base: 0.42,
  slow: 0.9,
  hero: 1.35,
};

export const STAGGER = {
  tight: 0.04,
  base: 0.08,
  loose: 0.14,
};

/* Distance an element travels on reveal, in px. */
export const REVEAL_Y = 36;
