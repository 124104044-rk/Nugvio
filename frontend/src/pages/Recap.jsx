import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { inr } from "@/lib/currency";
import { toast } from "sonner";
import { Copy, Flame, PiggyBank, Receipt, Target, HeartPulse, Wallet } from "lucide-react";


export default function Recap() {
  const [d, setD] = useState(null);
  useEffect(() => { (async () => setD((await api.get("/recap/weekly")).data))(); }, []);

  const share = async () => {
    const t = [
      "My Week in Money — NugVio",
      `Saved: ${inr(d.saved)}`,
      `Spent: ${inr(d.spent)} (${d.spend_delta <= 0 ? "" : "+"}${inr(d.spend_delta)} vs last week)`,
      d.budget_used_pct != null ? `Budget used: ${d.budget_used_pct}%` : null,
      `Goal progress: +${d.goal_progress_pct}%`,
      `Streak: ${d.streak_days} days`,
      `Financial Health: ${d.health_score}${d.health_delta != null ? ` (${d.health_delta >= 0 ? "+" : ""}${d.health_delta})` : ""}`,
    ].filter(Boolean).join("\n");
    try {
      await navigator.clipboard.writeText(t);
      toast.success("Recap copied — paste it anywhere");
    } catch {
      toast.error("Couldn't copy automatically");
    }
  };

  const spendDown = d && d.spend_delta <= 0;

  const Row = ({ icon: Icon, color, label, value, sub, tid }) => (
    <div className="flex items-center justify-between p-4 border-b border-[var(--border)]" data-testid={tid}>
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-full" style={{ background: `${color}18` }}><Icon size={18} color={color} /></div>
        <div className="font-semibold">{label}</div>
      </div>
      <div className="text-right">
        <div className="text-xl font-bold">{value}</div>
        {sub && <div className="text-xs text-[var(--ink-soft)]">{sub}</div>}
      </div>
    </div>
  );

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-end justify-between">
        <div>
          <div className="font-hand text-2xl" style={{ color: "var(--coral)" }}>every sunday vibe —</div>
          <h1 className="text-4xl font-bold">Your Week in Money</h1>
          {d && <p className="text-[var(--ink-soft)] mt-1">{d.period.from} → {d.period.to}</p>}
        </div>
        <button data-testid="recap-share" onClick={share} className="pill-btn btn-primary inline-flex items-center gap-2"><Copy size={15} /> Copy recap</button>
      </div>

      {d && (
        <div className="card p-0 overflow-hidden" data-testid="recap-card">
          <Row icon={PiggyBank} color="#16A34A" label="Saved toward goals" value={inr(d.saved)} tid="recap-saved" />
          <Row icon={Receipt} color={spendDown ? "#16A34A" : "#F97316"} label="Spent this week" value={inr(d.spent)}
            sub={`${spendDown ? "↓" : "↑"} ${inr(Math.abs(d.spend_delta))} vs last week${d.top_category ? ` · top: ${d.top_category.name}` : ""}`} tid="recap-spent" />
          {d.budget_used_pct != null && (
            <Row icon={Wallet} color={d.budget_used_pct > 90 ? "#F43F5E" : "#2563EB"} label="Monthly budget used" value={`${d.budget_used_pct}%`} tid="recap-budget" />
          )}
          <Row icon={Target} color="#2563EB" label="Goal progress this week" value={`+${d.goal_progress_pct}%`} tid="recap-goals" />
          <Row icon={Flame} color="#F97316" label="Financial streak" value={`${d.streak_days} days`} tid="recap-streak" />
          <Row icon={HeartPulse} color="#F43F5E" label="Financial Health"
            value={<span>{d.health_score}{d.health_delta != null && <span className="text-sm font-bold ml-1" style={{ color: d.health_delta >= 0 ? "#16A34A" : "#F43F5E" }}>({d.health_delta >= 0 ? "+" : ""}{d.health_delta})</span>}</span>} tid="recap-health" />
        </div>
      )}

      <div className="card p-5 nudge-blue text-sm" data-testid="recap-note">
        Come back every week — small consistent wins are how wealth actually happens.
      </div>
    </div>
  );
}
