import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2, Target } from "lucide-react";
import { useAuth } from "@/lib/auth";

export default function Goals() {
  const { refresh } = useAuth();
  const [rows, setRows] = useState([]);
  const [title, setTitle] = useState("");
  const [tgt, setTgt] = useState("");
  const [date, setDate] = useState("");
  const [contribution, setContribution] = useState({});

  const load = async () => setRows((await api.get("/goals")).data);
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

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-4xl font-bold">Goals</h1>
          <p className="text-[var(--ink-soft)] mt-1">Pick your dream. We'll do the math.</p>
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
          const remaining = Math.max(0, g.target_amount - g.saved_amount);
          const daysLeft = Math.max(1, Math.ceil((new Date(g.target_date) - new Date()) / 86400000));
          const monthlyNeed = Math.ceil((remaining / daysLeft) * 30);
          return (
            <div key={g.id} className="card p-6 animate-slide" style={{animationDelay:`${i*40}ms`}} data-testid={`goal-card-${g.id}`}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="chip"><Target size={12}/> Goal</div>
                  <div className="text-2xl font-bold mt-2">{g.title}</div>
                  <div className="text-sm text-[var(--ink-soft)]">by {new Date(g.target_date).toLocaleDateString()}</div>
                </div>
                <button onClick={()=>del(g.id)} className="p-2 rounded-full hover:bg-slate-100"><Trash2 size={16} color="#F43F5E"/></button>
              </div>
              <div className="mt-4 h-3 rounded-full bg-slate-100">
                <div className="h-3 rounded-full" style={{width:`${pct}%`, background: pct>=70?'#16A34A':'#2563EB'}}/>
              </div>
              <div className="text-sm mt-2">₹{Math.round(g.saved_amount)} / ₹{Math.round(g.target_amount)} <span className="text-[var(--ink-soft)]">({Math.round(pct)}%)</span></div>
              <div className="mt-3 nudge-blue card p-3 text-sm">
                💡 Save <b>₹{monthlyNeed.toLocaleString('en-IN')}/month</b> to hit this in time.
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
