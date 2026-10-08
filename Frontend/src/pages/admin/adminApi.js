import { authFetch, buildApiUrl } from '../../context/AuthContext';

// Shared by every admin page: sends the session token, which the backend's
// require_admin dependency checks against ADMIN_USERNAMES. The backend is the
// real gate (403 on failure) -- this is just how the token gets there.
export async function adminFetch(path, options = {}) {
  return authFetch(buildApiUrl(path), {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });
}
