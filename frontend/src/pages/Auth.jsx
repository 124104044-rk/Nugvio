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
