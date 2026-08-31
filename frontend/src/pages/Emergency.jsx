import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { ShieldCheck, ShieldAlert, Plus } from "lucide-react";

const inr = (n) => `₹${Math.round(n).toLocaleString("en-IN")}`;

export default function Emergency() {
  const [months, setMonths] = useState(6);
  const [d, setD] = useState(null);
  const [amt, setAmt] = useState("");

  const load = async (m = months) => setD((await api.get(`/emergency-fund?months=${m}`)).data);
  useEffect(() => { load(); }, []);

  const setM = (m) => { setMonths(m); load(m); };

  const createGoal = async () => {
    const target = Math.max(10000, Math.round(d.recommended));
    const date = new Date(Date.now() + 365 * 86400000).toISOString().slice(0, 10);
    await api.post("/goals", { title: "Emergency Fund", target_amount: target, target_date: date, icon: "shield" });
    toast.success("Emergency Fund goal created");
    load();
  };

  const contribute = async () => {
    const v = parseFloat(amt);
    if (!v || !d?.goal_id) return;
    const { data } = await api.post(`/goals/${d.goal_id}/contribute`, { amount: v });
    setAmt("");
    toast.success(`+${data.earned_points} NugPoints — fund topped up`);
    load();
  };

  const healthy = d && d.gap === 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold">Emergency Fund</h1>
        <p className="text-[var(--ink-soft)] mt-1">Your shield against job loss, medical bills, or life surprises.</p>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm text-[var(--ink-soft)]">Cover</span>
        {[3, 6, 9, 12].map((m) => (
          <button key={m} data-testid={`ef-months-${m}`} onClick={() => setM(m)} className={`pill-btn text-sm ${months === m ? "btn-primary" : "btn-ghost"}`}>{m} months</button>
        ))}
        <span className="text-sm text-[var(--ink-soft)]">of essentials</span>
      </div>

      <div className="grid md:grid-cols-4 gap-4">
        <div className="card p-5" data-testid="ef-essentials">
          <div className="text-xs text-[var(--ink-soft)]">Monthly essential expenses</div>
          <div className="text-3xl font-bold">{inr(d?.monthly_essentials ?? 0)}</div>
          <div className="text-xs text-[var(--ink-soft)] mt-1">Rent, bills, food, healthcare</div>
        </div>
        <div className="card p-5" data-testid="ef-recommended">
          <div className="text-xs text-[var(--ink-soft)]">Recommended fund ({months} mo)</div>
          <div className="text-3xl font-bold">{inr(d?.recommended ?? 0)}</div>
        </div>
        <div className="card p-5" data-testid="ef-current">
          <div className="text-xs text-[var(--ink-soft)]">Current fund</div>
          <div className="text-3xl font-bold" style={{ color: "#16A34A" }}>{inr(d?.current ?? 0)}</div>
          <div className="text-xs text-[var(--ink-soft)] mt-1">{d?.coverage_pct ?? 0}% covered</div>
        </div>
        <div className={`card p-5 ${healthy ? "nudge-green" : "nudge-orange"}`} data-testid="ef-gap">
          <div className="text-xs text-[var(--ink-soft)] flex items-center gap-1">
            {healthy ? <ShieldCheck size={14} color="#16A34A" /> : <ShieldAlert size={14} color="#F97316" />} Gap
          </div>
          <div className="text-3xl font-bold" style={{ color: healthy ? "#16A34A" : "#F97316" }}>{inr(d?.gap ?? 0)}</div>
        </div>
      </div>

      <div className="card p-6" data-testid="ef-progress">
        <div className="flex justify-between text-sm mb-2">
          <span className="font-semibold">Progress toward {months}-month cushion</span>
          <span className="text-[var(--ink-soft)]">{inr(d?.current ?? 0)} / {inr(d?.recommended ?? 0)}</span>
        </div>
        <div className="h-4 rounded-full bg-slate-100 overflow-hidden">
          <div className="h-full rounded-full" style={{ width: `${d?.coverage_pct ?? 0}%`, background: healthy ? "#16A34A" : "#F97316" }} />
        </div>
      </div>

      {d && d.gap > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-bold">Your monthly saving plan</h2>
          <div className="grid md:grid-cols-3 gap-4">
            {d.plans.map((p) => (
              <div key={p.months} className="card p-5" data-testid={`ef-plan-${p.months}`}>
                <div className="text-xs text-[var(--ink-soft)]">Close the gap in {p.months} months</div>
                <div className="text-2xl font-bold mt-1">{inr(p.monthly_saving)}<span className="text-sm font-semibold text-[var(--ink-soft)]">/month</span></div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card p-6" data-testid="ef-action">
        {d && !d.goal_id ? (
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="font-semibold">No emergency fund goal yet</div>
              <div className="text-sm text-[var(--ink-soft)]">Create one and every rupee you add earns NugPoints.</div>
            </div>
            <button data-testid="ef-create-goal" onClick={createGoal} className="pill-btn btn-primary inline-flex items-center gap-2"><Plus size={16} /> Create Emergency Fund goal</button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <div className="font-semibold">Top up "{d?.goal_title}"</div>
              <div className="text-sm text-[var(--ink-soft)]">Contributions count toward your fund and earn NugPoints.</div>
            </div>
            <input data-testid="ef-contrib-input" className="input w-40" type="number" placeholder="₹ amount" value={amt} onChange={(e) => setAmt(e.target.value)} />
            <button data-testid="ef-contrib-btn" onClick={contribute} className="pill-btn btn-orange whitespace-nowrap">Add to fund →</button>
          </div>
        )}
      </div>
    </div>
  );
}
