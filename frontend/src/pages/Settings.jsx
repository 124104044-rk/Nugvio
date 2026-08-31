import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import { CURRENCIES, getCurrency, setCurrencyLocal } from "@/lib/currency";
import { toast } from "sonner";
import { Sun, Moon, Monitor, LogOut, User, Bell, Palette } from "lucide-react";

function Toggle({ on, onClick, tid }) {
  return (
    <button type="button" data-testid={tid} onClick={onClick} aria-pressed={on}
      className="relative w-11 h-6 rounded-full transition-colors"
      style={{ background: on ? "var(--green)" : "var(--border)" }}>
      <span className="absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all" style={{ left: on ? "22px" : "2px" }} />
    </button>
  );
}

export default function Settings() {
  const { user, logout, setUser } = useAuth();
  const { theme, setTheme } = useTheme();
  const nav = useNavigate();
  const [name, setName] = useState(user?.name || "");
  const [currency, setCurrency] = useState(user?.currency || getCurrency());
  const prefs = user?.notif_prefs || {};
  const [np, setNp] = useState({
    risk_alerts: prefs.risk_alerts !== false,
    spending_alerts: prefs.spending_alerts !== false,
    goal_alerts: prefs.goal_alerts !== false,
  });

  const saveProfile = async () => {
    if (!name.trim()) return;
    const { data } = await api.patch("/me", { name: name.trim() });
    setUser(data);
    toast.success("Profile updated");
  };

  const saveCurrency = async (c) => {
    setCurrency(c);
    setCurrencyLocal(c);
    const { data } = await api.patch("/me", { currency: c });
    setUser(data);
    toast.success(`Currency set to ${c}`);
  };

  const togglePref = async (key) => {
    const next = { ...np, [key]: !np[key] };
    setNp(next);
    const { data } = await api.patch("/me", { notif_prefs: next });
    setUser(data);
  };

  const doLogout = async () => { await logout(); nav("/"); };

  const THEMES = [
    { id: "light", label: "Light", icon: Sun },
    { id: "dark", label: "Dark", icon: Moon },
    { id: "system", label: "System", icon: Monitor },
  ];

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-4xl font-bold">Settings</h1>
        <p className="text-[var(--ink-soft)] mt-1">Your profile, preferences and appearance.</p>
      </div>

      <div className="card p-6" data-testid="settings-profile">
        <div className="flex items-center gap-2 font-bold mb-4"><User size={17} /> Profile</div>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-semibold text-[var(--ink-soft)]">Name</label>
            <div className="flex gap-2 mt-1">
              <input data-testid="settings-name" className="input" value={name} onChange={(e) => setName(e.target.value)} />
              <button data-testid="settings-save-name" onClick={saveProfile} className="pill-btn btn-primary text-sm whitespace-nowrap">Save</button>
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-[var(--ink-soft)]">Email</label>
            <input data-testid="settings-email" className="input mt-1 opacity-70" value={user?.email || ""} readOnly />
          </div>
        </div>
      </div>

      <div className="card p-6" data-testid="settings-appearance">
        <div className="flex items-center gap-2 font-bold mb-4"><Palette size={17} /> Appearance</div>
        <div className="flex gap-2 flex-wrap">
          {THEMES.map((t) => (
            <button key={t.id} data-testid={`theme-${t.id}`} onClick={() => setTheme(t.id)}
              className={`pill-btn text-sm inline-flex items-center gap-2 ${theme === t.id ? "btn-primary" : "btn-ghost"}`}>
              <t.icon size={15} /> {t.label}
            </button>
          ))}
        </div>
        <div className="mt-5">
          <label className="text-xs font-semibold text-[var(--ink-soft)]">Currency</label>
          <select data-testid="settings-currency" className="input mt-1 max-w-[200px]" value={currency} onChange={(e) => saveCurrency(e.target.value)}>
            {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <div className="text-xs text-[var(--ink-soft)] mt-1">Changes the currency symbol shown across the app. Amounts are not converted.</div>
        </div>
      </div>

      <div className="card p-6" data-testid="settings-notifications">
        <div className="flex items-center gap-2 font-bold mb-4"><Bell size={17} /> Notifications</div>
        <div className="space-y-4">
          {[
            ["risk_alerts", "Risk alerts", "Low-balance and budget-breach warnings"],
            ["spending_alerts", "Spending alerts", "Heads-up when a budget crosses 80%"],
            ["goal_alerts", "Goal wins", "Celebrations when you're ahead on goals"],
          ].map(([key, label, sub]) => (
            <div key={key} className="flex items-center justify-between gap-4">
              <div>
                <div className="font-semibold text-sm">{label}</div>
                <div className="text-xs text-[var(--ink-soft)]">{sub}</div>
              </div>
              <Toggle on={np[key]} onClick={() => togglePref(key)} tid={`toggle-${key}`} />
            </div>
          ))}
        </div>
      </div>

      <div className="card p-6" data-testid="settings-account">
        <button data-testid="settings-logout" onClick={doLogout} className="pill-btn btn-ghost inline-flex items-center gap-2 text-sm">
          <LogOut size={15} /> Log out
        </button>
      </div>
    </div>
  );
}
