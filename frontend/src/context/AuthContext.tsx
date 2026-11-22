import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";
import { api, TOKEN_STORAGE_KEY } from "../api/client";

export interface AuthUser {
  id: number;
  full_name: string;
  email: string;
  created_at: string;
}

interface AuthResponse {
  access_token: string;
  user: AuthUser;
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  updateProfile: (fullName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const acceptSession = useCallback((response: AuthResponse) => {
    window.sessionStorage.setItem(TOKEN_STORAGE_KEY, response.access_token);
    setUser(response.user);
  }, []);

  useEffect(() => {
    const token = window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) {
      setIsLoading(false);
      return;
    }
    api
      .get<AuthUser>("/auth/me")
      .then(({ data }) => setUser(data))
      .catch(() => {
        window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const { data } = await api.post<AuthResponse>("/auth/login", { email, password });
      acceptSession(data);
    },
    [acceptSession],
  );

  const register = useCallback(
    async (fullName: string, email: string, password: string) => {
      const { data } = await api.post<AuthResponse>("/auth/register", {
        full_name: fullName,
        email,
        password,
      });
      acceptSession(data);
    },
    [acceptSession],
  );

  const updateProfile = useCallback(async (fullName: string) => {
    const { data } = await api.patch<AuthUser>("/auth/me", { full_name: fullName });
    setUser(data);
  }, []);

  const logout = useCallback(() => {
    window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, isLoading, login, register, updateProfile, logout }),
    [user, isLoading, login, register, updateProfile, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider.");
  return context;
}