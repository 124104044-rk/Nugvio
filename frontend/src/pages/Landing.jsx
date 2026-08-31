import { Link } from "react-router-dom";
import { LOGO_URL } from "@/lib/api";
import { Sparkles, ShieldCheck, Bot, Coins, ArrowRight, Zap, TrendingUp, Trophy } from "lucide-react";

export default function Landing() {
  return (
    <div className="min-h-screen paper-grain">
      {/* Nav */}
      <header className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2" data-testid="landing-logo">
          <img src={LOGO_URL} alt="NugVio" className="h-11 w-auto" />
        </div>
        <nav className="hidden md:flex items-center gap-1">
          <a href="#why" className="nav-link">Why NugVio</a>
          <a href="#features" className="nav-link">Features</a>
          <a href="#rewards" className="nav-link">Rewards</a>
          <a href="#pricing" className="nav-link">Pricing</a>
        </nav>
        <div className="flex items-center gap-2">
          <Link to="/login" className="pill-btn btn-ghost" data-testid="nav-login">Log in</Link>
          <Link to="/signup" className="pill-btn btn-primary" data-testid="nav-signup">Get started</Link>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 pt-12 pb-24 grid md:grid-cols-12 gap-10 items-start">
        <div className="md:col-span-7">
          <div className="chip mb-6" style={{background:'#FFEDD5', borderColor:'#FED7AA', color:'#9A3412'}}>
            <Sparkles size={14}/> AI Financial Operating System · Built in India
          </div>
          <h1 className="text-6xl md:text-7xl font-extrabold leading-[0.95] tracking-tighter">
            Track less.<br/>
            <span style={{color:'var(--blue)'}}>Grow more.</span>
          </h1>
          <p className="font-hand text-3xl mt-4" style={{color:'var(--coral)'}}>
            nudge the youth →
          </p>
          <p className="mt-6 text-lg text-[var(--ink-soft)] max-w-xl leading-relaxed">
            NugVio isn't another expense tracker. It's an AI coach that tells you what to do next with your money —
            and rewards you for saving, budgeting and investing. Not for spending.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/signup" className="pill-btn btn-primary inline-flex items-center gap-2" data-testid="hero-cta-signup">
              Start free <ArrowRight size={18}/>
            </Link>
            <Link to="/login" className="pill-btn btn-ghost" data-testid="hero-cta-login">Try the demo</Link>
          </div>
          <div className="mt-10 grid grid-cols-3 gap-4 max-w-md">
            <div><div className="text-2xl font-bold">18–30</div><div className="text-xs text-[var(--ink-soft)]">Built for Indian youth</div></div>
            <div><div className="text-2xl font-bold">₹0</div><div className="text-xs text-[var(--ink-soft)]">To get started</div></div>
            <div><div className="text-2xl font-bold">1 app</div><div className="text-xs text-[var(--ink-soft)]">Not 7</div></div>
          </div>
        </div>

        {/* Floating widgets collage */}
        <div className="md:col-span-5 relative h-[520px]">
          <div className="card p-5 absolute top-0 right-0 w-72 animate-slide" style={{animationDelay:'80ms'}}>
            <div className="text-xs text-[var(--ink-soft)] mb-1">Financial Health Score</div>
            <div className="flex items-center gap-4">
              <div className="gauge-ring" style={{"--pct": 78}}>
                <div className="bg-white rounded-full w-16 h-16 flex items-center justify-center text-xl font-extrabold">78</div>
              </div>
              <div>
                <div className="text-sm font-semibold">You're doing great</div>
                <div className="text-xs text-[var(--ink-soft)]">+6 this week</div>
              </div>
            </div>
          </div>

          <div className="card p-5 absolute top-40 left-0 w-80 nudge-orange animate-slide" style={{animationDelay:'180ms'}}>
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-full" style={{background:'#FED7AA'}}><Bot size={18} color="#9A3412"/></div>
              <div>
                <div className="font-semibold">Coach nudge</div>
                <div className="text-sm text-[var(--ink-soft)] mt-1">Your Food spend is 92% of budget. Cook 2 meals this week to hit target.</div>
              </div>
            </div>
          </div>

          <div className="card p-5 absolute bottom-6 right-4 w-72 animate-slide" style={{animationDelay:'260ms'}}>
            <div className="flex items-center gap-3 mb-2">
              <Coins size={18} color="#F43F5E"/>
              <div className="font-semibold">NugPoints</div>
            </div>
            <div className="text-3xl font-extrabold">850</div>
            <div className="text-xs text-[var(--ink-soft)] mt-1">Earned by saving, not spending</div>
          </div>

          <div className="card p-5 absolute bottom-40 left-6 w-64 nudge-green animate-slide" style={{animationDelay:'340ms'}}>
            <div className="text-xs text-[var(--ink-soft)]">MacBook goal</div>
            <div className="font-semibold">₹35,000 / ₹1,20,000</div>
            <div className="mt-2 h-2 rounded-full bg-white">
              <div className="h-2 rounded-full" style={{width:'29%', background:'var(--green)'}} />
            </div>
          </div>
        </div>
      </section>

      {/* Why */}
      <section id="why" className="bg-white border-y border-[var(--border)]">
        <div className="max-w-7xl mx-auto px-6 py-20">
          <h2 className="text-4xl font-bold max-w-3xl">Every other app tells you <span className="line-through text-[var(--ink-soft)]">what happened</span>. NugVio tells you what to do next.</h2>
          <div className="grid md:grid-cols-4 gap-5 mt-10">
            {[
              {i: Bot, c: 'var(--blue)', t: "AI Coach", d: "Ask 'Should I invest?' in plain English. Get honest answers, not jargon."},
              {i: TrendingUp, c: 'var(--green)', t: "Predictive nudges", d: "'You'll miss your Bali goal by 4 weeks' — before it happens."},
              {i: Trophy, c: 'var(--coral)', t: "Reward discipline", d: "Earn NugPoints for saving, budgeting, killing debt. Not shopping sprees."},
              {i: ShieldCheck, c: 'var(--orange)', t: "Built for India", d: "SIP, PPF, HRA, 80C, UPI — the coach knows your world."},
            ].map((x,i)=>(
              <div key={i} className="card p-6">
                <div className="p-3 rounded-2xl inline-flex" style={{background:'#F1F5F9'}}><x.i size={22} color={x.c}/></div>
                <div className="font-semibold text-lg mt-4">{x.t}</div>
                <div className="text-sm text-[var(--ink-soft)] mt-1">{x.d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features grid */}
      <section id="features" className="max-w-7xl mx-auto px-6 py-20">
        <div className="flex items-end justify-between mb-8">
          <h2 className="text-4xl font-bold max-w-xl">One app. Every money moment.</h2>
          <p className="font-hand text-2xl" style={{color:'var(--coral)'}}>← replaces 7 apps</p>
        </div>
        <div className="grid md:grid-cols-3 gap-5">
          {[
            {t:"Smart Expenses", d:"Type 'Zomato 340' — AI categorizes it. No forms."},
            {t:"Budget Planner", d:"Category-wise limits with live alerts before you overshoot."},
            {t:"Goal Planner", d:"Laptop, MBA, Bali. NugVio tells you the monthly SIP needed."},
            {t:"Debt Optimizer", d:"Snowball or Avalanche? See how much you'd save either way."},
            {t:"Tax Assistant", d:"Compare Old vs New regime in seconds. Educational only."},
            {t:"Cashflow Predict", d:"30-day forecast — spot the shortage before it hits."},
          ].map((f,i)=>(
            <div key={i} className="card p-6 hover:-translate-y-1 transition-transform">
              <div className="text-xs text-[var(--ink-soft)]">{String(i+1).padStart(2,'0')}</div>
              <div className="text-xl font-semibold mt-1">{f.t}</div>
              <div className="text-sm text-[var(--ink-soft)] mt-2">{f.d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Rewards */}
      <section id="rewards" className="bg-[var(--ink)] text-white">
        <div className="max-w-7xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-10 items-center">
          <div>
            <div className="chip mb-4" style={{background:'#1E293B', borderColor:'#334155', color:'#FDA4AF'}}>
              <Zap size={14}/> NugPoints
            </div>
            <h2 className="text-4xl font-bold" style={{color:'#fff'}}>Rewards for the boring stuff.</h2>
            <p className="text-slate-300 mt-4 max-w-lg">
              Save ₹1,000? Earn NugPoints. Complete a lesson? More points. Pay a bill on time? More.
              Redeem for Amazon, BookMyShow, Myntra, IRCTC or NugVio Premium.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[
              {b:"Amazon", t:"₹100 voucher", p:500},
              {b:"BookMyShow", t:"2 tickets", p:1200},
              {b:"Myntra", t:"₹200 credit", p:800},
              {b:"NugVio", t:"1M Premium", p:1500},
            ].map((r,i)=>(
              <div key={i} className="p-5 rounded-2xl bg-[#0F172A] border border-slate-700">
                <div className="text-sm text-slate-400">{r.b}</div>
                <div className="text-xl font-semibold mt-1" style={{color:'#fff'}}>{r.t}</div>
                <div className="text-sm mt-3" style={{color:'var(--coral)'}}>{r.p} NugPoints</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-7xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-6">
          <div className="card p-8">
            <div className="text-xs text-[var(--ink-soft)]">Free forever</div>
            <div className="text-3xl font-bold mt-1">₹0</div>
            <ul className="mt-6 space-y-2 text-sm">
              <li>✓ Expense tracker + AI categorization</li>
              <li>✓ Budgets + Goals</li>
              <li>✓ Financial Health Score</li>
              <li>✓ 5 AI Coach messages / day</li>
              <li>✓ NugPoints & basic rewards</li>
            </ul>
            <Link to="/signup" className="pill-btn btn-ghost inline-block mt-8" data-testid="pricing-free-cta">Start free</Link>
          </div>
          <div className="card p-8" style={{background:'#0F172A', color:'#fff', borderColor:'#1E293B'}}>
            <div className="text-xs" style={{color:'#94A3B8'}}>Premium · investor-ready</div>
            <div className="flex items-baseline gap-2 mt-1">
              <div className="text-3xl font-bold" style={{color:'#fff'}}>₹199</div>
              <div className="text-sm" style={{color:'#94A3B8'}}>/ month</div>
            </div>
            <ul className="mt-6 space-y-2 text-sm" style={{color:'#CBD5E1'}}>
              <li>✓ Unlimited AI Coach</li>
              <li>✓ Debt Optimizer (Snowball & Avalanche)</li>
              <li>✓ Tax Assistant + Cashflow Prediction</li>
              <li>✓ Advanced Financial Literacy modules</li>
              <li>✓ Premium reward multiplier</li>
            </ul>
            <Link to="/signup" className="pill-btn btn-orange inline-block mt-8" data-testid="pricing-premium-cta">Try 14 days free</Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-[var(--border)]">
        <div className="max-w-7xl mx-auto px-6 py-10 flex items-center justify-between text-sm text-[var(--ink-soft)]">
          <div className="flex items-center gap-2">
            <img src={LOGO_URL} className="h-7 w-auto" alt=""/>
            <span>© 2026 NugVio · Nudge The Youth</span>
          </div>
          <div>Not a bank. Educational content only.</div>
        </div>
      </footer>
    </div>
  );
}
