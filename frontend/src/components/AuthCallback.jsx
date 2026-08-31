import { useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
  const nav = useNavigate();
  const location = useLocation();
  const { setUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;
    (async () => {
      const params = new URLSearchParams(location.hash.replace(/^#/, ""));
      const sessionId = params.get("session_id");
      try {
        const { data } = await api.post("/auth/google/session", { session_id: sessionId });
        setUser(data);
        window.history.replaceState(null, "", window.location.pathname);
        nav("/app", { replace: true, state: { user: data } });
      } catch {
        window.history.replaceState(null, "", window.location.pathname);
        nav("/login", { replace: true });
      }
    })();
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center text-[var(--ink-soft)]" data-testid="auth-callback">
      Signing you in…
    </div>
  );
}
