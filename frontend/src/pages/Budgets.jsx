import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2, AlertTriangle } from "lucide-react";

const CATEGORIES = ["Food","Travel","Shopping","Bills","Healthcare","Entertainment","Rent","Investments","Other"];

export default function Budgets() {
  const [rows, setRows] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [cat, setCat] = useState("Food");
  const [limit, setLimit] = useState("");

  const load = async () => {
    const [b, a] = await Promise.all([api.get("/budgets"), api.get("/budget-alerts")]);
    setRows(b.data);
    setAlerts(a.data.alerts || []);
  };
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    if (!limit) return;
    await api.post("/budgets", { category: cat, monthly_limit: parseFloat(limit) });
    setLimit("");
    toast.success("Budget saved");
    load();
  };

  const del = async (c) => { await api.delete(`/budgets/${c}`); load(); };

  const barColor = (pct) => pct >= 100 ? '#F43F5E' : pct >= 80 ? '#F97316' : '#2563EB';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold">Budgets</h1>
        <p className="text-[var(--ink-soft)] mt-1">Set a ceiling per category. Nugvio will nudge you before you overshoot.</p>
      </div>

      {alerts.length > 0 && (
        <div className="card p-5 nudge-orange" data-testid="budget-alerts-inline">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle size={18} color="#F97316"/>
            <div className="font-semibold">{alerts.length} budget alert{alerts.length>1?'s':''} this month</div>
          </div>
          <div className="grid md:grid-cols-3 gap-3">
            {alerts.map(a => (
              <div key={a.id} className="p-3 rounded-xl bg-white border border-[var(--border)]" data-testid={`inline-alert-${a.category}`}>
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-sm">{a.category}</div>
                  <div className="text-xs font-bold" style={{color: a.level==='exceeded'?'var(--coral)':'var(--orange)'}}>{Math.round(a.pct)}%</div>
                </div>
                <div className="text-xs text-[var(--ink-soft)] mt-1">{a.message}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={add} className="card p-6 grid md:grid-cols-12 gap-3" data-testid="budget-form">
        <select data-testid="budget-category" className="input md:col-span-5" value={cat} onChange={e=>setCat(e.target.value)}>
          {CATEGORIES.map(c=><option key={c}>{c}</option>)}
        </select>
        <input data-testid="budget-limit" className="input md:col-span-5" type="number" step="0.01" placeholder="Monthly limit ₹" value={limit} onChange={e=>setLimit(e.target.value)} />
        <button data-testid="budget-submit" className="pill-btn btn-primary md:col-span-2 flex items-center justify-center gap-2"><Plus size={16}/> Save</button>
      </form>

      <div className="grid md:grid-cols-2 gap-4">
        {rows.map((b, i) => {
          const pct = Math.min(100, (b.spent / b.monthly_limit) * 100);
          return (
            <div key={b.category} className="card p-5 animate-slide" style={{animationDelay:`${i*40}ms`}} data-testid={`budget-card-${b.category}`}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold text-lg">{b.category}</div>
                  <div className="text-xs text-[var(--ink-soft)]">₹{Math.round(b.spent)} of ₹{Math.round(b.monthly_limit)}</div>
                </div>
                <button onClick={()=>del(b.category)} className="p-2 rounded-full hover:bg-slate-100"><Trash2 size={16} color="#F43F5E"/></button>
              </div>
              <div className="h-2 mt-3 rounded-full bg-slate-100">
                <div className="h-2 rounded-full" style={{width:`${pct}%`, background: barColor(pct)}}/>
              </div>
              <div className="text-xs mt-2" style={{color: barColor(pct)}}>
                {pct >= 100 ? "Overshoot — pause spending" : pct >= 80 ? "Almost there — cool it" : "On track"}
              </div>
            </div>
          );
        })}
        {rows.length===0 && <div className="card p-6 text-[var(--ink-soft)]">No budgets yet. Add one above.</div>}
      </div>
    </div>
  );
}
