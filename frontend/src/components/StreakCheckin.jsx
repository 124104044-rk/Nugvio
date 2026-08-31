import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { toast } from "sonner";
import { Flame, ShieldCheck } from "lucide-react";

export default function StreakCheckin() {
  const { refresh } = useAuth();
  const [st, setSt] = useState(null);

  const load = async () => { try { setSt((await api.get("/checkin/status")).data); } catch {} };
  useEffect(() => { load(); }, []);

  const checkin = async () => {
    try {
      const { data } = await api.post("/checkin");
      let msg = `Day ${data.streak_days} streak! +${data.points_earned} NugPoints`;
      if (data.milestone_bonus) msg += ` (incl. +${data.milestone_bonus} weekly bonus)`;
      if (data.saver_earned) msg += " · Streak-saver pass earned";
      if (data.saver_used) msg += " · Saver pass protected your streak";
      toast.success(msg);
      load(); refresh?.();
    } catch {
      toast.info("Already checked in today");
      load();
    }
  };

  if (!st) return null;
  return (
    <div className="flex items-center gap-2">
      {st.streak_savers > 0 && (
        <span className="chip" data-testid="streak-savers" title="Streak-saver passes — one protects a single missed day">
          <ShieldCheck size={13} color="#16A34A" /> <b>{st.streak_savers}</b>
        </span>
      )}
      {st.checked_in_today ? (
        <span className="chip" data-testid="streak-chip">
          <Flame size={14} color="#F97316" /> <b>{st.streak_days}</b> day streak
        </span>
      ) : (
        <button data-testid="checkin-btn" onClick={checkin} className="pill-btn btn-orange text-sm inline-flex items-center gap-1.5">
          <Flame size={15} /> Check in · +10
        </button>
      )}
    </div>
  );
}
