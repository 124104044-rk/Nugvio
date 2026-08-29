import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2, Sparkles } from "lucide-react";

const CATEGORIES = ["Food","Travel","Shopping","Bills","Healthcare","Entertainment","Rent","Investments","Other"];
const CAT_COLOR = {Food:'#F97316', Travel:'#2563EB', Shopping:'#F43F5E', Bills:'#0EA5E9', Healthcare:'#16A34A', Entertainment:'#A855F7', Rent:'#0F172A', Investments:'#16A34A', Other:'#64748B'};

export default function Expenses() {
  const [rows, setRows] = useState([]);
  const [desc, setDesc] = useState("");
  const [amt, setAmt] = useState("");
  const [cat, setCat] = useState("");
  const [busy, setBusy] = useState(false);
  const [aiHint, setAiHint] = useState(null);

  const load = async () => {
    const { data } = await api.get("/expenses");
    setRows(data);
  };
  useEffect(() => { load(); }, []);

  const suggest = async (v) => {
    setDesc(v);
    setAiHint(null);
    if (v.trim().length > 3) {
      try {
        const { data } = await api.post("/expenses/categorize", { description: v });
        setAiHint(data.category);
      } catch {}
    }
  };

  const add = async (e) => {
    e.preventDefault();
    if (!desc || !amt) return;
    setBusy(true);
    try {
      await api.post("/expenses", { description: desc, amount: parseFloat(amt), category: cat || undefined });
      setDesc(""); setAmt(""); setCat(""); setAiHint(null);
      toast.success("Expense added");
      load();
    } catch (e2) { toast.error("Could not add"); }
    finally { setBusy(false); }
  };

  const del = async (id) => {
    await api.delete(`/expenses/${id}`);
    load();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold">Expenses</h1>
        <p className="text-[var(--ink-soft)] mt-1">Type it like you'd say it. AI figures out the rest.</p>
      </div>

      <form onSubmit={add} className="card p-6" data-testid="expense-form">
        <div className="flex items-center gap-2 mb-2 text-sm text-[var(--ink-soft)]">
          <Sparkles size={14} color="#F97316"/> Smart add — try "Zomato biryani 340"
        </div>
        <div className="grid md:grid-cols-12 gap-3">
          <input data-testid="expense-desc" className="input md:col-span-6" placeholder="What did you spend on?" value={desc} onChange={e=>suggest(e.target.value)} />
          <input data-testid="expense-amount" className="input md:col-span-2" type="number" step="0.01" placeholder="₹ amount" value={amt} onChange={e=>setAmt(e.target.value)} />
          <select data-testid="expense-category" className="input md:col-span-2" value={cat} onChange={e=>setCat(e.target.value)}>
            <option value="">{aiHint ? `AI: ${aiHint}` : "Auto (AI)"}</option>
            {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <button data-testid="expense-submit" disabled={busy} className="pill-btn btn-primary md:col-span-2 flex items-center justify-center gap-2">
            <Plus size={16}/> Add
          </button>
        </div>
      </form>

      <div className="card p-0 overflow-hidden" data-testid="expense-list">
        <div className="grid grid-cols-12 gap-2 p-4 text-xs uppercase tracking-wider text-[var(--ink-soft)] font-semibold border-b border-[var(--border)]">
          <div className="col-span-6">Description</div>
          <div className="col-span-3">Category</div>
          <div className="col-span-2 text-right">Amount</div>
          <div className="col-span-1"></div>
        </div>
        {rows.map((r, i) => (
          <div key={r.id} className="grid grid-cols-12 gap-2 p-4 items-center border-b border-[var(--border)] hover:bg-slate-50 animate-slide" style={{animationDelay:`${i*20}ms`}}>
            <div className="col-span-6">
              <div className="font-semibold">{r.description}</div>
              <div className="text-xs text-[var(--ink-soft)]">{new Date(r.date).toLocaleDateString()}</div>
            </div>
            <div className="col-span-3">
              <span className="chip"><span className="tag-dot" style={{background: CAT_COLOR[r.category] || '#64748B'}}/>{r.category}</span>
            </div>
            <div className="col-span-2 text-right font-bold">₹{Math.round(r.amount)}</div>
            <div className="col-span-1 text-right">
              <button data-testid={`del-exp-${r.id}`} onClick={()=>del(r.id)} className="p-2 rounded-full hover:bg-slate-100"><Trash2 size={16} color="#F43F5E"/></button>
            </div>
          </div>
        ))}
        {rows.length===0 && <div className="p-6 text-[var(--ink-soft)]">No expenses yet.</div>}
      </div>
    </div>
  );
}
