import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2, Target, Zap } from "lucide-react";
import { useAuth } from "@/lib/auth";

const inr = (n) => `₹${Math.round(n).toLocaleString("en-IN")}`;
const STATUS = {
  ahead: { label: "Ahead of schedule", bg: "#DCFCE7", color: "#166534" },
  on_track: { label: "On track", bg: "#DBEAFE", color: "#1E40AF" },
  behind: { label: "Behind schedule", bg: "#FFEDD5", color: "#9A3412" },
};

export default function Goals() {
  const { refresh } = useAuth();
  const [rows, setRows] = useState([]);
  const [sips, setSips] = useState([]);
  const [title, setTitle] = useState("");
  const [tgt, setTgt] = useState("");
  const [date, setDate] = useState("");
  const [contribution, setContribution] = useState({});
  const [pilot, setPilot] = useState({});

  const load = async () => {
    const { data } = await api.get("/goals-autopilot");
    setRows(data.goals); setSips(data.sips);
  };
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    if (!title || !tgt || !date) return;
    await api.post("/goals", { title, target_amount: parseFloat(tgt), target_date: date });
    setTitle(""); setTgt(""); setDate("");
    toast.success("Goal added");
    load();
  };

  const contribute = async (id) => {
    const amt = parseFloat(contribution[id] || 0);
    if (!amt) return;
    const { data } = await api.post(`/goals/${id}/contribute`, { amount: amt });
    setContribution({ ...contribution, [id]: "" });
    toast.success(`+${data.earned_points} NugPoints earned`);
    load(); refresh();
  };

  const del = async (id) => { await api.delete(`/goals/${id}`); load(); };

  const saveAutopilot = async (g) => {
    const p = pilot[g.id] || {};
    await api.patch(`/goals/${g.id}/autopilot`, {
      monthly_commit: p.commit !== undefined ? (parseFloat(p.commit) || 0) : g.monthly_commit,
      linked_sip_id: p.sip !== undefined ? p.sip : (g.linked_sip_id || ""),
    });
    toast.success("Autopilot updated");
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-4xl font-bold">Goals</h1>
          <p className="text-[var(--ink-soft)] mt-1">Pick your dream. Autopilot tells you if you'll make it.</p>
        </div>
        <div className="font-hand text-2xl" style={{color:'var(--coral)'}}>save = earn points ★</div>
      </div>

      <form onSubmit={add} className="card p-6 grid md:grid-cols-12 gap-3" data-testid="goal-form">
        <input data-testid="goal-title" className="input md:col-span-5" placeholder="MacBook, Bali trip, MBA…" value={title} onChange={e=>setTitle(e.target.value)} />
        <input data-testid="goal-target" className="input md:col-span-3" type="number" step="1" placeholder="Target ₹" value={tgt} onChange={e=>setTgt(e.target.value)} />
        <input data-testid="goal-date" className="input md:col-span-2" type="date" value={date} onChange={e=>setDate(e.target.value)} />
        <button data-testid="goal-submit" className="pill-btn btn-primary md:col-span-2 flex items-center justify-center gap-2"><Plus size={16}/> Add</button>
      </form>

      <div className="grid md:grid-cols-2 gap-5">
        {rows.map((g, i) => {
          const pct = Math.min(100, (g.saved_amount / g.target_amount) * 100);
          const S = STATUS[g.status] || STATUS.on_track;
          const p = pilot[g.id] || {};
          const shortfall = g.committed_monthly < g.required_monthly;
          return (
            <div key={g.id} className="card p-6 animate-slide" style={{animationDelay:`${i*40}ms`}} data-testid={`goal-card-${g.id}`}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <div className="chip"><Target size={12}/> Goal</div>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{background: S.bg, color: S.color}} data-testid={`goal-status-${g.id}`}>{S.label}</span>
                  </div>
                  <div className="text-2xl font-bold mt-2">{g.title}</div>
                  <div className="text-sm text-[var(--ink-soft)]">by {new Date(g.target_date).toLocaleDateString()}</div>
                </div>
                <button onClick={()=>del(g.id)} data-testid={`goal-del-${g.id}`} className="p-2 rounded-full hover:bg-slate-100"><Trash2 size={16} color="#F43F5E"/></button>
              </div>

              <div className="mt-4 h-3 rounded-full bg-slate-100">
                <div className="h-3 rounded-full" style={{width:`${pct}%`, background: pct>=70?'#16A34A':'#2563EB'}}/>
              </div>
              <div className="text-sm mt-2">{inr(g.saved_amount)} / {inr(g.target_amount)} <span className="text-[var(--ink-soft)]">({Math.round(pct)}%)</span></div>

              <div className={`mt-3 card p-3 text-sm ${g.status === "behind" ? "nudge-orange" : "nudge-blue"}`} data-testid={`goal-pace-${g.id}`}>
                {g.status === "behind"
                  ? <>⏰ Behind by ~<b>{Math.abs(g.months_off)} months</b>. Save <b>{inr(g.required_monthly)}/month</b> to still hit it.</>
                  : g.status === "ahead"
                  ? <>🎉 <b>{inr(g.variance)}</b> ahead of pace. Needs <b>{inr(g.required_monthly)}/month</b> from here.</>
                  : <>💡 Save <b>{inr(g.required_monthly)}/month</b> to hit this in time.</>}
              </div>

              <div className="mt-3 card p-3" data-testid={`goal-autopilot-${g.id}`}>
                <div className="flex items-center gap-1.5 text-xs uppercase tracking-wider font-bold text-[var(--ink-soft)]"><Zap size={12}/> Autopilot</div>
                <div className="grid grid-cols-12 gap-2 mt-2">
                  <input data-testid={`goal-commit-${g.id}`} className="input col-span-4 text-sm" type="number" placeholder="₹/month"
                    value={p.commit !== undefined ? p.commit : (g.monthly_commit || "")}
                    onChange={e=>setPilot({...pilot, [g.id]: {...p, commit: e.target.value}})}/>
                  <select data-testid={`goal-sip-${g.id}`} className="input col-span-5 text-sm"
                    value={p.sip !== undefined ? p.sip : (g.linked_sip_id || "")}
                    onChange={e=>setPilot({...pilot, [g.id]: {...p, sip: e.target.value}})}>
                    <option value="">No SIP linked</option>
                    {sips.map(s=><option key={s.id} value={s.id}>{s.name} ({inr(s.monthly_amount)})</option>)}
                  </select>
                  <button data-testid={`goal-autopilot-save-${g.id}`} onClick={()=>saveAutopilot(g)} className="pill-btn btn-ghost col-span-3 text-xs">Save</button>
                </div>
                <div className="text-xs mt-2" data-testid={`goal-committed-${g.id}`}>
                  Committed: <b>{inr(g.committed_monthly)}/mo</b> · Needed: <b>{inr(g.required_monthly)}/mo</b>
                  {g.committed_monthly > 0 && (
                    <span className="font-semibold" style={{color: shortfall ? "#F97316" : "#16A34A"}}>
                      {" "}· {shortfall ? `add ${inr(g.required_monthly - g.committed_monthly)}/mo more` : "fully funded"}
                    </span>
                  )}
                  {g.projected_delay_months != null && g.projected_delay_months > 0.5 && (
                    <span className="font-semibold" style={{color:"#F43F5E"}}> · projected {Math.round(g.projected_delay_months)} mo late</span>
                  )}
                </div>
              </div>

              <div className="flex gap-2 mt-4">
                <input data-testid={`contrib-input-${g.id}`} className="input" placeholder="₹ contribute" type="number" value={contribution[g.id]||""} onChange={e=>setContribution({...contribution, [g.id]: e.target.value})}/>
                <button data-testid={`contrib-btn-${g.id}`} onClick={()=>contribute(g.id)} className="pill-btn btn-orange whitespace-nowrap">Save →</button>
              </div>
            </div>
          );
        })}
        {rows.length===0 && <div className="card p-6 text-[var(--ink-soft)]">No goals yet. Add one above.</div>}
      </div>
    </div>
  );
}
