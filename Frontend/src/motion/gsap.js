/*
 * One place that registers GSAP plugins, so every module imports a ready gsap.
 */
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(ScrollTrigger, useGSAP);

// Transforms only; GSAP's default force3D:auto already promotes to the GPU.
gsap.defaults({ overwrite: 'auto' });

export { gsap, ScrollTrigger, useGSAP };
