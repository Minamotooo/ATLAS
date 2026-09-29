/*
 * Decide whether to load the WebGL scene at all. Phones, low-core or
 * low-memory devices, data-saver mode and machines without WebGL get the
 * static fallback instead, and never download the Three.js chunk.
 */
export function canRunScene() {
  if (typeof window === 'undefined') return false;
  if (window.matchMedia('(max-width: 767px)').matches) return false;
  const nav = window.navigator || {};
  if (nav.connection && nav.connection.saveData) return false;
  if ((nav.hardwareConcurrency || 8) < 4) return false;
  if (nav.deviceMemory && nav.deviceMemory < 4) return false;

  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    if (!gl) return false;
    // free the probe context right away
    gl.getExtension('WEBGL_lose_context')?.loseContext();
    return true;
  } catch {
    return false;
  }
}
