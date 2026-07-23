import { createContext, useContext, useState } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);
const USER_KEY = 'fantalol_react_user';
const TOKEN_KEY = 'fantalol_react_token';

function storedUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(storedUser);
  const [loading, setLoading] = useState(false);

  const login = async (credentials) => {
    setLoading(true);
    try {
      const session = await api.login(credentials);
      const nextUser = { username: session.username, role: session.role };
      localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
      localStorage.setItem(TOKEN_KEY, session.token);
      setUser(nextUser);
      return nextUser;
    } finally {
      setLoading(false);
    }
  };

  const register = async (details) => {
    setLoading(true);
    try {
      await api.register(details);
      return login({ username: details.username, password: details.password });
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  };

  const value = { user, loading, login, register, logout, isAuthenticated: Boolean(user) };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
