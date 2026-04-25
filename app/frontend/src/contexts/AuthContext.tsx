import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";

const TOKEN_KEY = "typomaster_jwt";
const USER_KEY = "typomaster_user";

export interface AuthUser {
  user_id: string;
  github_id: number;
  username: string;
  display_name: string;
  avatar_url: string;
  email: string | null;
  bio: string | null;
  created_at: string;
  last_login_at: string;
  is_active: boolean;
}

export interface AuthState {
  authenticated: boolean;
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: () => void;
  logout: () => void;
  setAuth: (token: string, user: AuthUser) => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:50120";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<AuthUser | null>(() => {
    const saved = localStorage.getItem(USER_KEY);
    if (saved) {
      try { return JSON.parse(saved); } catch { return null; }
    }
    return null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    fetch(`${BASE_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.authenticated && data.user) {
          setUser(data.user);
          localStorage.setItem(USER_KEY, JSON.stringify(data.user));
        } else {
          setToken(null);
          setUser(null);
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
        }
      })
      .catch(() => {
        setToken(null);
        setUser(null);
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(() => {
    fetch(`${BASE_URL}/api/v1/auth/github/url`)
      .then((res) => res.json())
      .then((data) => {
        if (data.url) {
          window.location.href = data.url;
        }
      })
      .catch((err) => console.error("Failed to get GitHub auth URL:", err));
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }, []);

  const setAuth = useCallback((newToken: string, newUser: AuthUser) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem(TOKEN_KEY, newToken);
    localStorage.setItem(USER_KEY, JSON.stringify(newUser));
  }, []);

  return (
    <AuthContext.Provider
      value={{
        authenticated: !!user && !!token,
        user,
        token,
        loading,
        login,
        logout,
        setAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
