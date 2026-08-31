import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { inr } from "@/lib/currency";
import { toast } from "sonner";
import { Plus, Trash2, Landmark, TrendingDown } from "lucide-react";

const KINDS = ["Bank", "Savings", "Cash", "Other"];

export default function NetWorth() {
  const [d, setD] = useState(null);
  const [form, setForm] = useState({ name: "", kind: "Bank", value: "" });

  const load = async () => setD((await api.get("/networth")).data);
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    if (!form.name || !form.value) return;
    await api.post("/assets", { name: form.name, kind: form.kind, value: parseFloat(form.value) });
    setForm({ name: "", kind: "Bank", value: "" });
    toast.success("Asset added");
    load();
  };
  const del = async (id) => { await api.delete(`/assets/${id}`); load(); };
  const edit = async (a) => {
    const v = window.prompt(`Update value for ${a.name}`, a.value);
    if (v === null || isNaN(parseFloat(v))) return;
    await api.patch(`/assets/${a.id}`, { value: parseFloat(v) });
    toast.success("Updated");
    load();
  };

  const assetsTotal = d?.assets?.total ?? 0;
  const liabTotal = d?.liabilities?.total ?? 0;
  const net = d?.net_worth ?? 0;
  const assetPct = assetsTotal + liabTotal > 0 ? (assetsTotal / (assetsTotal + liabTotal)) * 100 : 50;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold">Net Worth</h1>
        <p className="text-[var(--ink-soft)] mt-1">Assets − Liabilities. The one number that tells the whole story.</p>
      </div>

      <div className="card p-8" data-testid="networth-hero">
        <div className="text-xs uppercase tracking-wider text-[var(--ink-soft)] font-semibold">Your net worth</div>
        <div className="text-6xl font-extrabold mt-1" style={{ color: net >= 0 ? "#16A34A" : "#F43F5E" }} data-testid="networth-value">{inr(net)}</div>
        <div className="mt-5 h-4 rounded-full overflow-hidden flex">
          <div className="h-full" style={{ width: `${assetPct}%`, background: "#16A34A" }} />
          <div className="h-full" style={{ width: `${100 - assetPct}%`, background: "#F43F5E" }} />
        </div>
        <div className="flex justify-between text-sm mt-2">
          <span>Assets <b style={{ color: "#16A34A" }}>{inr(assetsTotal)}</b></span>
          <span>Liabilities <b style={{ color: "#F43F5E" }}>{inr(liabTotal)}</b></span>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-5">
        <div className="space-y-4">
          <div className="flex items-center gap-2"><Landmark size={18} color="#16A34A" /><h2 className="text-lg font-bold">Assets</h2></div>

          <form onSubmit={add} className="card p-4 grid grid-cols-12 gap-2" data-testid="asset-form">
            <input data-testid="asset-name" className="input col-span-5" placeholder="e.g. SBI Savings" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <select data-testid="asset-kind" className="input col-span-3" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>{KINDS.map((k) => <option key={k}>{k}</option>)}</select>
            <input data-testid="asset-value" className="input col-span-3" type="number" placeholder="₹" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} />
            <button data-testid="asset-submit" className="pill-btn btn-primary col-span-1 flex items-center justify-center"><Plus size={16} /></button>
          </form>

          <div className="card p-0 overflow-hidden" data-testid="assets-list">
            {(d?.assets?.manual ?? []).map((a) => (
              <div key={a.id} className="flex items-center justify-between p-4 border-b border-[var(--border)]">
                <div>
                  <div className="font-semibold">{a.name}</div>
                  <div className="text-xs text-[var(--ink-soft)]">{a.kind} · manual</div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="font-bold">{inr(a.value)}</div>
                  <button data-testid={`asset-edit-${a.id}`} onClick={() => edit(a)} className="pill-btn btn-ghost text-xs px-3 py-1">Update</button>
                  <button data-testid={`asset-del-${a.id}`} onClick={() => del(a.id)} className="p-2 rounded-full hover:bg-slate-100"><Trash2 size={15} color="#F43F5E" /></button>
                </div>
              </div>
            ))}
            {(d?.assets?.auto ?? []).map((a) => (
              <div key={a.id} className="flex items-center justify-between p-4 border-b border-[var(--border)] bg-slate-50" data-testid={`asset-auto-${a.id}`}>
                <div>
                  <div className="font-semibold">{a.name}</div>
                  <div className="text-xs text-[var(--ink-soft)]">{a.kind} · auto-tracked</div>
                </div>
                <div className="font-bold" style={{ color: "#16A34A" }}>{inr(a.value)}</div>
              </div>
            ))}
            {(d?.assets?.manual ?? []).length === 0 && (d?.assets?.auto ?? []).length === 0 && (
              <div className="p-6 text-[var(--ink-soft)]">No assets yet. Add your bank balance above.</div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2"><TrendingDown size={18} color="#F43F5E" /><h2 className="text-lg font-bold">Liabilities</h2></div>
          <div className="card p-4 text-sm text-[var(--ink-soft)]">Pulled automatically from your Debts — credit cards, loans, EMIs.</div>
          <div className="card p-0 overflow-hidden" data-testid="liabilities-list">
            {(d?.liabilities?.items ?? []).map((l) => (
              <div key={l.id} className="flex items-center justify-between p-4 border-b border-[var(--border)]">
                <div>
                  <div className="font-semibold">{l.name}</div>
                  {l.apr != null && <div className="text-xs text-[var(--ink-soft)]">{l.apr}% APR</div>}
                </div>
                <div className="font-bold" style={{ color: "#F43F5E" }}>−{inr(l.value)}</div>
              </div>
            ))}
            {(d?.liabilities?.items ?? []).length === 0 && <div className="p-6 text-[var(--ink-soft)]">No liabilities. Beautiful.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
