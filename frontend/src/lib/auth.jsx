import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, TOKEN_KEY, UNAUTHORIZED_EVENT } from "@/lib/api";

const AuthCtx = createContext(null);

// Long enough to survive a free-tier backend cold start, short enough that the
// startup check can never hang forever.
const ME_TIMEOUT_MS = 60000;

export function classifyAuthError(err) {
  const status = err?.response?.status;
  if (status === 401 || status === 403) return { kind: "unauthenticated" };
  if (err?.code === "ECONNABORTED" || err?.code === "ETIMEDOUT") {
    return { kind: "error", message: "The server is taking too long to respond. It may be waking up — please retry in a moment." };
  }
  if (!err?.response) {
    return { kind: "error", message: "Couldn't reach the NugVio server. Check your connection and retry." };
  }
  return { kind: "error", message: `The server returned an error (${status}). Please retry.` };
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = anon, obj = user
  const [authError, setAuthError] = useState(null); // message when the check failed for non-auth reasons

  const load = useCallback(async () => {
    setAuthError(null);
    try {
      const { data } = await api.get("/auth/me", { timeout: ME_TIMEOUT_MS });
      if (data.currency) localStorage.setItem("nugvio_currency", data.currency);
      setUser(data);
    } catch (err) {
      const r = classifyAuthError(err);
      if (r.kind === "unauthenticated") {
        // Missing / expired / invalid token -> clear it and go to login.
        localStorage.removeItem(TOKEN_KEY);
        setUser(false);
      } else {
        // Genuine network/server problem: don't pretend the user is logged out,
        // surface the error so the UI can offer a retry.
        setUser((u) => (u ? u : null));
        setAuthError(r.message);
      }
    }
  }, []);

  useEffect(() => {
    // CRITICAL: If returning from OAuth callback, skip the /me check.
    // AuthCallback will exchange the session_id and establish the session first.
    if (window.location.hash?.includes("session_id=")) return;
    load();
  }, [load]);

  // Any authenticated API call that comes back 401 (e.g. token expired mid-session)
  // ends the session cleanly instead of leaving the app half-loaded.
  useEffect(() => {
    const onUnauthorized = () => { setAuthError(null); setUser(false); };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    if (data.token) localStorage.setItem(TOKEN_KEY, data.token);
    setAuthError(null);
    setUser(data);
    return data;
  };
  const register = async (name, email, password) => {
    const { data } = await api.post("/auth/register", { name, email, password });
    if (data.token) localStorage.setItem(TOKEN_KEY, data.token);
    setAuthError(null);
    setUser(data);
    return data;
  };
  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    localStorage.removeItem(TOKEN_KEY);
    setUser(false);
  };
  const refresh = load;

  return (
    <AuthCtx.Provider value={{ user, authError, login, register, logout, refresh, setUser }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
