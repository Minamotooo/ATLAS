/*
 * Client for GET /users/{id}/progress: one request for a learner's mastery
 * across the whole catalogue. The navbar and the courses page both need it on
 * the same navigation, so results are shared for a few seconds.
 */
import { buildApiUrl } from '../context/AuthContext';

const TTL_MS = 8000;
const cache = new Map(); // userId -> { at, promise }

export function fetchProgress(userId, { fresh = false } = {}) {
  if (!userId) return Promise.resolve(null);
  const hit = cache.get(userId);
  if (!fresh && hit && Date.now() - hit.at < TTL_MS) return hit.promise;

  const promise = fetch(buildApiUrl(`/users/${encodeURIComponent(userId)}/progress`)).then((res) => {
    if (!res.ok) throw new Error(`Progress request failed (${res.status})`);
    return res.json();
  });
  cache.set(userId, { at: Date.now(), promise });
  promise.catch(() => cache.delete(userId));
  return promise;
}

export function fetchPublicStats() {
  return fetch(buildApiUrl('/stats/public')).then((res) => {
    if (!res.ok) throw new Error(`Stats request failed (${res.status})`);
    return res.json();
  });
}
