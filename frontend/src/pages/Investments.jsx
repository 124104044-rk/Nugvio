import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2, Play, Pause, TrendingUp, TrendingDown, Wallet, PieChart } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";

const KINDS = ["MF", "Stock", "Gold", "FD", "Bond", "Crypto"];
const KIND_COLOR = { MF: "#2563EB", Stock: "#F97316", Gold: "#EAB308", FD: "#16A34A", Bond: "#0EA5E9", Crypto: "#A855F7" };
const inr = (n) => `₹${Math.round(n).toLocaleString("en-IN")}`;

export default function Investments() {
  const [summary, setSummary] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [sips, setSips] = useState([]);
  const [proj, setProj] = useState(null);
  const [tab, setTab] = useState("holdings");

  const [hForm, setHForm] = useState({ name: "", kind: "MF", units: "", avg_price: "", current_price: "" });
  const [sForm, setSForm] = useState({ name: "", monthly_amount: "", start_date: new Date().toISOString().slice(0, 10), expected_return: "12" });

  const load = async () => {
    const [s, h, sp, p] = await Promise.all([
      api.get("/investments/summary"),
      api.get("/investments/holdings"),
      api.get("/investments/sips"),
      api.get("/investments/projection"),
    ]);
    setSummary(s.data); setHoldings(h.data); setSips(sp.data); setProj(p.data);
  };
  useEffect(() => { load(); }, []);

  const addHolding = async (e) => {
    e.preventDefault();
    if (!hForm.name || !hForm.units || !hForm.avg_price || !hForm.current_price) return;
    await api.post("/investments/holdings", {
      name: hForm.name, kind: hForm.kind,
      units: parseFloat(hForm.units), avg_price: parseFloat(hForm.avg_price), current_price: parseFloat(hForm.current_price),
    });
    setHForm({ name: "", kind: "MF", units: "", avg_price: "", current_price: "" });
    toast.success("Holding added");
    load();
  };

  const addSip = async (e) => {
    e.preventDefault();
    if (!sForm.name || !sForm.monthly_amount) return;
    await api.post("/investments/sips", {
      name: sForm.name, monthly_amount: parseFloat(sForm.monthly_amount),
      start_date: sForm.start_date, expected_return: parseFloat(sForm.expected_return || "12"),
    });
    setSForm({ name: "", monthly_amount: "", start_date: new Date().toISOString().slice(0, 10), expected_return: "12" });
    toast.success("SIP added");
    load();
  };

  const delHolding = async (id) => { await api.delete(`/investments/holdings/${id}`); load(); };
  const delSip = async (id) => { await api.delete(`/investments/sips/${id}`); load(); };
  const toggleSip = async (s) => { await api.patch(`/investments/sips/${s.id}`, { active: !s.active }); load(); };
  const updatePrice = async (h) => {
    const v = window.prompt(`Update current price for ${h.name}`, h.current_price);
    if (v === null || isNaN(parseFloat(v))) return;
    await api.patch(`/investments/holdings/${h.id}`, { current_price: parseFloat(v) });
    toast.success("Price updated");
    load();
  };

  const gainPos = (summary?.gain ?? 0) >= 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold">Investments</h1>
        <p className="text-[var(--ink-soft)] mt-1">Your SIPs and portfolio — wealth alongside your spending.</p>
      </div>

      <div className="grid md:grid-cols-4 gap-4">
        <div className="card p-5" data-testid="invest-stat-invested">
          <div className="text-xs text-[var(--ink-soft)] flex items-center gap-1"><Wallet size={14} /> Invested</div>
          <div className="text-3xl font-bold">{inr(summary?.invested ?? 0)}</div>
        </div>
        <div className="card p-5" data-testid="invest-stat-current">
          <div className="text-xs text-[var(--ink-soft)]">Current value</div>
          <div className="text-3xl font-bold">{inr(summary?.current_value ?? 0)}</div>
        </div>
        <div className={`card p-5 ${gainPos ? "nudge-green" : "nudge-orange"}`} data-testid="invest-stat-gain">
          <div className="text-xs text-[var(--ink-soft)] flex items-center gap-1">
            {gainPos ? <TrendingUp size={14} /> : <TrendingDown size={14} />} Total gain
          </div>
          <div className="text-3xl font-bold" style={{ color: gainPos ? "var(--green, #16A34A)" : "var(--coral, #F43F5E)" }}>
            {gainPos ? "+" : ""}{inr(summary?.gain ?? 0)} <span className="text-base font-semibold">({summary?.gain_pct ?? 0}%)</span>
          </div>
        </div>
        <div className="card p-5" data-testid="invest-stat-sip">
          <div className="text-xs text-[var(--ink-soft)]">Monthly SIP</div>
          <div className="text-3xl font-bold">{inr(summary?.monthly_sip ?? 0)}</div>
          <div className="text-xs text-[var(--ink-soft)]">{summary?.sips_count ?? 0} active SIP{(summary?.sips_count ?? 0) === 1 ? "" : "s"}</div>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <div className="card p-6 lg:col-span-2" data-testid="invest-projection">
          <div className="flex items-end justify-between mb-2">
            <div>
              <h2 className="text-lg font-bold">SIP wealth projection</h2>
              <p className="text-xs text-[var(--ink-soft)]">{inr(proj?.monthly_sip ?? 0)}/mo at {proj?.avg_return_pct ?? 0}% avg return · 10 years</p>
            </div>
            <div className="text-right">
              <div className="text-xs text-[var(--ink-soft)]">Projected value</div>
              <div className="text-2xl font-bold" style={{ color: "#16A34A" }}>{inr(proj?.final_value ?? 0)}</div>
            </div>
          </div>
          <div className="h-56">
            <ResponsiveContainer>
              <AreaChart data={proj?.series ?? []}>
                <defs>
                  <linearGradient id="gv" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#16A34A" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#16A34A" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="year" tick={{ fontSize: 11 }} tickFormatter={(y) => `Y${y}`} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${Math.round(v / 100000)}L`} width={36} />
                <Tooltip formatter={(v, n) => [inr(v), n === "value" ? "Value" : "Invested"]} labelFormatter={(y) => `Year ${y}`} />
                <Area type="monotone" dataKey="invested" stroke="#94A3B8" strokeDasharray="4 4" fill="none" />
                <Area type="monotone" dataKey="value" stroke="#16A34A" strokeWidth={2} fill="url(#gv)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-6" data-testid="invest-allocation">
          <h2 className="text-lg font-bold mb-3 flex items-center gap-2"><PieChart size={18} /> Allocation</h2>
          <div className="space-y-3">
            {(summary?.allocation ?? []).map((a) => (
              <div key={a.kind}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-semibold">{a.kind}</span>
                  <span className="text-[var(--ink-soft)]">{inr(a.value)} · {a.pct}%</span>
                </div>
                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${a.pct}%`, background: KIND_COLOR[a.kind] || "#64748B" }} />
                </div>
              </div>
            ))}
            {(summary?.allocation ?? []).length === 0 && <div className="text-sm text-[var(--ink-soft)]">Add holdings to see allocation.</div>}
          </div>
          {summary?.best && (
            <div className="mt-4 pt-4 border-t border-[var(--border)] text-sm space-y-1">
              <div className="flex justify-between"><span className="text-[var(--ink-soft)]">Best</span><span className="font-semibold" style={{ color: "#16A34A" }}>{summary.best.name} +{summary.best.pct}%</span></div>
              {summary.worst && <div className="flex justify-between"><span className="text-[var(--ink-soft)]">Worst</span><span className="font-semibold" style={{ color: "#F43F5E" }}>{summary.worst.name} {summary.worst.pct}%</span></div>}
            </div>
          )}
        </div>
      </div>

      <div className="flex gap-2">
        <button data-testid="invest-tab-holdings" onClick={() => setTab("holdings")} className={`pill-btn ${tab === "holdings" ? "btn-primary" : "btn-ghost"}`}>Portfolio ({holdings.length})</button>
        <button data-testid="invest-tab-sips" onClick={() => setTab("sips")} className={`pill-btn ${tab === "sips" ? "btn-primary" : "btn-ghost"}`}>SIPs ({sips.length})</button>
      </div>

      {tab === "holdings" && (
        <>
          <form onSubmit={addHolding} className="card p-6 grid md:grid-cols-12 gap-3" data-testid="holding-form">
            <input data-testid="holding-name" className="input md:col-span-3" placeholder="Fund / stock name" value={hForm.name} onChange={(e) => setHForm({ ...hForm, name: e.target.value })} />
            <select data-testid="holding-kind" className="input md:col-span-2" value={hForm.kind} onChange={(e) => setHForm({ ...hForm, kind: e.target.value })}>{KINDS.map((k) => <option key={k}>{k}</option>)}</select>
            <input data-testid="holding-units" className="input md:col-span-2" type="number" step="0.001" placeholder="Units" value={hForm.units} onChange={(e) => setHForm({ ...hForm, units: e.target.value })} />
            <input data-testid="holding-avg-price" className="input md:col-span-2" type="number" step="0.01" placeholder="Avg buy ₹" value={hForm.avg_price} onChange={(e) => setHForm({ ...hForm, avg_price: e.target.value })} />
            <input data-testid="holding-current-price" className="input md:col-span-2" type="number" step="0.01" placeholder="Current ₹" value={hForm.current_price} onChange={(e) => setHForm({ ...hForm, current_price: e.target.value })} />
            <button data-testid="holding-submit" className="pill-btn btn-primary md:col-span-1 flex items-center justify-center"><Plus size={16} /></button>
          </form>

          <div className="card p-0 overflow-hidden" data-testid="holdings-list">
            <div className="grid grid-cols-12 gap-2 p-4 text-xs uppercase tracking-wider text-[var(--ink-soft)] font-semibold border-b border-[var(--border)]">
              <div className="col-span-3">Name</div>
              <div className="col-span-1">Kind</div>
              <div className="col-span-2 text-right">Invested</div>
              <div className="col-span-2 text-right">Current</div>
              <div className="col-span-2 text-right">Gain</div>
              <div className="col-span-2 text-right">Actions</div>
            </div>
            {holdings.map((h, i) => (
              <div key={h.id} className="grid grid-cols-12 gap-2 p-4 items-center border-b border-[var(--border)] animate-slide" style={{ animationDelay: `${i * 20}ms` }}>
                <div className="col-span-3">
                  <div className="font-semibold">{h.name}</div>
                  <div className="text-xs text-[var(--ink-soft)]">{h.units} units @ ₹{h.avg_price}</div>
                </div>
                <div className="col-span-1"><span className="chip"><span className="tag-dot" style={{ background: KIND_COLOR[h.kind] || "#64748B" }} />{h.kind}</span></div>
                <div className="col-span-2 text-right font-semibold">{inr(h.invested)}</div>
                <div className="col-span-2 text-right font-semibold">{inr(h.current)}</div>
                <div className="col-span-2 text-right font-bold" style={{ color: h.gain >= 0 ? "#16A34A" : "#F43F5E" }}>
                  {h.gain >= 0 ? "+" : ""}{inr(h.gain)} <span className="text-xs font-semibold">({h.gain_pct}%)</span>
                </div>
                <div className="col-span-2 flex justify-end gap-1">
                  <button data-testid={`holding-price-${h.id}`} onClick={() => updatePrice(h)} className="pill-btn btn-ghost text-xs px-3 py-1">Update ₹</button>
                  <button data-testid={`holding-del-${h.id}`} onClick={() => delHolding(h.id)} className="p-2 rounded-full hover:bg-slate-100"><Trash2 size={16} color="#F43F5E" /></button>
                </div>
              </div>
            ))}
            {holdings.length === 0 && <div className="p-6 text-[var(--ink-soft)]">No holdings yet. Add your first investment above.</div>}
          </div>
        </>
      )}

      {tab === "sips" && (
        <>
          <form onSubmit={addSip} className="card p-6 grid md:grid-cols-12 gap-3" data-testid="sip-form">
            <input data-testid="sip-name" className="input md:col-span-4" placeholder="SIP name (e.g. Nifty 50 Index)" value={sForm.name} onChange={(e) => setSForm({ ...sForm, name: e.target.value })} />
            <input data-testid="sip-amount" className="input md:col-span-2" type="number" step="1" placeholder="₹/month" value={sForm.monthly_amount} onChange={(e) => setSForm({ ...sForm, monthly_amount: e.target.value })} />
            <input data-testid="sip-start" className="input md:col-span-2" type="date" value={sForm.start_date} onChange={(e) => setSForm({ ...sForm, start_date: e.target.value })} />
            <input data-testid="sip-return" className="input md:col-span-3" type="number" step="0.5" placeholder="Expected return %" value={sForm.expected_return} onChange={(e) => setSForm({ ...sForm, expected_return: e.target.value })} />
            <button data-testid="sip-submit" className="pill-btn btn-primary md:col-span-1 flex items-center justify-center"><Plus size={16} /></button>
          </form>

          <div className="card p-0 overflow-hidden" data-testid="sips-list">
            <div className="grid grid-cols-12 gap-2 p-4 text-xs uppercase tracking-wider text-[var(--ink-soft)] font-semibold border-b border-[var(--border)]">
              <div className="col-span-4">SIP</div>
              <div className="col-span-2 text-right">Monthly</div>
              <div className="col-span-2 text-right">Invested so far</div>
              <div className="col-span-2 text-right">Expected return</div>
              <div className="col-span-2 text-right">Actions</div>
            </div>
            {sips.map((s, i) => (
              <div key={s.id} className={`grid grid-cols-12 gap-2 p-4 items-center border-b border-[var(--border)] ${!s.active ? "opacity-60" : ""} animate-slide`} style={{ animationDelay: `${i * 20}ms` }}>
                <div className="col-span-4">
                  <div className="font-semibold">{s.name}</div>
                  <div className="text-xs text-[var(--ink-soft)]">Since {s.start_date} · {s.months_run} months</div>
                </div>
                <div className="col-span-2 text-right font-bold">{inr(s.monthly_amount)}</div>
                <div className="col-span-2 text-right font-semibold">{inr(s.invested_so_far)}</div>
                <div className="col-span-2 text-right">{s.expected_return}%</div>
                <div className="col-span-2 flex justify-end gap-1">
                  <button data-testid={`sip-toggle-${s.id}`} onClick={() => toggleSip(s)} className="p-2 rounded-full hover:bg-slate-100" title={s.active ? "Pause" : "Resume"}>
                    {s.active ? <Pause size={16} /> : <Play size={16} color="#16A34A" />}
                  </button>
                  <button data-testid={`sip-del-${s.id}`} onClick={() => delSip(s.id)} className="p-2 rounded-full hover:bg-slate-100"><Trash2 size={16} color="#F43F5E" /></button>
                </div>
              </div>
            ))}
            {sips.length === 0 && <div className="p-6 text-[var(--ink-soft)]">No SIPs yet. Add one above to see projections.</div>}
          </div>
        </>
      )}
    </div>
  );
}
