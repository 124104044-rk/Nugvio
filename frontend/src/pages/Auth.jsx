import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { LOGO_URL } from "@/lib/api";
import { toast } from "sonner";

function formatErr(d) {
  if (!d) return "Something went wrong";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map(e => e?.msg || JSON.stringify(e)).join(" ");
  return d?.msg || JSON.stringify(d);
}

export default function AuthPage({ mode }) {
  const isLogin = mode === "login";
  const nav = useNavigate();
  const { login, register } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState(isLogin ? "demo@nugvio.in" : "");
  const [password, setPassword] = useState(isLogin ? "Nugvio@123" : "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      if (isLogin) await login(email, password);
      else await register(name, email, password);
      toast.success(isLogin ? "Welcome back" : "Welcome to Nugvio");
      nav("/app");
    } catch (e2) {
      setErr(formatErr(e2.response?.data?.detail) || e2.message);
    } finally { setBusy(false); }
  };

  const googleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/app";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen grid md:grid-cols-2">
      <div className="hidden md:flex flex-col justify-between p-10 relative" style={{background:'#0F172A', color:'#fff'}}>
        <Link to="/" className="flex items-center gap-2" data-testid="auth-logo-link">
          <img src={LOGO_URL} alt="Nugvio" className="h-11 w-auto"/>
        </Link>
        <div>
          <div className="font-hand text-3xl mb-3" style={{color:'#FDA4AF'}}>nudge the youth</div>
          <h2 className="text-4xl font-bold" style={{color:'#fff'}}>Track less.<br/>Grow more.</h2>
          <p className="text-slate-300 mt-4 max-w-md">
            Your AI financial coach that rewards discipline instead of spending. Built for young India.
          </p>
        </div>
        <div className="text-xs text-slate-500">Demo credentials pre-filled — just click Log in.</div>
      </div>

      <div className="flex items-center justify-center p-6 paper-grain">
        <form onSubmit={submit} className="w-full max-w-sm card p-8" data-testid="auth-form">
          <div className="md:hidden flex justify-center mb-4"><img src={LOGO_URL} className="h-10 w-auto" alt=""/></div>
          <h1 className="text-3xl font-bold mb-1">{isLogin ? "Welcome back" : "Create your account"}</h1>
          <p className="text-sm text-[var(--ink-soft)] mb-6">{isLogin ? "Log in to your Nugvio dashboard" : "Start nudging your money in 30 seconds"}</p>

          {!isLogin && (
            <div className="mb-3">
              <label className="text-xs font-semibold text-[var(--ink-soft)]">Name</label>
              <input data-testid="auth-name" className="input mt-1" value={name} onChange={e=>setName(e.target.value)} required placeholder="Priya Sharma"/>
            </div>
          )}
          <div className="mb-3">
            <label className="text-xs font-semibold text-[var(--ink-soft)]">Email</label>
            <input data-testid="auth-email" type="email" className="input mt-1" value={email} onChange={e=>setEmail(e.target.value)} required placeholder="you@example.com"/>
          </div>
          <div className="mb-3">
            <label className="text-xs font-semibold text-[var(--ink-soft)]">Password</label>
            <input data-testid="auth-password" type="password" className="input mt-1" value={password} onChange={e=>setPassword(e.target.value)} required minLength={6}/>
          </div>

          {err && <div className="text-sm text-[var(--coral)] my-2" data-testid="auth-error">{err}</div>}

          <button data-testid="auth-submit" disabled={busy} className="pill-btn btn-primary w-full mt-2">
            {busy ? "Please wait…" : isLogin ? "Log in" : "Create account"}
          </button>

          <div className="flex items-center gap-3 my-4">
            <div className="flex-1 h-px bg-[var(--border)]" />
            <span className="text-xs text-[var(--ink-soft)]">or</span>
            <div className="flex-1 h-px bg-[var(--border)]" />
          </div>

          <button type="button" data-testid="google-login-btn" onClick={googleLogin}
            className="pill-btn btn-ghost w-full flex items-center justify-center gap-2 border border-[var(--border)]">
            <svg width="17" height="17" viewBox="0 0 24 24" aria-hidden="true">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.1z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.1A6.6 6.6 0 0 1 5.5 12c0-.73.13-1.44.34-2.1V7.06H2.18A11 11 0 0 0 1 12c0 1.77.43 3.45 1.18 4.94l3.66-2.84z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"/>
            </svg>
            Continue with Google
          </button>

          <div className="text-sm text-[var(--ink-soft)] mt-6 text-center">
            {isLogin ? (
              <>New to Nugvio? <Link to="/signup" className="font-semibold text-[var(--blue)]" data-testid="switch-signup">Create account</Link></>
            ) : (
              <>Already have an account? <Link to="/login" className="font-semibold text-[var(--blue)]" data-testid="switch-login">Log in</Link></>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
