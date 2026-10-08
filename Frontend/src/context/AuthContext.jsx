import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const AuthContext = createContext(null);
// { token, user }. 'atlasUser' held the old password-less session; it is discarded.
const storageKey = 'atlasSession';
const legacyStorageKey = 'atlasUser';
const unauthorizedEvent = 'atlas:unauthorized';
const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const buildApiUrl = (path) => {
  const trimmedBase = apiBase.replace(/\/$/, '');
  const trimmedPath = path.replace(/^\//, '');
  return `${trimmedBase}/${trimmedPath}`;
};

function readSession() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    return saved?.token && saved?.user ? saved : null;
  } catch {
    return null;
  }
}

// Drop-in for fetch() against the API: attaches the session token, and signs
// the user out if the backend says it has expired or been revoked.
export async function authFetch(url, options = {}) {
  const token = readSession()?.token;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (response.status === 401 && token) {
    window.dispatchEvent(new Event(unauthorizedEvent));
  }
  return response;
}

const loginErrors = { 401: 'invalid_credentials', 403: 'password_not_set', 429: 'too_many_attempts' };
const signupErrors = { 400: 'invalid', 403: 'reserved', 409: 'already_exists' };

async function postCredentials(path, username, password, errorCodes) {
  const response = await fetch(buildApiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_name: username, password }),
  });
  if (!response.ok) {
    throw new Error(errorCodes[response.status] || 'server_error');
  }
  return response.json();
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const clearSession = () => {
    localStorage.removeItem(storageKey);
    setUser(null);
  };

  useEffect(() => {
    window.addEventListener(unauthorizedEvent, clearSession);
    try {
      localStorage.removeItem(legacyStorageKey);
      const session = readSession();
      if (session) {
        setUser(session.user);
        // Re-read the account so fields that can change (is_admin) stay current.
        authFetch(buildApiUrl('/auth/me'))
          .then((response) => (response.ok ? response.json() : null))
          .then((fresh) => {
            if (fresh?.user_id === session.user.user_id) {
              localStorage.setItem(storageKey, JSON.stringify({ ...session, user: fresh }));
              setUser(fresh);
            }
          })
          .catch(() => {});
      }
    } catch (error) {
      console.warn('Failed to read saved auth session', error);
    } finally {
      setLoading(false);
    }
    return () => window.removeEventListener(unauthorizedEvent, clearSession);
  }, []);

  const persistSession = ({ token, user: userData }) => {
    localStorage.setItem(storageKey, JSON.stringify({ token, user: userData }));
    setUser(userData);
    return userData;
  };

  const signIn = async (username, password) =>
    persistSession(await postCredentials('/auth/login', username, password, loginErrors));

  const signUp = async (username, password) =>
    persistSession(await postCredentials('/auth/signup', username, password, signupErrors));

  const signOut = clearSession;

  const value = useMemo(
    () => ({ user, loading, signIn, signUp, signOut }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
