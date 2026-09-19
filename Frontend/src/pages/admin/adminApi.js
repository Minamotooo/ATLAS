import { buildApiUrl } from '../../context/AuthContext';

// Shared by every admin page: attaches the X-User-Name header the backend's
// require_admin dependency checks against ADMIN_USERNAMES. The backend is
// the real gate (403 on failure) -- this is just how the header gets there.
export async function adminFetch(path, username, options = {}) {
  const response = await fetch(buildApiUrl(path), {
    ...options,
    headers: {
      'X-User-Name': username,
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });
  return response;
}
