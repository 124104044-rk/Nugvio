import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2, Sparkles, Pencil, Search, X } from "lucide-react";
import { inr, sym } from "@/lib/currency";

const CATEGORIES = ["Food","Travel","Shopping","Bills","Healthcare","Entertainment","Rent","Investments","Other"];
const CAT_COLOR = {Food:'#F97316', Travel:'#2563EB', Shopping:'#F43F5E', Bills:'#0EA5E9', Healthcare:'#16A34A', Entertainment:'#A855F7', Rent:'#0F172A', Investments:'#16A34A', Income:'#16A34A', Other:'#64748B'};

export default function Expenses() {
  const [rows, setRows] = useState([]);
  const [desc, setDesc] = useState("");
  const [amt, setAmt] = useState("");
  const [cat, setCat] = useState("");
  const [type, setType] = useState("expense");
  const [busy, setBusy] = useState(false);
  const [aiHint, setAiHint] = useState(null);
  const [editing, setEditing] = useState(null);

  const [q, setQ] = useState("");
  const [fType, setFType] = useState("all");
  const [fCat, setFCat] = useState("");
  const [fFrom, setFFrom] = useState("");
  const [fTo, setFTo] = useState("");
  const debounce = useRef(null);

  const load = async (params = {}) => {
    const p = new URLSearchParams();
    if (params.q ?? q) p.set("q", params.q ?? q);
    const t = params.fType ?? fType;
    if (t !== "all") p.set("type", t);
    if (params.fCat ?? fCat) p.set("category", params.fCat ?? fCat);
    if (params.fFrom ?? fFrom) p.set("date_from", params.fFrom ?? fFrom);
    if (params.fTo ?? fTo) p.set("date_to", params.fTo ?? fTo);
    const { data } = await api.get(`/expenses?${p.toString()}`);
    setRows(data);
  };
  useEffect(() => { load(); }, []);

  const onSearch = (v) => {
    setQ(v);
    clearTimeout(debounce.current);
    debounce.current = setTimeout(() => load({ q: v }), 350);
  };
  const setFilter = (patch) => {
    if (patch.fType !== undefined) setFType(patch.fType);
    if (patch.fCat !== undefined) setFCat(patch.fCat);
    if (patch.fFrom !== undefined) setFFrom(patch.fFrom);
    if (patch.fTo !== undefined) setFTo(patch.fTo);
    load(patch);
  };
  const clearFilters = () => {
    setQ(""); setFType("all"); setFCat(""); setFFrom(""); setFTo("");
    load({ q: "", fType: "all", fCat: "", fFrom: "", fTo: "" });
  };

  const suggest = async (v) => {
    setDesc(v);
    setAiHint(null);
    if (type === "expense" && v.trim().length > 3) {
      try {
        const { data } = await api.post("/expenses/categorize", { description: v });
        setAiHint(data.category);
      } catch {}
    }
  };

  const startEdit = (r) => {
    setEditing(r);
    setDesc(r.description);
    setAmt(String(r.amount));
    setCat(r.category === "Income" ? "" : r.category);
    setType(r.type === "income" ? "income" : "expense");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const cancelEdit = () => { setEditing(null); setDesc(""); setAmt(""); setCat(""); setType("expense"); setAiHint(null); };

  const submit = async (e) => {
    e.preventDefault();
    if (!desc || !amt) return;
    setBusy(true);
    try {
      if (editing) {
        await api.patch(`/expenses/${editing.id}`, {
          description: desc, amount: parseFloat(amt), type,
          category: type === "income" ? "Income" : (cat || editing.category),
        });
        toast.success("Transaction updated");
        cancelEdit();
      } else {
        await api.post("/expenses", { description: desc, amount: parseFloat(amt), category: type === "income" ? "Income" : (cat || undefined), type });
        setDesc(""); setAmt(""); setCat(""); setAiHint(null);
        toast.success(type === "income" ? "Income added" : "Expense added");
      }
      load();
    } catch { toast.error("Could not save"); }
    finally { setBusy(false); }
  };

  const del = async (id) => {
    await api.delete(`/expenses/${id}`);
    load();
  };

  const hasFilters = q || fType !== "all" || fCat || fFrom || fTo;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold">Transactions</h1>
        <p className="text-[var(--ink-soft)] mt-1">Type it like you'd say it. AI figures out the rest.</p>
      </div>

      <form onSubmit={submit} className="card p-4 md:p-6" data-testid="expense-form">
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 text-sm text-[var(--ink-soft)]">
            <Sparkles size={14} color="#F97316"/>
            <span className="hidden sm:inline">{editing ? "Editing transaction" : 'Smart add — try "Zomato biryani 340"'}</span>
            <span className="sm:hidden">{editing ? "Editing" : "Smart add"}</span>
          </div>
          <div className="flex gap-1">
            <button type="button" data-testid="type-expense" onClick={()=>setType("expense")} className={`pill-btn text-xs px-3 py-1.5 ${type==="expense" ? "btn-primary" : "btn-ghost"}`}>Expense</button>
            <button type="button" data-testid="type-income" onClick={()=>setType("income")} className={`pill-btn text-xs px-3 py-1.5 ${type==="income" ? "btn-primary" : "btn-ghost"}`}>Income</button>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-12 gap-3">
          <input data-testid="expense-desc" className="input col-span-2 md:col-span-6" placeholder={type==="income" ? "Salary, freelance payment…" : "What did you spend on?"} value={desc} onChange={e=>suggest(e.target.value)} />
          <input data-testid="expense-amount" className="input md:col-span-2" type="number" step="0.01" placeholder={`${sym()} amount`} value={amt} onChange={e=>setAmt(e.target.value)} />
          {type === "expense" ? (
            <select data-testid="expense-category" className="input md:col-span-2" value={cat} onChange={e=>setCat(e.target.value)}>
              <option value="">{aiHint ? `AI: ${aiHint}` : "Auto (AI)"}</option>
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          ) : (
            <div className="input md:col-span-2 flex items-center text-sm text-[var(--ink-soft)]">Income</div>
          )}
          <button data-testid="expense-submit" disabled={busy} className="pill-btn btn-primary col-span-2 md:col-span-2 flex items-center justify-center gap-2">
            {editing ? <><Pencil size={15}/> Update</> : <><Plus size={16}/> Add</>}
          </button>
        </div>
        {editing && (
          <button type="button" data-testid="cancel-edit" onClick={cancelEdit} className="text-xs font-semibold text-[var(--ink-soft)] mt-2 hover:underline">Cancel editing</button>
        )}
      </form>

      <div className="card p-4" data-testid="filters-bar">
        <div className="flex flex-col md:flex-row gap-2 md:items-center">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ink-soft)]" />
            <input data-testid="tx-search" className="input pl-9" placeholder="Search transactions…" value={q} onChange={e=>onSearch(e.target.value)} />
          </div>
          <div className="flex gap-1">
            {["all","expense","income"].map(t => (
              <button key={t} data-testid={`filter-${t}`} onClick={()=>setFilter({ fType: t })} className={`pill-btn text-xs px-3 py-1.5 capitalize ${fType===t ? "btn-primary" : "btn-ghost"}`}>{t}</button>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap gap-2 mt-2 items-center">
          <select data-testid="filter-category" className="input !w-auto text-sm py-2 min-w-[130px]" value={fCat} onChange={e=>setFilter({ fCat: e.target.value })}>
            <option value="">All categories</option>
            {[...CATEGORIES, "Income"].map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <input data-testid="filter-from" className="input !w-auto text-sm py-2" type="date" value={fFrom} onChange={e=>setFilter({ fFrom: e.target.value })} />
          <span className="text-xs text-[var(--ink-soft)]">to</span>
          <input data-testid="filter-to" className="input !w-auto text-sm py-2" type="date" value={fTo} onChange={e=>setFilter({ fTo: e.target.value })} />
          {hasFilters && (
            <button data-testid="filter-clear" onClick={clearFilters} className="chip hover:opacity-70"><X size={12}/> Clear</button>
          )}
        </div>
      </div>

      <div className="card p-0 overflow-hidden" data-testid="expense-list">
        {rows.map((r, i) => {
          const isIncome = r.type === "income";
          return (
            <div key={r.id} className="flex items-center gap-3 p-4 border-b border-[var(--border)] hover:bg-slate-50 animate-slide" style={{animationDelay:`${Math.min(i,15)*20}ms`}}>
              <div className="flex-1 min-w-0">
                <div className="font-semibold truncate">{r.description}</div>
                <div className="text-xs text-[var(--ink-soft)] flex items-center gap-2 mt-0.5">
                  {new Date(r.date).toLocaleDateString()}
                  <span className="chip"><span className="tag-dot" style={{background: CAT_COLOR[r.category] || '#64748B'}}/>{r.category}</span>
                </div>
              </div>
              <div className="font-bold whitespace-nowrap" style={{ color: isIncome ? "#16A34A" : "inherit" }}>
                {isIncome ? "+" : ""}{inr(r.amount)}
              </div>
              <div className="flex">
                <button data-testid={`edit-exp-${r.id}`} onClick={()=>startEdit(r)} className="p-2 rounded-full hover:bg-slate-100"><Pencil size={15} color="#2563EB"/></button>
                <button data-testid={`del-exp-${r.id}`} onClick={()=>del(r.id)} className="p-2 rounded-full hover:bg-slate-100"><Trash2 size={15} color="#F43F5E"/></button>
              </div>
            </div>
          );
        })}
        {rows.length===0 && <div className="p-6 text-[var(--ink-soft)]">{hasFilters ? "No transactions match your filters." : "No transactions yet."}</div>}
      </div>
    </div>
  );
}
