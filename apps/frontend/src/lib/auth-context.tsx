"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, ApiError, ensureCsrfCookie, type User } from "@/lib/api";

type MfaRequiredResult = { mfaRequired: true };
type LoginResult = User | MfaRequiredResult;

function isMfaRequired(result: LoginResult): result is MfaRequiredResult {
  return "mfaRequired" in result;
}

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<LoginResult>;
  verifyMfa: (code: string) => Promise<User>;
  register: (email: string, password: string, firstName: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const me = await api.get<User>("/auth/me/");
      setUser(me);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    ensureCsrfCookie().finally(() => {
      refresh().finally(() => setLoading(false));
    });
  }, [refresh]);

  const login = useCallback(async (email: string, password: string): Promise<LoginResult> => {
    const result = await api.post<User | { mfa_required: true }>("/auth/login/", { email, password });
    if ("mfa_required" in result) {
      return { mfaRequired: true };
    }
    setUser(result);
    return result;
  }, []);

  const verifyMfa = useCallback(async (code: string): Promise<User> => {
    const result = await api.post<User>("/auth/mfa/verify/", { code });
    setUser(result);
    return result;
  }, []);

  const register = useCallback(async (email: string, password: string, firstName: string) => {
    const result = await api.post<User>("/auth/register/", {
      email,
      password,
      first_name: firstName,
    });
    setUser(result);
    return result;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout/");
    } catch (err) {
      // A 403 here just means the session was already gone — still clear
      // local state either way.
      if (!(err instanceof ApiError)) throw err;
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, verifyMfa, register, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export { isMfaRequired };
