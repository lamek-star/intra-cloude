"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiError, ensureCsrfCookie, type User } from "@/lib/api";
import { checkWithPasskey, type PasskeyWhere } from "@/lib/passkeys";

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
  signInWithPasskey: (where?: PasskeyWhere) => Promise<User>;
  register: (email: string, password: string, firstName: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const queryClient = useQueryClient();
  const signedInId = useRef<string | null>(null);

  // Cached page data belongs to whoever was signed in when it was read: it is dropped whenever that changes
  // (sign-in, two-step, registration, sign-out, an expired session), so it never shows to someone else.
  const setUser = useCallback(
    (next: User | null) => {
      const id = next?.id ?? null;
      if (id !== signedInId.current) {
        queryClient.clear();
        signedInId.current = id;
      }
      setUserState(next);
    },
    [queryClient],
  );

  const refresh = useCallback(async () => {
    try {
      const me = await api.get<User>("/auth/me/");
      setUser(me);
    } catch {
      setUser(null);
    }
  }, [setUser]);

  useEffect(() => {
    // Together: reading /auth/me/ is a GET and needs no CSRF cookie; only later changes do.
    // One-shot fetch-on-mount, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    Promise.allSettled([ensureCsrfCookie(), refresh()]).finally(() => setLoading(false));
  }, [refresh]);

  const login = useCallback(async (email: string, password: string): Promise<LoginResult> => {
    const result = await api.post<User | { mfa_required: true }>("/auth/login/", { email, password });
    if ("mfa_required" in result) {
      return { mfaRequired: true };
    }
    setUser(result);
    return result;
  }, [setUser]);

  const verifyMfa = useCallback(async (code: string): Promise<User> => {
    const result = await api.post<User>("/auth/mfa/verify/", { code });
    setUser(result);
    return result;
  }, [setUser]);

  const signInWithPasskey = useCallback(async (where?: PasskeyWhere): Promise<User> => {
    const result = await checkWithPasskey(where);
    setUser(result);
    return result;
  }, [setUser]);

  const register = useCallback(async (email: string, password: string, firstName: string) => {
    const result = await api.post<User>("/auth/register/", {
      email,
      password,
      first_name: firstName,
    });
    setUser(result);
    return result;
  }, [setUser]);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout/");
    } catch (err) {
      // A 403 here just means the session was already gone — still clear
      // local state either way.
      if (!(err instanceof ApiError)) throw err;
    }
    setUser(null);
  }, [setUser]);

  return (
    <AuthContext.Provider value={{ user, loading, login, verifyMfa, signInWithPasskey, register, logout, refresh }}>
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
