/*
 * The knowledge globe: one point per skill in the ATLAS ontology.
 *
 * Geometry (built once):
 *  - sphere layout: a Fibonacci sphere, subjects interleaved like a world map
 *  - map layout: three sunflower discs, one per subject, sized by skill count
 *  - a constellation web joining each skill to its nearest same-subject
 *    neighbours on the sphere (a stand-in for prerequisite links)
 *
 * Per frame it eases towards the targets in sceneState: scroll progress drives
 * the sphere -> map morph, the story step drives which subject is lit, and the
 * pointer tilts the globe and parts the points around the cursor.
 */
import { useEffect, useMemo, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { sceneState, SUBJECTS } from './sceneStore';
import {
  backdropFragment,
  backdropVertex,
  linesFragment,
  linesVertex,
  pointsFragment,
  pointsVertex,
} from './shaders';

// Colours as raw sRGB triples: the shaders write them straight to the screen.
function hexToRgb(hex) {
  const n = parseInt(hex.replace('#', ''), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}

// Deterministic PRNG so the layout is identical on every visit.
function mulberry32(seed) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const GOLDEN = Math.PI * (3 - Math.sqrt(5));

function buildLayout(counts) {
  const total = counts.reduce((a, b) => a + b, 0);
  const rand = mulberry32(1688);

  // Interleave subjects across the sphere (a shuffled subject per slot).
  const subjectOf = [];
  counts.forEach((c, s) => {
    for (let i = 0; i < c; i += 1) subjectOf.push(s);
  });
  for (let i = subjectOf.length - 1; i > 0; i -= 1) {
    const j = Math.floor(rand() * (i + 1));
    [subjectOf[i], subjectOf[j]] = [subjectOf[j], subjectOf[i]];
  }

  const sphere = new Float32Array(total * 3);
  const plane = new Float32Array(total * 3);
  const color = new Float32Array(total * 3);
  const seed = new Float32Array(total);
  const subject = new Float32Array(total);

  const R = 1.75;
  // map discs: centres spread on x, radius ~ sqrt(count) so area ~ skill count
  const centres = [-2.35, 0.1, 2.45];
  const radii = counts.map((c) => 0.046 * Math.sqrt(c));
  const placedInSubject = [0, 0, 0];
  const palette = SUBJECTS.map((s) => hexToRgb(s.color));

  for (let i = 0; i < total; i += 1) {
    const y = 1 - (2 * (i + 0.5)) / total;
    const ring = Math.sqrt(1 - y * y);
    const theta = GOLDEN * i;
    const jitter = 1 + (rand() - 0.5) * 0.06;
    sphere.set([Math.cos(theta) * ring * R * jitter, y * R * jitter, Math.sin(theta) * ring * R * jitter], i * 3);

    const s = subjectOf[i];
    const k = placedInSubject[s];
    placedInSubject[s] += 1;
    const rr = radii[s] * Math.sqrt((k + 0.5) / counts[s]);
    const a = k * GOLDEN;
    plane.set([centres[s] + Math.cos(a) * rr, Math.sin(a) * rr * 0.92 - 0.1, 0], i * 3);

    color.set(palette[s], i * 3);
    seed[i] = rand();
    subject[i] = s;
  }

  // Constellation web: link each point to its 2 nearest same-subject neighbours.
  const pairs = [];
  for (let i = 0; i < total; i += 1) {
    let best = [Infinity, -1];
    let second = [Infinity, -1];
    for (let j = 0; j < total; j += 1) {
      if (j === i || subjectOf[j] !== subjectOf[i]) continue;
      const dx = sphere[i * 3] - sphere[j * 3];
      const dy = sphere[i * 3 + 1] - sphere[j * 3 + 1];
      const dz = sphere[i * 3 + 2] - sphere[j * 3 + 2];
      const d = dx * dx + dy * dy + dz * dz;
      if (d < best[0]) {
        second = best;
        best = [d, j];
      } else if (d < second[0]) {
        second = [d, j];
      }
    }
    if (best[1] > i) pairs.push([i, best[1]]);
    if (second[1] > i && rand() < 0.45) pairs.push([i, second[1]]);
  }

  const n = pairs.length * 2;
  const lSphere = new Float32Array(n * 3);
  const lPlane = new Float32Array(n * 3);
  const lColor = new Float32Array(n * 3);
  const lSeed = new Float32Array(n);
  const lSubject = new Float32Array(n);
  pairs.forEach(([a, b], p) => {
    [a, b].forEach((idx, e) => {
      const v = p * 2 + e;
      lSphere.set(sphere.subarray(idx * 3, idx * 3 + 3), v * 3);
      lPlane.set(plane.subarray(idx * 3, idx * 3 + 3), v * 3);
      lColor.set(color.subarray(idx * 3, idx * 3 + 3), v * 3);
      lSeed[v] = seed[idx];
      lSubject[v] = subject[idx];
    });
  });

  return {
    points: { sphere, plane, color, seed, subject },
    lines: { sphere: lSphere, plane: lPlane, color: lColor, seed: lSeed, subject: lSubject },
  };
}

function makeGeometry({ sphere, plane, color, seed, subject }) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(sphere, 3));
  g.setAttribute('aPlane', new THREE.BufferAttribute(plane, 3));
  g.setAttribute('aColor', new THREE.BufferAttribute(color, 3));
  g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1));
  g.setAttribute('aSubject', new THREE.BufferAttribute(subject, 1));
  g.computeBoundingSphere();
  return g;
}

const damp = THREE.MathUtils.damp;

export default function KnowledgeGlobe({ counts = [356, 886, 446], reduced = false }) {
  const group = useRef(null);
  const { size, viewport, invalidate } = useThree();

  const { pointsGeo, linesGeo, pointsMat, linesMat, backdropMat, backdropGeo } = useMemo(() => {
    const layout = buildLayout(counts);
    const shared = {
      uTime: { value: 0 },
      uMorph: { value: 0 },
      uIntro: { value: reduced ? 1 : 0 },
      uMouse: { value: new THREE.Vector2(9, 9) },
      uAspect: { value: 1 },
      uRepel: { value: reduced ? 0 : 1 },
    };
    const pointsMaterial = new THREE.ShaderMaterial({
      vertexShader: pointsVertex,
      fragmentShader: pointsFragment,
      uniforms: {
        ...shared,
        uSize: { value: 62 },
        uPixelRatio: { value: Math.min(window.devicePixelRatio || 1, 2) },
        uFocusW: { value: new THREE.Vector3(0, 0, 0) },
        uFocusAmt: { value: 0 },
      },
      transparent: true,
      depthWrite: false,
    });
    const linesMaterial = new THREE.ShaderMaterial({
      vertexShader: linesVertex,
      fragmentShader: linesFragment,
      uniforms: shared,
      transparent: true,
      depthWrite: false,
    });
    const backdropMaterial = new THREE.ShaderMaterial({
      vertexShader: backdropVertex,
      fragmentShader: backdropFragment,
      uniforms: {
        uTime: shared.uTime,
        uMouse: { value: new THREE.Vector2(0, 0) },
        uProgress: { value: 0 },
        uAspect: shared.uAspect,
        uBase: { value: new THREE.Vector3(...hexToRgb('#FBF8F3')) },
        uC1: { value: new THREE.Vector3(...hexToRgb('#B1A3FF')) },
        uC2: { value: new THREE.Vector3(...hexToRgb('#FFB39E')) },
        uC3: { value: new THREE.Vector3(...hexToRgb('#FFD15C')) },
      },
      depthTest: false,
      depthWrite: false,
    });
    return {
      pointsGeo: makeGeometry(layout.points),
      linesGeo: makeGeometry(layout.lines),
      pointsMat: pointsMaterial,
      linesMat: linesMaterial,
      backdropMat: backdropMaterial,
      backdropGeo: new THREE.PlaneGeometry(2, 2),
    };
    // counts is a stable literal; rebuilding on every render would be wasteful
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Explicit disposal: these objects are created outside JSX.
  useEffect(
    () => () => {
      [pointsGeo, linesGeo, backdropGeo].forEach((g) => g.dispose());
      [pointsMat, linesMat, backdropMat].forEach((m) => m.dispose());
    },
    [pointsGeo, linesGeo, backdropGeo, pointsMat, linesMat, backdropMat],
  );

  // Keep aspect-dependent uniforms right on resize; redraw if rendering on demand.
  useEffect(() => {
    pointsMat.uniforms.uAspect.value = size.width / Math.max(size.height, 1);
    pointsMat.uniforms.uPixelRatio.value = Math.min(window.devicePixelRatio || 1, 2);
    invalidate();
  }, [size, pointsMat, invalidate]);

  useFrame((state, delta) => {
    const dt = Math.min(delta, 1 / 20);
    const u = pointsMat.uniforms;
    u.uTime.value += dt;

    const targetMorph = THREE.MathUtils.smoothstep(sceneState.progress, 0.18, 0.55);
    u.uMorph.value = damp(u.uMorph.value, targetMorph, 3.2, dt);
    if (!reduced) u.uIntro.value = damp(u.uIntro.value, 1, 1.6, dt);

    // focus: ease each subject's weight toward the story step
    const f = sceneState.focus;
    const fw = u.uFocusW.value;
    fw.set(damp(fw.x, f === 0 ? 1 : 0, 5, dt), damp(fw.y, f === 1 ? 1 : 0, 5, dt), damp(fw.z, f === 2 ? 1 : 0, 5, dt));
    u.uFocusAmt.value = damp(u.uFocusAmt.value, f >= 0 ? 1 : 0, 5, dt);

    const raw = sceneState.pointer;
    u.uMouse.value.set(damp(u.uMouse.value.x, raw.x, 8, dt), damp(u.uMouse.value.y, raw.y, 8, dt));
    // (9, 9) means "no pointer": keep repulsion off but hold tilt and backdrop still
    const away = Math.abs(raw.x) > 1.5;
    const p = away ? { x: 0, y: 0 } : raw;
    backdropMat.uniforms.uMouse.value.set(p.x, p.y);
    backdropMat.uniforms.uProgress.value = sceneState.progress;

    const g = group.current;
    if (g) {
      const m = u.uMorph.value;
      // spin as a globe, settle flat (with a slight map tilt) as it unfolds
      g.rotation.y += dt * 0.09 * (1 - m);
      const flatY = Math.round(g.rotation.y / (Math.PI * 2)) * Math.PI * 2;
      g.rotation.y = THREE.MathUtils.lerp(g.rotation.y, flatY, m * 0.08);
      g.rotation.x = damp(g.rotation.x, p.y * -0.22 * (1 - m) - m * 0.28, 4, dt);
      g.rotation.z = damp(g.rotation.z, p.x * 0.08 * (1 - m), 4, dt);
      // sit to the right of the hero copy on wide screens, centred for the map
      const side = viewport.aspect > 1.2 ? 1.45 : 0;
      g.position.x = damp(g.position.x, side * (1 - m), 3, dt);
      g.scale.setScalar(damp(g.scale.x, viewport.aspect > 1.2 ? 1 : 0.8, 3, dt));
    }
  });

  return (
    <>
      <mesh geometry={backdropGeo} material={backdropMat} renderOrder={-1} frustumCulled={false} dispose={null} />
      <group ref={group}>
        <lineSegments geometry={linesGeo} material={linesMat} dispose={null} />
        <points geometry={pointsGeo} material={pointsMat} dispose={null} />
      </group>
    </>
  );
}
