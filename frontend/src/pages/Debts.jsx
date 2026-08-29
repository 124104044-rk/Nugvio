import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";

export default function Debts() {
  const [rows, setRows] = useState([]);
  const [name, setName] = useState("");
  const [bal, setBal] = useState("");
  const [apr, setApr] = useState("");
  const [minp, setMinp] = useState("");
  const [method, setMethod] = useState("avalanche");
  const [extra, setExtra] = useState(0);
  const [strategy, setStrategy] = useState(null);

  const loadRows = async () => setRows((await api.get("/debts")).data);
  const loadStrategy = async () => {
    const { data } = await api.get(`/debts/strategy?method=${method}&extra_payment=${extra}`);
    setStrategy(data);
  };
  useEffect(() => { loadRows(); }, []);
  useEffect(() => { loadStrategy(); }, [method, extra, rows.length]);

  const add = async (e) => {
    e.preventDefault();
    if (!name || !bal || !apr || !minp) return;
    await api.post("/debts", { name, balance: parseFloat(bal), apr: parseFloat(apr), min_payment: parseFloat(minp) });
    setName(""); setBal(""); setApr(""); setMinp("");
    toast.success("Debt added");
    loadRows();
  };
  const del = async (id) => { await api.delete(`/debts/${id}`); loadRows(); };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold">Debt Optimizer</h1>
        <p className="text-[var(--ink-soft)] mt-1">Kill high-interest debt first. Or knock small ones for motivation. Pick your fighter.</p>
      </div>

      <form onSubmit={add} className="card p-6 grid md:grid-cols-12 gap-3" data-testid="debt-form">
        <input data-testid="debt-name" className="input md:col-span-4" placeholder="e.g. HDFC Credit Card" value={name} onChange={e=>setName(e.target.value)} />
        <input data-testid="debt-balance" className="input md:col-span-2" type="number" placeholder="Balance ₹" value={bal} onChange={e=>setBal(e.target.value)} />
        <input data-testid="debt-apr" className="input md:col-span-2" type="number" step="0.1" placeholder="APR %" value={apr} onChange={e=>setApr(e.target.value)} />
        <input data-testid="debt-min" className="input md:col-span-2" type="number" placeholder="Min pay ₹" value={minp} onChange={e=>setMinp(e.target.value)} />
        <button data-testid="debt-submit" className="pill-btn btn-primary md:col-span-2 flex items-center justify-center gap-2"><Plus size={16}/> Add</button>
      </form>

      <div className="grid md:grid-cols-2 gap-5">
        <div className="card p-6" data-testid="debt-list">
          <div className="text-lg font-semibold mb-3">Your debts</div>
          {rows.map(d => (
            <div key={d.id} className="py-3 border-b border-[var(--border)] flex items-center justify-between">
              <div>
                <div className="font-semibold">{d.name}</div>
                <div className="text-xs text-[var(--ink-soft)]">₹{Math.round(d.balance).toLocaleString('en-IN')} · {d.apr}% APR · min ₹{d.min_payment}</div>
              </div>
              <button onClick={()=>del(d.id)} className="p-2 rounded-full hover:bg-slate-100"><Trash2 size={16} color="#F43F5E"/></button>
            </div>
          ))}
          {rows.length===0 && <div className="text-sm text-[var(--ink-soft)]">No debts. Cool.</div>}
        </div>

        <div className="card p-6" data-testid="debt-strategy">
          <div className="flex items-center justify-between mb-3">
            <div className="text-lg font-semibold">Payoff plan</div>
            <div className="flex gap-2">
              <button data-testid="method-avalanche" onClick={()=>setMethod('avalanche')} className={`pill-btn text-sm ${method==='avalanche'?'btn-primary':'btn-ghost'}`}>Avalanche</button>
              <button data-testid="method-snowball" onClick={()=>setMethod('snowball')} className={`pill-btn text-sm ${method==='snowball'?'btn-primary':'btn-ghost'}`}>Snowball</button>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 mb-3">
            <div className="card p-3">
              <div className="text-xs text-[var(--ink-soft)]">Payoff time</div>
              <div className="text-2xl font-bold">{strategy?.months ?? '–'}<span className="text-sm font-normal"> mo</span></div>
            </div>
            <div className="card p-3">
              <div className="text-xs text-[var(--ink-soft)]">Total interest</div>
              <div className="text-2xl font-bold" style={{color:'#F43F5E'}}>₹{Math.round(strategy?.total_interest ?? 0).toLocaleString('en-IN')}</div>
            </div>
            <div className="card p-3">
              <div className="text-xs text-[var(--ink-soft)]">Order</div>
              <div className="text-xs mt-1">{(strategy?.order || []).join(' → ') || '–'}</div>
            </div>
          </div>
          <div>
            <label className="text-xs text-[var(--ink-soft)]">Extra monthly payment: <b>₹{extra}</b></label>
            <input data-testid="extra-slider" type="range" min="0" max="10000" step="500" value={extra} onChange={e=>setExtra(parseInt(e.target.value))} className="w-full"/>
          </div>
          <div className="h-40 mt-3">
            <ResponsiveContainer>
              <LineChart data={strategy?.schedule || []}>
                <XAxis dataKey="month" hide/>
                <YAxis hide/>
                <Tooltip formatter={(v)=>`₹${Math.round(v).toLocaleString('en-IN')}`} labelFormatter={(l)=>`Month ${l}`}/>
                <Line type="monotone" dataKey="remaining_total" stroke="#F97316" strokeWidth={2.5} dot={false}/>
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
