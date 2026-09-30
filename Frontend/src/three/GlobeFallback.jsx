/*
 * Static stand-in for the WebGL globe on phones, low-end devices, data-saver
 * and machines without WebGL: an SVG projection of the same Fibonacci sphere,
 * in the same subject colours, over the same mesh-gradient backdrop. No
 * three.js is downloaded on these devices.
 *
 * focus (0..2) dims the other subjects, the same story beat the WebGL scene plays.
 */
import { useMemo } from 'react';
import { SUBJECTS } from './sceneStore';

const GOLDEN = Math.PI * (3 - Math.sqrt(5));

export default function GlobeFallback({ className = '', still = false, focus = -1 }) {
  const dots = useMemo(() => {
    const n = 320;
    const tilt = 0.35;
    const out = [];
    for (let i = 0; i < n; i += 1) {
      const y = 1 - (2 * (i + 0.5)) / n;
      const r = Math.sqrt(1 - y * y);
      const th = GOLDEN * i;
      const x = Math.cos(th) * r;
      const z = Math.sin(th) * r;
      // tilt around x so the globe reads as 3D
      const y2 = y * Math.cos(tilt) - z * Math.sin(tilt);
      const z2 = y * Math.sin(tilt) + z * Math.cos(tilt);
      out.push({ x: 50 + x * 42, y: 50 - y2 * 42, depth: (z2 + 1) / 2, s: (i * 7) % 3 });
    }
    return out.sort((a, b) => a.depth - b.depth);
  }, []);

  return (
    <div
      className={className}
      aria-hidden="true"
      style={{
        background:
          'radial-gradient(40% 50% at 20% 25%, rgba(177,163,255,0.35), transparent 70%),' +
          'radial-gradient(35% 45% at 85% 70%, rgba(255,179,158,0.35), transparent 70%),' +
          'radial-gradient(40% 40% at 60% 100%, rgba(255,209,92,0.35), transparent 70%), #FBF8F3',
      }}
    >
      {/* centring lives on the wrapper so the float keyframes (a transform) don't undo it */}
      <div className="absolute right-[4%] top-1/2 -translate-y-1/2 max-md:right-1/2 max-md:translate-x-1/2 max-md:opacity-30">
      <svg viewBox="0 0 100 100" className={`block aspect-square h-[min(78vh,38rem)] w-auto ${still ? '' : 'animate-float'}`}>
        {dots.map((d, i) => (
          <circle
            key={i}
            cx={d.x}
            cy={d.y}
            r={0.55 + d.depth * 0.75}
            fill={SUBJECTS[d.s].color}
            opacity={(0.25 + d.depth * 0.75) * (focus < 0 || focus === d.s ? 1 : 0.14)}
            style={{ transition: 'opacity var(--dur-slow) var(--ease-out)' }}
          />
        ))}
      </svg>
      </div>
    </div>
  );
}
