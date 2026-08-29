import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { LOGO_URL } from "@/lib/api";
import BudgetAlertsBell from "@/components/BudgetAlertsBell";
import { LayoutDashboard, Receipt, PiggyBank, Target, MessageCircle, TrendingDown, GraduationCap, Calculator, LineChart, Gift, LogOut, Repeat } from "lucide-react";

const items = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true, tid: "nav-dashboard" },
  { to: "/app/expenses", label: "Expenses", icon: Receipt, tid: "nav-expenses" },
  { to: "/app/recurring", label: "Recurring", icon: Repeat, tid: "nav-recurring" },
  { to: "/app/budgets", label: "Budgets", icon: PiggyBank, tid: "nav-budgets" },
  { to: "/app/goals", label: "Goals", icon: Target, tid: "nav-goals" },
  { to: "/app/coach", label: "AI Coach", icon: MessageCircle, tid: "nav-coach" },
  { to: "/app/debts", label: "Debts", icon: TrendingDown, tid: "nav-debts" },
  { to: "/app/learn", label: "Learn", icon: GraduationCap, tid: "nav-learn" },
  { to: "/app/tax", label: "Tax", icon: Calculator, tid: "nav-tax" },
  { to: "/app/cashflow", label: "Cashflow", icon: LineChart, tid: "nav-cashflow" },
  { to: "/app/rewards", label: "NugPoints", icon: Gift, tid: "nav-rewards" },
];

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const doLogout = async () => { await logout(); nav("/"); };

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 shrink-0 border-r border-[var(--border)] bg-white sticky top-0 h-screen p-5 flex flex-col">
        <a href="/app" className="flex items-center gap-2 mb-8" data-testid="sidebar-logo">
          <img src={LOGO_URL} alt="Nugvio" className="h-10 w-auto" />
        </a>
        <nav className="flex flex-col gap-1">
          {items.map((it) => (
            <NavLink
              key={it.to}
              to={it.to}
              end={it.end}
              data-testid={it.tid}
              className={({ isActive }) =>
                `nav-link flex items-center gap-3 ${isActive ? "active" : ""}`
              }
            >
              <it.icon size={18} strokeWidth={1.7} />
              <span>{it.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto">
          <div className="card p-4">
            <div className="text-xs text-[var(--ink-soft)]">Signed in as</div>
            <div className="font-semibold truncate" data-testid="sidebar-user-name">{user?.name}</div>
            <div className="text-xs text-[var(--ink-soft)] truncate mb-3">{user?.email}</div>
            <button data-testid="logout-btn" onClick={doLogout} className="pill-btn btn-ghost w-full flex items-center justify-center gap-2 text-sm">
              <LogOut size={16} /> Sign out
            </button>
          </div>
        </div>
      </aside>
      <main className="flex-1 p-8 max-w-[1400px]">
        <div className="flex justify-end mb-2">
          <BudgetAlertsBell />
        </div>
        {children}
      </main>
    </div>
  );
}
