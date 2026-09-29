/*
 * Shared, mutable scene input. DOM code (ScrollTrigger, pointer listeners)
 * writes here and the render loop reads it every frame, so scrolling never
 * causes a React re-render.
 *
 *  progress  0..1 through the landing page's hero + story
 *  focus     -1 for none, else subject index 0 Physics, 1 Chemistry, 2 Mathematics
 *  pointer   pointer position in normalised device coordinates (-1..1)
 */
export const sceneState = {
  progress: 0,
  focus: -1,
  pointer: { x: 9, y: 9 }, // off-screen until the pointer first moves
};

export const SUBJECTS = [
  { key: 'Physics', color: '#FF5A36' },
  { key: 'Chemistry', color: '#5533F0' },
  { key: 'Mathematics', color: '#E39A00' },
];
