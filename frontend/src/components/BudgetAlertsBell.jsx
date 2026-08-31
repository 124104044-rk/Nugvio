import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import { Bell, ShieldAlert, AlertTriangle, PartyPopper } from "lucide-react";
import { Link } from "react-router-dom";

const LEVEL = {
  risk: { icon: ShieldAlert, cls: "nudge-red", color: "#F43F5E", label: "Risk" },
  spending: { icon: AlertTriangle, cls: "nudge-orange", color: "#F97316", label: "Spending" },
  goal: { icon: PartyPopper, cls: "nudge-green", color: "#16A34A", label: "Win" },
};

export default function BudgetAlertsBell() {
  const [data, setData] = useState({ alerts: [], count: 0, critical: 0 });
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const load = async () => {
    try { setData((await api.get("/alerts")).data); } catch {}
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
            <div className="font-semibold">Smart Alerts</div>
            <Link to="/app/actions" className="text-xs font-semibold text-[var(--blue)]" onClick={()=>setOpen(false)}>Action Center →</Link>
          </div>
          {data.alerts.length === 0 && (
            <div className="text-sm text-[var(--ink-soft)] py-4 text-center">All quiet. No risks, no breaches.</div>
          )}
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {data.alerts.map(a => {
              const L = LEVEL[a.level] || LEVEL.spending;
              return (
                <Link to={a.route || "/app/actions"} key={a.id} onClick={()=>setOpen(false)} className={`block p-3 rounded-xl ${L.cls}`} data-testid={`alert-${a.id}`}>
                  <div className="flex items-start gap-2">
                    <L.icon size={16} color={L.color} className="mt-0.5"/>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-sm">{a.title}</div>
                        <div className="text-[10px] font-bold uppercase tracking-wider" style={{color: L.color}}>{L.label}</div>
                      </div>
                      <div className="text-xs text-[var(--ink-soft)] mt-0.5">{a.message}</div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
