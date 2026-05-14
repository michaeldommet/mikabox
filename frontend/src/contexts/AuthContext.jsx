import { createContext, useContext, useState, useEffect } from 'react';
import { api, setTokens, clearTokens, getAccessToken } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing token on mount
    const token = getAccessToken();
    if (token) {
      api.getMe()
        .then(setUser)
        .catch(() => clearTokens())
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const data = await api.login(email, password);
    if (data.access_token) {
      setTokens(data.access_token, data.refresh_token);
      const me = await api.getMe();
      setUser(me);
      return true;
    }
    throw new Error(data.detail || 'Login failed');
  };

  const register = async (email, password, displayName) => {
    const data = await api.register(email, password, displayName);
    if (data.access_token) {
      setTokens(data.access_token, data.refresh_token);
      const me = await api.getMe();
      setUser(me);
      return true;
    }
    throw new Error(data.detail || 'Registration failed');
  };

  const logout = () => {
    clearTokens();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
