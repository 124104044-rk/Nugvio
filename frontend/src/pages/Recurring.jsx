import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2, Play, Pause, Zap, CalendarDays } from "lucide-react";

const CATEGORIES = ["Food","Travel","Shopping","Bills","Healthcare","Entertainment","Rent","Investments","Other"];
const CAT_COLOR = {Food:'#F97316', Travel:'#2563EB', Shopping:'#F43F5E', Bills:'#0EA5E9', Healthcare:'#16A34A', Entertainment:'#A855F7', Rent:'#0F172A', Investments:'#16A34A', Other:'#64748B'};

export default function Recurring() {
  const [data, setData] = useState({ items: [], monthly_committed: 0 });
  const [name, setName] = useState("");
  const [amt, setAmt] = useState("");
  const [cat, setCat] = useState("Bills");
  const [freq, setFreq] = useState("monthly");
  const [nd, setNd] = useState(new Date(Date.now()+86400000).toISOString().slice(0,10));

  const load = async () => setData((await api.get("/recurring")).data);
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    if (!name || !amt) return;
    await api.post("/recurring", { name, amount: parseFloat(amt), category: cat, frequency: freq, next_due: nd });
    setName(""); setAmt("");
    toast.success("Recurring added");
    load();
  };
  const toggle = async (r) => { await api.patch(`/recurring/${r.id}`, { active: !r.active }); load(); };
  const del = async (id) => { await api.delete(`/recurring/${id}`); load(); };
  const post = async (id) => {
    const { data } = await api.post(`/recurring/${id}/post`);
    toast.success(`Posted ₹${Math.round(data.expense.amount)} · next due ${data.next_due}`);
    load();
  };
  const runAll = async () => {
    const { data } = await api.post("/recurring/run-due");
    if (data.posted) toast.success(`${data.posted} recurring transaction(s) posted`);
    else toast.info("Nothing due right now");
    load();
  };

  const dueCount = data.items.filter(i => i.is_due).length;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-4xl font-bold">Recurring</h1>
          <p className="text-[var(--ink-soft)] mt-1">Subscriptions, rent, SIPs. Track the money that leaves without asking.</p>
        </div>
        <button data-testid="recurring-run-all" onClick={runAll} className="pill-btn btn-primary inline-flex items-center gap-2"><Zap size={16}/> Post due now {dueCount ? `(${dueCount})` : ""}</button>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="card p-5" data-testid="recurring-stat-total">
          <div className="text-xs text-[var(--ink-soft)]">Total active</div>
          <div className="text-3xl font-bold">{data.items.filter(i=>i.active).length}</div>
        </div>
        <div className="card p-5" data-testid="recurring-stat-monthly">
          <div className="text-xs text-[var(--ink-soft)]">Monthly commitment</div>
          <div className="text-3xl font-bold" style={{color:'var(--coral)'}}>₹{Math.round(data.monthly_committed).toLocaleString('en-IN')}</div>
        </div>
        <div className={`card p-5 ${dueCount ? 'nudge-orange' : 'nudge-green'}`} data-testid="recurring-stat-due">
          <div className="text-xs text-[var(--ink-soft)]">Due today or overdue</div>
          <div className="text-3xl font-bold">{dueCount}</div>
        </div>
      </div>

      <form onSubmit={add} className="card p-6 grid md:grid-cols-12 gap-3" data-testid="recurring-form">
        <input data-testid="rec-name" className="input md:col-span-3" placeholder="Netflix, Rent, SIP…" value={name} onChange={e=>setName(e.target.value)} />
        <input data-testid="rec-amount" className="input md:col-span-2" type="number" step="0.01" placeholder="₹ amount" value={amt} onChange={e=>setAmt(e.target.value)} />
        <select data-testid="rec-category" className="input md:col-span-2" value={cat} onChange={e=>setCat(e.target.value)}>{CATEGORIES.map(c=><option key={c}>{c}</option>)}</select>
        <select data-testid="rec-frequency" className="input md:col-span-2" value={freq} onChange={e=>setFreq(e.target.value)}>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </select>
        <input data-testid="rec-next-due" className="input md:col-span-2" type="date" value={nd} onChange={e=>setNd(e.target.value)} />
        <button data-testid="rec-submit" className="pill-btn btn-primary md:col-span-1 flex items-center justify-center gap-2"><Plus size={16}/></button>
      </form>

      <div className="card p-0 overflow-hidden" data-testid="recurring-list">
        <div className="grid grid-cols-12 gap-2 p-4 text-xs uppercase tracking-wider text-[var(--ink-soft)] font-semibold border-b border-[var(--border)]">
          <div className="col-span-3">Name</div>
          <div className="col-span-2">Category</div>
          <div className="col-span-2">Frequency</div>
          <div className="col-span-2">Next due</div>
          <div className="col-span-1 text-right">Amount</div>
          <div className="col-span-2 text-right">Actions</div>
        </div>
        {data.items.map((r, i) => (
          <div key={r.id} className={`grid grid-cols-12 gap-2 p-4 items-center border-b border-[var(--border)] ${r.is_due ? 'bg-orange-50' : ''} ${!r.active ? 'opacity-60' : ''} animate-slide`} style={{animationDelay:`${i*20}ms`}}>
            <div className="col-span-3">
              <div className="font-semibold">{r.name}</div>
              {r.is_due && <div className="text-xs font-semibold" style={{color:'var(--orange)'}}>Due now</div>}
            </div>
            <div className="col-span-2">
              <span className="chip"><span className="tag-dot" style={{background: CAT_COLOR[r.category] || '#64748B'}}/>{r.category}</span>
            </div>
            <div className="col-span-2 text-sm capitalize flex items-center gap-1"><CalendarDays size={14}/> {r.frequency}</div>
            <div className="col-span-2 text-sm">{r.next_due}</div>
            <div className="col-span-1 text-right font-bold">₹{Math.round(r.amount)}</div>
            <div className="col-span-2 flex justify-end gap-1">
              <button data-testid={`rec-post-${r.id}`} onClick={()=>post(r.id)} disabled={!r.active} className="p-2 rounded-full hover:bg-slate-100" title="Post now"><Play size={16} color="#2563EB"/></button>
              <button data-testid={`rec-toggle-${r.id}`} onClick={()=>toggle(r)} className="p-2 rounded-full hover:bg-slate-100" title={r.active?"Pause":"Resume"}>
                {r.active ? <Pause size={16}/> : <Play size={16} color="#16A34A"/>}
              </button>
              <button data-testid={`rec-del-${r.id}`} onClick={()=>del(r.id)} className="p-2 rounded-full hover:bg-slate-100"><Trash2 size={16} color="#F43F5E"/></button>
            </div>
          </div>
        ))}
        {data.items.length===0 && <div className="p-6 text-[var(--ink-soft)]">No recurring transactions yet.</div>}
      </div>
    </div>
  );
}
