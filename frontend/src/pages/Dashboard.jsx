import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Bot, TrendingUp, ShieldAlert, Trophy, ArrowRight, Coins } from "lucide-react";
import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from "recharts";
import { Link } from "react-router-dom";

export default function Dashboard() {
  const { user } = useAuth();
  const [score, setScore] = useState(null);
  const [nudges, setNudges] = useState([]);
  const [cashflow, setCashflow] = useState(null);
  const [goals, setGoals] = useState([]);
  const [expenses, setExpenses] = useState([]);

  useEffect(() => {
    (async () => {
      const [s, n, c, g, e] = await Promise.all([
        api.get("/health-score/breakdown").then(r=>r.data),
        api.get("/nudges").then(r=>r.data),
        api.get("/cashflow/predict").then(r=>r.data),
        api.get("/goals").then(r=>r.data),
        api.get("/expenses?limit=6").then(r=>r.data),
      ]);
      setScore(s); setNudges(n); setCashflow(c); setGoals(g); setExpenses(e);
    })();
  }, []);

  const toneClass = (t) => t==="danger"?"nudge-red":t==="warning"?"nudge-orange":t==="positive"?"nudge-green":"nudge-blue";

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <div className="font-hand text-2xl" style={{color:'var(--coral)'}}>hey {user?.name?.split(' ')[0] || 'friend'} —</div>
          <h1 className="text-4xl font-bold tracking-tight">Here's your next move.</h1>
        </div>
        <div className="chip" data-testid="dash-nugpoints">
          <Coins size={14} color="#F43F5E"/> <span className="font-bold">{user?.nug_points ?? 0}</span> NugPoints
        </div>
      </div>

      {/* Top nudge banner */}
      {nudges[0] && (
        <div className={`card p-5 ${toneClass(nudges[0].tone)}`} data-testid="dash-top-nudge">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-full bg-white border border-[var(--border)]"><Bot size={20}/></div>
            <div className="flex-1">
              <div className="text-xs uppercase tracking-wider text-[var(--ink-soft)] font-semibold">Next best action</div>
              <div className="text-lg font-semibold mt-1">{nudges[0].title}</div>
              <div className="text-sm text-[var(--ink-soft)] mt-1">{nudges[0].message}</div>
            </div>
            <Link to="/app/actions" className="pill-btn btn-primary text-sm inline-flex items-center gap-2" data-testid="act-now-btn">
              Act now <ArrowRight size={16}/>
            </Link>
          </div>
        </div>
      )}

      {/* Bento grid */}
      <div className="grid grid-cols-12 gap-5">
        {/* Health score */}
        <div className="card p-6 col-span-12 md:col-span-5" data-testid="dash-health-score">
          <div className="text-xs text-[var(--ink-soft)]">Financial Health Score</div>
          <div className="flex items-center gap-6 mt-3">
            <div className="w-40 h-40">
              <ResponsiveContainer>
                <RadialBarChart innerRadius="70%" outerRadius="100%" data={[{name:'s', value: score?.overall ?? 0, fill: score?.overall>=70?'#16A34A':score?.overall>=40?'#F97316':'#F43F5E'}]} startAngle={90} endAngle={-270}>
                  <PolarAngleAxis type="number" domain={[0,100]} tick={false} />
                  <RadialBar background dataKey="value" cornerRadius={100} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <div>
              <div className="text-6xl font-extrabold leading-none">{score?.overall ?? '–'}</div>
              <div className="text-sm text-[var(--ink-soft)] mt-1">out of 100 · next stop {score?.target ?? 80}</div>
              <div className="mt-3 space-y-1 text-sm">
                {(score?.components ?? []).slice(0, 3).map(c => (
                  <div key={c.key} className="flex justify-between gap-6"><span>{c.label}</span><b>{c.points}/{c.max}</b></div>
                ))}
              </div>
              <Link to="/app/actions" className="text-sm font-semibold text-[var(--blue)] mt-2 inline-block" data-testid="dash-boost-score">Full breakdown →</Link>
            </div>
          </div>
        </div>

        {/* NugPoints wallet */}
        <div className="card p-6 col-span-12 md:col-span-3" style={{background:'#FFF1F2', borderColor:'#FECDD3'}} data-testid="dash-wallet">
          <div className="flex items-center gap-2"><Trophy size={18} color="#F43F5E"/> <div className="text-sm font-semibold" style={{color:'#9F1239'}}>NugPoints Wallet</div></div>
          <div className="text-5xl font-extrabold mt-3">{user?.nug_points ?? 0}</div>
          <div className="text-xs text-[var(--ink-soft)] mt-1">Earned by saving, not spending</div>
          <Link to="/app/rewards" className="pill-btn btn-orange text-sm mt-4 inline-block" data-testid="dash-redeem">Redeem →</Link>
        </div>

        {/* Cash flow */}
        <div className="card p-6 col-span-12 md:col-span-4" data-testid="dash-cashflow">
          <div className="text-xs text-[var(--ink-soft)]">30-day cashflow forecast</div>
          <div className="text-lg font-semibold">Avg daily spend ₹{Math.round(cashflow?.avg_daily_spend ?? 0)}</div>
          <div className="h-32 mt-2">
            <ResponsiveContainer>
              <AreaChart data={cashflow?.forecast ?? []}>
                <defs>
                  <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563EB" stopOpacity={0.4}/>
                    <stop offset="100%" stopColor="#2563EB" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="day" hide/>
                <YAxis hide/>
                <Tooltip formatter={(v)=>`₹${Math.round(v)}`} labelFormatter={(l)=>`Day ${l}`}/>
                <Area type="monotone" dataKey="balance" stroke="#2563EB" strokeWidth={2} fill="url(#g1)"/>
              </AreaChart>
            </ResponsiveContainer>
          </div>
          {cashflow?.warnings?.[0] && (
            <div className="text-xs mt-1 flex items-center gap-1" style={{color:'var(--coral)'}}>
              <ShieldAlert size={14}/> {cashflow.warnings[0].message}
            </div>
          )}
        </div>

        {/* Nudges list */}
        <div className="card p-6 col-span-12 md:col-span-7" data-testid="dash-nudges">
          <div className="flex items-center justify-between mb-3">
            <div className="text-lg font-semibold">Coach nudges</div>
            <TrendingUp size={18} color="#F97316"/>
          </div>
          <div className="space-y-3">
            {nudges.slice(1).map((n, i) => (
              <div key={n.id} className={`card p-4 ${toneClass(n.tone)} animate-slide`} style={{animationDelay:`${i*40}ms`}}>
                <div className="font-semibold">{n.title}</div>
                <div className="text-sm text-[var(--ink-soft)]">{n.message}</div>
              </div>
            ))}
            {nudges.length <= 1 && <div className="text-sm text-[var(--ink-soft)]">All quiet. Keep the discipline.</div>}
          </div>
        </div>

        {/* Recent expenses */}
        <div className="card p-6 col-span-12 md:col-span-5" data-testid="dash-recent-expenses">
          <div className="flex items-center justify-between mb-3">
            <div className="text-lg font-semibold">Recent expenses</div>
            <Link to="/app/expenses" className="text-sm font-semibold text-[var(--blue)]">View all →</Link>
          </div>
          <div className="divide-y divide-[var(--border)]">
            {expenses.slice(0,6).map(e => (
              <div key={e.id} className="py-2 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold">{e.description}</div>
                  <div className="text-xs text-[var(--ink-soft)]">{e.category} · {new Date(e.date).toLocaleDateString()}</div>
                </div>
                <div className="font-bold">₹{Math.round(e.amount)}</div>
              </div>
            ))}
            {expenses.length===0 && <div className="text-sm text-[var(--ink-soft)] py-3">No expenses yet — add one from the Expenses tab.</div>}
          </div>
        </div>

        {/* Goals summary */}
        <div className="card p-6 col-span-12" data-testid="dash-goals">
          <div className="flex items-center justify-between mb-3">
            <div className="text-lg font-semibold">Your goals</div>
            <Link to="/app/goals" className="text-sm font-semibold text-[var(--blue)]">Manage →</Link>
          </div>
          <div className="grid md:grid-cols-3 gap-4">
            {goals.map(g => {
              const pct = Math.min(100, (g.saved_amount / g.target_amount) * 100);
              return (
                <div key={g.id} className="card p-4">
                  <div className="text-sm text-[var(--ink-soft)]">Goal</div>
                  <div className="font-semibold text-lg">{g.title}</div>
                  <div className="text-xs text-[var(--ink-soft)] mt-1">₹{Math.round(g.saved_amount)} / ₹{Math.round(g.target_amount)}</div>
                  <div className="mt-2 h-2 rounded-full bg-slate-100">
                    <div className="h-2 rounded-full" style={{width:`${pct}%`, background: pct>=70?'#16A34A':'#2563EB'}}/>
                  </div>
                </div>
              );
            })}
            {goals.length===0 && <div className="text-sm text-[var(--ink-soft)]">No goals yet.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
