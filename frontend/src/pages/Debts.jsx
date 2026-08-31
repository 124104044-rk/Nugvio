import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2, Zap, PartyPopper } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";

const inr = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`;

export default function Debts() {
  const [rows, setRows] = useState([]);
  const [name, setName] = useState("");
  const [bal, setBal] = useState("");
  const [apr, setApr] = useState("");
  const [minp, setMinp] = useState("");
  const [method, setMethod] = useState("avalanche");
  const [extra, setExtra] = useState(0);
  const [strategy, setStrategy] = useState(null);
  const [payAmt, setPayAmt] = useState({});
  const [impact, setImpact] = useState(null);

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

  const quickPay = async (d, amount) => {
    const amt = parseFloat(amount);
    if (!amt || amt <= 0) return;
    try {
      const { data } = await api.post(`/debts/${d.id}/pay`, { amount: amt });
      setPayAmt({ ...payAmt, [d.id]: "" });
      setImpact({ ...data, debt_name: d.name });
      if (data.paid_off) {
        toast.success(`🎉 '${d.name}' is fully paid off! +${data.earned_points} NugPoints`);
      } else {
        toast.success(`${inr(data.paid)} paid on ${d.name} — ${data.months_saved} mo & ${inr(data.interest_saved)} interest saved · +${data.earned_points} NugPoints`);
      }
      await loadRows();
      loadStrategy();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Payment failed");
    }
  };

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

      {impact && (
        <div className="card p-5 nudge-green animate-slide" data-testid="pay-impact-banner">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-white border border-[var(--border)]"><PartyPopper size={18} color="#16A34A"/></div>
            <div className="flex-1">
              <div className="font-semibold">
                {impact.paid_off
                  ? <>'{impact.debt_name}' fully paid off — incredible!</>
                  : <>{inr(impact.paid)} paid on '{impact.debt_name}'</>}
              </div>
              <div className="text-sm text-[var(--ink-soft)]">
                You just saved <b style={{color:'#16A34A'}}>{impact.months_saved} month{impact.months_saved===1?'':'s'}</b> and <b style={{color:'#16A34A'}}>{inr(impact.interest_saved)}</b> in future interest{impact.earned_points > 0 && <> · earned <b>+{impact.earned_points} NugPoints</b></>}.
              </div>
            </div>
            <button onClick={()=>setImpact(null)} className="text-xs font-semibold text-[var(--ink-soft)] hover:underline" data-testid="pay-impact-dismiss">Dismiss</button>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-5">
        <div className="card p-6" data-testid="debt-list">
          <div className="text-lg font-semibold mb-3">Your debts</div>
          {rows.map(d => (
            <div key={d.id} className="py-3 border-b border-[var(--border)]">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold">{d.name} {d.balance <= 0 && <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{background:'#DCFCE7', color:'#166534'}}>Paid off</span>}</div>
                  <div className="text-xs text-[var(--ink-soft)]">{inr(d.balance)} · {d.apr}% APR · min ₹{d.min_payment}</div>
                </div>
                <button onClick={()=>del(d.id)} data-testid={`debt-del-${d.id}`} className="p-2 rounded-full hover:bg-slate-100"><Trash2 size={16} color="#F43F5E"/></button>
              </div>
              {d.balance > 0 && (
                <div className="mt-2 flex items-center gap-1.5 flex-wrap" data-testid={`debt-quickpay-${d.id}`}>
                  <Zap size={13} color="#F97316"/>
                  {[500, 1000, 2000].map(a => (
                    <button key={a} data-testid={`debt-quick-${a}-${d.id}`} onClick={()=>quickPay(d, a)} className="pill-btn btn-ghost text-xs px-3 py-1">+{inr(a)}</button>
                  ))}
                  <input data-testid={`debt-pay-input-${d.id}`} className="input text-xs w-24 py-1" type="number" placeholder="₹ custom"
                    value={payAmt[d.id] || ""} onChange={e=>setPayAmt({...payAmt, [d.id]: e.target.value})}/>
                  <button data-testid={`debt-pay-btn-${d.id}`} onClick={()=>quickPay(d, payAmt[d.id])} className="pill-btn btn-orange text-xs px-3 py-1">Pay</button>
                </div>
              )}
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
