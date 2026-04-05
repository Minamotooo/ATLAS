import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const AuthContext = createContext(null);
const storageKey = 'atlasUser';
const apiBase = import.meta.env.VITE_API_BASE_URL || '';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        setUser(JSON.parse(saved));
      }
    } catch (error) {
      console.warn('Failed to read saved auth user', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const persistUser = (userData) => {
    localStorage.setItem(storageKey, JSON.stringify(userData));
    setUser(userData);
  };

  const signIn = async (username) => {
    const response = await fetch(`${apiBase}/users/${encodeURIComponent(username)}`);
    if (!response.ok) {
      throw new Error(response.status === 404 ? 'not_found' : 'server_error');
    }
    const userData = await response.json();
    persistUser(userData);
    return userData;
  };

  const signUp = async (username) => {
    const response = await fetch(`${apiBase}/users/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_name: username }),
    });

    if (!response.ok) {
      throw new Error(response.status === 409 ? 'already_exists' : 'server_error');
    }

    const userData = await response.json();
    persistUser(userData);
    return userData;
  };

  const signOut = () => {
    localStorage.removeItem(storageKey);
    setUser(null);
  };

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
