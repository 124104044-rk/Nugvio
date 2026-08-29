import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import { Bell, AlertTriangle, TriangleAlert, Info } from "lucide-react";
import { Link } from "react-router-dom";

const LEVEL = {
  exceeded: { icon: TriangleAlert, cls: "nudge-red", color: "#F43F5E", label: "Exceeded" },
  warning:  { icon: AlertTriangle, cls: "nudge-orange", color: "#F97316", label: "Warning" },
  info:     { icon: Info, cls: "nudge-blue", color: "#2563EB", label: "Heads up" },
};

export default function BudgetAlertsBell() {
  const [data, setData] = useState({ alerts: [], count: 0, critical: 0 });
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const load = async () => {
    try { setData((await api.get("/budget-alerts")).data); } catch {}
  };
  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button data-testid="alerts-bell" onClick={()=>setOpen(o=>!o)} className="p-2 rounded-full hover:bg-slate-100 relative">
        <Bell size={20}/>
        {data.critical > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold flex items-center justify-center text-white" style={{background:'var(--coral)'}} data-testid="alerts-badge">
            {data.critical}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-96 card p-4 z-40 bg-white shadow-xl" data-testid="alerts-panel" style={{boxShadow: '0 20px 40px -12px rgba(15,23,42,0.25)'}}>
          <div className="flex items-center justify-between mb-3">
            <div className="font-semibold">Budget Alerts</div>
            <Link to="/app/budgets" className="text-xs font-semibold text-[var(--blue)]" onClick={()=>setOpen(false)}>Manage →</Link>
          </div>
          {data.alerts.length === 0 && (
            <div className="text-sm text-[var(--ink-soft)] py-4 text-center">All good. No budgets at risk this month.</div>
          )}
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {data.alerts.map(a => {
              const L = LEVEL[a.level] || LEVEL.info;
              return (
                <div key={a.id} className={`p-3 rounded-xl ${L.cls}`} data-testid={`alert-${a.category}`}>
                  <div className="flex items-start gap-2">
                    <L.icon size={16} color={L.color} className="mt-0.5"/>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-sm">{a.category}</div>
                        <div className="text-xs font-bold" style={{color: L.color}}>{Math.round(a.pct)}%</div>
                      </div>
                      <div className="text-xs text-[var(--ink-soft)] mt-0.5">{a.message}</div>
                      <div className="mt-2 h-1.5 rounded-full bg-white border border-[var(--border)]">
                        <div className="h-full rounded-full" style={{width:`${Math.min(100, a.pct)}%`, background: L.color}}/>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
