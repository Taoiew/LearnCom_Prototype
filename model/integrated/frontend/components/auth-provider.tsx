"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  clearAuthUser,
  getStoredAuthUser,
  persistAuthUser,
  type ApiUser,
} from "@/lib/api";

type AuthContextValue = {
  user: ApiUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<ApiUser>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<ApiUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedUser = getStoredAuthUser();
    if (storedUser) {
      setUser(storedUser);
    }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const { loginWithBackend } = await import("@/lib/api");
    const nextUser = await loginWithBackend(email, password);
    persistAuthUser(nextUser);
    setUser(nextUser);
    return nextUser;
  };

  const logout = () => {
    clearAuthUser();
    setUser(null);
    if (typeof window !== "undefined") {
      window.location.assign("/login");
    }
  };

  const value = useMemo(
    () => ({ user, loading, login, logout }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
