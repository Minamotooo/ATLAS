/*
 * GLSL for the knowledge globe. Three programs:
 *
 *  POINTS  one sprite per skill. Morphs sphere -> subject map (uMorph), parts
 *          around the cursor (uMouse, in NDC), twinkles, and emphasises the
 *          focused subject (uFocusW / uFocusAmt).
 *  LINES   the constellation web between neighbouring skills, driven by the
 *          same morph and repel so it stays attached to its points.
 *  BACKDROP a full-screen mesh gradient: three soft colour fields drifting over
 *          warm ivory, nudged by the pointer and by scroll progress.
 *
 * Colours arrive as uniforms/attributes in linear 0..1 RGB.
 */

// Shared: morph + cursor repulsion, in view space so the push is screen-sized.
const MORPH_AND_REPEL = /* glsl */ `
  uniform float uTime;
  uniform float uMorph;
  uniform float uIntro;
  uniform vec2  uMouse;
  uniform float uAspect;
  uniform float uRepel;

  attribute vec3  aPlane;
  attribute float aSeed;
  attribute float aSubject;

  vec4 morphedViewPosition(out float push) {
    float m = smoothstep(0.0, 1.0, uMorph);
    // breathing sphere: every point drifts a little on its own phase
    vec3 sphere = position * (1.0 + 0.035 * sin(uTime * 0.7 + aSeed * 6.2831));
    vec3 plane = aPlane + vec3(0.0, 0.0, 0.04 * sin(uTime * 0.9 + aSeed * 12.0));
    vec3 p = mix(sphere, plane, m);
    // intro: points condense from a wide cloud
    p *= mix(2.6 + aSeed, 1.0, uIntro);

    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    vec4 clip = projectionMatrix * mv;
    vec2 ndc = clip.xy / clip.w;
    vec2 d = ndc - uMouse;
    d.x *= uAspect;
    float dist = length(d);
    push = smoothstep(0.32, 0.0, dist) * uRepel;
    mv.xy += normalize(d + vec2(1e-5)) * push * 0.42;
    return mv;
  }
`;

export const pointsVertex = /* glsl */ `
  ${MORPH_AND_REPEL}
  uniform float uSize;
  uniform float uPixelRatio;
  uniform vec3  uFocusW;
  uniform float uFocusAmt;
  attribute vec3 aColor;
  varying vec3  vColor;
  varying float vAlpha;

  void main() {
    float push;
    vec4 mv = morphedViewPosition(push);
    gl_Position = projectionMatrix * mv;

    float w = aSubject < 0.5 ? uFocusW.x : (aSubject < 1.5 ? uFocusW.y : uFocusW.z);
    float emph = mix(1.0, mix(0.45, 1.7, w), uFocusAmt);
    float twinkle = 0.8 + 0.2 * sin(uTime * 2.1 + aSeed * 43.0);

    gl_PointSize = uSize * uPixelRatio * emph * twinkle * (1.0 + push * 0.9) / -mv.z;
    vColor = aColor;
    vAlpha = mix(1.0, mix(0.22, 1.0, w), uFocusAmt) * uIntro;
  }
`;

export const pointsFragment = /* glsl */ `
  varying vec3  vColor;
  varying float vAlpha;

  void main() {
    vec2 uv = gl_PointCoord - 0.5;
    float r = length(uv);
    if (r > 0.5) discard;
    // solid core with a bright top-left highlight: reads as a glossy bead,
    // which survives a washed-out projector far better than a glow would
    float core = smoothstep(0.5, 0.36, r);
    float shine = smoothstep(0.22, 0.0, length(uv - vec2(-0.14, 0.14)));
    vec3 col = mix(vColor, vec3(1.0), shine * 0.55);
    gl_FragColor = vec4(col, core * vAlpha);
  }
`;

export const linesVertex = /* glsl */ `
  ${MORPH_AND_REPEL}
  attribute vec3 aColor;
  varying vec3  vColor;
  varying float vAlpha;

  void main() {
    float push;
    vec4 mv = morphedViewPosition(push);
    gl_Position = projectionMatrix * mv;
    vColor = aColor;
    // the web is the globe's structure; it thins out as the map unfolds
    vAlpha = (0.34 - 0.24 * smoothstep(0.0, 1.0, uMorph)) * uIntro;
  }
`;

export const linesFragment = /* glsl */ `
  varying vec3  vColor;
  varying float vAlpha;
  void main() { gl_FragColor = vec4(vColor, vAlpha); }
`;

export const backdropVertex = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.999, 1.0);
  }
`;

export const backdropFragment = /* glsl */ `
  uniform float uTime;
  uniform vec2  uMouse;
  uniform float uProgress;
  uniform float uAspect;
  uniform vec3  uBase;
  uniform vec3  uC1;
  uniform vec3  uC2;
  uniform vec3  uC3;
  varying vec2 vUv;

  // soft circular field
  float field(vec2 uv, vec2 c, float r) {
    return exp(-dot(uv - c, uv - c) / (r * r));
  }

  void main() {
    vec2 uv = vUv;
    uv.x *= uAspect;
    float t = uTime * 0.06;
    vec2 m = uMouse * 0.06;

    vec2 c1 = vec2(0.25 * uAspect + 0.12 * sin(t * 1.3), 0.78 + 0.08 * cos(t * 1.1)) + m;
    vec2 c2 = vec2(0.82 * uAspect + 0.10 * cos(t), 0.30 + 0.10 * sin(t * 1.7)) - m;
    vec2 c3 = vec2(0.55 * uAspect + 0.16 * sin(t * 0.8 + 2.0), 0.08 + 0.35 * uProgress) + m * 0.5;

    vec3 col = uBase;
    col = mix(col, uC1, field(uv, c1, 0.42) * 0.30);
    col = mix(col, uC2, field(uv, c2, 0.38) * 0.26);
    col = mix(col, uC3, field(uv, c3, 0.46) * 0.30);
    // gentle vignette toward paper-deep so the edge of the canvas never shows
    col = mix(col, uBase * 0.97, smoothstep(0.55, 1.05, length(vUv - 0.5) * 1.4));
    gl_FragColor = vec4(col, 1.0);
  }
`;
