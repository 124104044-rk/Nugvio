import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Link } from "react-router-dom";
import { AlertTriangle, TrendingUp, Info, PartyPopper, ArrowRight, Sparkles } from "lucide-react";

const SEV = {
  high: { cls: "nudge-red", icon: AlertTriangle, color: "#F43F5E", label: "Act now" },
  medium: { cls: "nudge-orange", icon: TrendingUp, color: "#F97316", label: "Worth fixing" },
  low: { cls: "nudge-blue", icon: Info, color: "#2563EB", label: "Good to do" },
  win: { cls: "nudge-green", icon: PartyPopper, color: "#16A34A", label: "Win" },
};
const inr = (n) => `₹${Math.round(n).toLocaleString("en-IN")}`;

export default function ActionCenter() {
  const [data, setData] = useState(null);
  const [breakdown, setBreakdown] = useState(null);

  useEffect(() => {
    (async () => {
      const [a, b] = await Promise.all([api.get("/action-center"), api.get("/health-score/breakdown")]);
      setData(a.data); setBreakdown(b.data);
    })();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <div className="font-hand text-2xl" style={{ color: "var(--coral)" }}>your money, decoded —</div>
        <h1 className="text-4xl font-bold">What should I do today?</h1>
        <p className="text-[var(--ink-soft)] mt-1">Every insight comes with one clear action. Do them, watch your score climb.</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-3" data-testid="action-insights">
          {(data?.insights ?? []).map((ins, i) => {
            const S = SEV[ins.severity] || SEV.low;
            return (
              <div key={ins.id} className={`card p-5 ${S.cls} animate-slide`} style={{ animationDelay: `${i * 40}ms` }} data-testid={`insight-${ins.id}`}>
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-full bg-white border border-[var(--border)]"><S.icon size={18} color={S.color} /></div>
                  <div className="flex-1">
                    <div className="text-xs uppercase tracking-wider font-semibold" style={{ color: S.color }}>{S.label}</div>
                    <div className="text-lg font-semibold mt-0.5">{ins.title}</div>
                    <div className="text-sm text-[var(--ink-soft)] mt-1">{ins.message}</div>
                  </div>
                  <Link to={ins.route} className="pill-btn btn-primary text-sm whitespace-nowrap inline-flex items-center gap-1.5" data-testid={`action-btn-${ins.id}`}>
                    {ins.action_label} <ArrowRight size={14} />
                  </Link>
                </div>
              </div>
            );
          })}
          {!data && <div className="card p-6 text-[var(--ink-soft)]">Analyzing your money…</div>}
        </div>

        <div className="space-y-5">
          <div className="card p-6" data-testid="score-breakdown">
            <div className="text-xs text-[var(--ink-soft)]">Financial Health</div>
            <div className="flex items-baseline gap-2">
              <div className="text-5xl font-extrabold">{breakdown?.overall ?? "–"}</div>
              <div className="text-[var(--ink-soft)]">/100</div>
            </div>
            <div className="mt-4 space-y-3">
              {(breakdown?.components ?? []).map((c) => (
                <div key={c.key} data-testid={`score-comp-${c.key}`}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{c.label}</span>
                    <b>{c.points}/{c.max}</b>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${c.pct}%`, background: c.pct >= 70 ? "#16A34A" : c.pct >= 40 ? "#F97316" : "#F43F5E" }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card p-6" style={{ background: "#EFF6FF", borderColor: "#BFDBFE" }} data-testid="score-target-card">
            <div className="flex items-center gap-2 font-semibold"><Sparkles size={16} color="#2563EB" /> Get to {breakdown?.target ?? 80}</div>
            <p className="text-sm text-[var(--ink-soft)] mt-1">Complete these {breakdown?.actions?.length ?? 3} actions to raise your score:</p>
            <div className="mt-3 space-y-2">
              {(breakdown?.actions ?? []).map((a, i) => (
                <div key={i} className="card p-3 bg-white" data-testid={`score-action-${i}`}>
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <div className="text-sm font-semibold">{a.title}</div>
                      <div className="text-xs text-[var(--ink-soft)] mt-0.5">{a.message}</div>
                      <div className="text-xs font-semibold mt-1" style={{ color: "#16A34A" }}>up to +{a.potential_gain} pts ({a.component})</div>
                    </div>
                    <Link to={a.route} className="pill-btn btn-ghost text-xs whitespace-nowrap">{a.label}</Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
