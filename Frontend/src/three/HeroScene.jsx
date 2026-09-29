/*
 * The landing page's WebGL scene. Loaded lazily (React.lazy) so three.js and
 * R3F live in their own chunk and never block first paint.
 */
import { useEffect } from 'react';
import SceneCanvas from './SceneCanvas';
import KnowledgeGlobe from './KnowledgeGlobe';
import { sceneState } from './sceneStore';

export default function HeroScene({ className = '', counts, reduced = false }) {
  // The canvas ignores pointer events (content sits on top), so read the
  // pointer from the window and convert to normalised device coordinates.
  useEffect(() => {
    if (reduced) return undefined;
    const onMove = (e) => {
      sceneState.pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
      sceneState.pointer.y = -(e.clientY / window.innerHeight) * 2 + 1;
    };
    const onLeave = () => {
      sceneState.pointer.x = 9; // far away: no repulsion
      sceneState.pointer.y = 9;
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    document.documentElement.addEventListener('pointerleave', onLeave);
    return () => {
      window.removeEventListener('pointermove', onMove);
      document.documentElement.removeEventListener('pointerleave', onLeave);
    };
  }, [reduced]);

  return (
    <SceneCanvas className={className} reduced={reduced} camera={{ position: [0, 0, 6.2], fov: 42, near: 0.1, far: 50 }}>
      <KnowledgeGlobe counts={counts} reduced={reduced} />
    </SceneCanvas>
  );
}
