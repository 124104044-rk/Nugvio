import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { LOGO_URL } from "@/lib/api";
import BudgetAlertsBell from "@/components/BudgetAlertsBell";
import StreakCheckin from "@/components/StreakCheckin";
import { LayoutDashboard, Receipt, PiggyBank, Target, MessageCircle, TrendingDown, GraduationCap, Calculator, LineChart, Gift, LogOut, Repeat, TrendingUp, Sparkles, Landmark, ShieldCheck, CalendarRange } from "lucide-react";

const sections = [
  { label: "Overview", items: [
    { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true, tid: "nav-dashboard" },
    { to: "/app/actions", label: "Action Center", icon: Sparkles, tid: "nav-actions" },
  ]},
  { label: "Spend", items: [
    { to: "/app/expenses", label: "Expenses", icon: Receipt, tid: "nav-expenses" },
    { to: "/app/recurring", label: "Recurring", icon: Repeat, tid: "nav-recurring" },
    { to: "/app/budgets", label: "Budgets", icon: PiggyBank, tid: "nav-budgets" },
    { to: "/app/cashflow", label: "Cashflow", icon: LineChart, tid: "nav-cashflow" },
  ]},
  { label: "Wealth", items: [
    { to: "/app/investments", label: "Investments", icon: TrendingUp, tid: "nav-investments" },
    { to: "/app/networth", label: "Net Worth", icon: Landmark, tid: "nav-networth" },
    { to: "/app/goals", label: "Goals", icon: Target, tid: "nav-goals" },
    { to: "/app/emergency", label: "Emergency Fund", icon: ShieldCheck, tid: "nav-emergency" },
    { to: "/app/debts", label: "Debts", icon: TrendingDown, tid: "nav-debts" },
  ]},
  { label: "Grow", items: [
    { to: "/app/coach", label: "AI Coach", icon: MessageCircle, tid: "nav-coach" },
    { to: "/app/learn", label: "Learn", icon: GraduationCap, tid: "nav-learn" },
    { to: "/app/tax", label: "Tax", icon: Calculator, tid: "nav-tax" },
    { to: "/app/rewards", label: "NugPoints", icon: Gift, tid: "nav-rewards" },
    { to: "/app/recap", label: "Weekly Recap", icon: CalendarRange, tid: "nav-recap" },
  ]},
];

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const doLogout = async () => { await logout(); nav("/"); };

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 shrink-0 border-r border-[var(--border)] bg-white sticky top-0 h-screen p-5 flex flex-col">
        <a href="/app" className="flex items-center gap-2 mb-5" data-testid="sidebar-logo">
          <img src={LOGO_URL} alt="Nugvio" className="h-10 w-auto" />
        </a>
        <nav className="flex-1 overflow-y-auto pr-1 -mr-1">
          {sections.map((sec) => (
            <div key={sec.label} className="mb-3">
              <div className="text-[10px] uppercase tracking-[0.15em] text-[var(--ink-soft)] font-bold px-3 mb-1">{sec.label}</div>
              <div className="flex flex-col gap-0.5">
                {sec.items.map((it) => (
                  <NavLink
                    key={it.to}
                    to={it.to}
                    end={it.end}
                    data-testid={it.tid}
                    className={({ isActive }) =>
                      `nav-link flex items-center gap-3 text-sm ${isActive ? "active" : ""}`
                    }
                  >
                    <it.icon size={17} strokeWidth={1.7} />
                    <span>{it.label}</span>
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="mt-3">
          <div className="card p-3">
            <div className="text-xs text-[var(--ink-soft)]">Signed in as</div>
            <div className="font-semibold truncate text-sm" data-testid="sidebar-user-name">{user?.name}</div>
            <div className="text-xs text-[var(--ink-soft)] truncate mb-2">{user?.email}</div>
            <button data-testid="logout-btn" onClick={doLogout} className="pill-btn btn-ghost w-full flex items-center justify-center gap-2 text-xs py-1.5">
              <LogOut size={14} /> Sign out
            </button>
          </div>
        </div>
      </aside>
      <main className="flex-1 p-8 max-w-[1400px]">
        <div className="flex justify-end items-center gap-3 mb-2">
          <StreakCheckin />
          <BudgetAlertsBell />
        </div>
        {children}
      </main>
    </div>
  );
}
