/*
 * Reusable WebGL layer built on React Three Fiber.
 *
 *  - devicePixelRatio capped at 2
 *  - renders only while on screen (IntersectionObserver) and while the tab is
 *    visible; otherwise the frame loop is switched off entirely
 *  - under reduced motion it renders on demand only (a still image)
 *  - pointer-events are off: the page above it stays fully interactive
 *  - resize is handled by R3F (ResizeObserver on the wrapper)
 */
import { useEffect, useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';

export default function SceneCanvas({ children, className = '', camera, reduced = false }) {
  const wrapRef = useRef(null);
  const [onScreen, setOnScreen] = useState(true);
  const [tabVisible, setTabVisible] = useState(() => !document.hidden);

  useEffect(() => {
    const io = new IntersectionObserver(([entry]) => setOnScreen(entry.isIntersecting), {
      rootMargin: '120px',
    });
    if (wrapRef.current) io.observe(wrapRef.current);
    const onVis = () => setTabVisible(!document.hidden);
    document.addEventListener('visibilitychange', onVis);
    return () => {
      io.disconnect();
      document.removeEventListener('visibilitychange', onVis);
    };
  }, []);

  const frameloop = reduced ? 'demand' : onScreen && tabVisible ? 'always' : 'never';

  return (
    <div ref={wrapRef} className={className} aria-hidden="true">
      <Canvas
        dpr={[1, 2]}
        frameloop={frameloop}
        camera={camera}
        gl={{ antialias: true, alpha: false, powerPreference: 'high-performance', stencil: false }}
        style={{ pointerEvents: 'none' }}
      >
        {children}
      </Canvas>
    </div>
  );
}
