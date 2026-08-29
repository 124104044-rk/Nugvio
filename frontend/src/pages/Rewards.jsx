import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { Gift, Trophy, History } from "lucide-react";

const COLOR = { orange: 'var(--orange)', coral: 'var(--coral)', green: 'var(--green)', blue: 'var(--blue)' };

export default function Rewards() {
  const { user, refresh } = useAuth();
  const [state, setState] = useState({ points: 0, catalog: [], history: [] });

  const load = async () => setState((await api.get("/rewards")).data);
  useEffect(() => { load(); }, []);

  const redeem = async (id) => {
    try {
      await api.post(`/rewards/redeem/${id}`);
      toast.success("Redeemed! Voucher will be emailed.");
      load(); refresh();
    } catch (e) { toast.error(e.response?.data?.detail || "Not enough NugPoints"); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-4xl font-bold">NugPoints</h1>
          <p className="text-[var(--ink-soft)] mt-1">Earn by saving, budgeting, learning. Redeem for real stuff.</p>
        </div>
        <div className="card p-4 nudge-red flex items-center gap-3" data-testid="rewards-balance">
          <Trophy size={22} color="#F43F5E"/>
          <div>
            <div className="text-xs text-[var(--ink-soft)]">Balance</div>
            <div className="text-3xl font-extrabold">{user?.nug_points ?? state.points}</div>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-5" data-testid="rewards-catalog">
        {state.catalog.map(r => {
          const canAfford = (user?.nug_points ?? 0) >= r.points;
          return (
            <div key={r.id} className="card p-5">
              <div className="w-full h-24 rounded-xl flex items-center justify-center text-white text-2xl font-bold" style={{background: COLOR[r.color]}}>
                <Gift/>&nbsp;{r.brand}
              </div>
              <div className="text-lg font-semibold mt-3">{r.title}</div>
              <div className="text-sm mt-1" style={{color:'var(--coral)'}}><b>{r.points}</b> NugPoints</div>
              <button data-testid={`redeem-${r.id}`} onClick={()=>redeem(r.id)} disabled={!canAfford} className={`pill-btn ${canAfford?'btn-primary':'btn-ghost'} mt-4 w-full`}>
                {canAfford ? "Redeem" : `Need ${r.points - (user?.nug_points ?? 0)} more`}
              </button>
            </div>
          );
        })}
      </div>

      <div className="card p-6" data-testid="rewards-history">
        <div className="flex items-center gap-2 mb-3"><History size={18}/><div className="text-lg font-semibold">Activity</div></div>
        {state.history.length===0 && <div className="text-sm text-[var(--ink-soft)]">No activity yet. Save toward a goal to earn NugPoints.</div>}
        {state.history.map(h => (
          <div key={h.id} className="py-2 border-b border-[var(--border)] flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold">{h.note}</div>
              <div className="text-xs text-[var(--ink-soft)]">{new Date(h.at).toLocaleString()}</div>
            </div>
            <div className={`font-bold ${h.points >= 0 ? 'text-[var(--green)]' : 'text-[var(--coral)]'}`}>{h.points >= 0 ? '+' : ''}{h.points}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
