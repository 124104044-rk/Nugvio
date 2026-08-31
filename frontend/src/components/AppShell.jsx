import { useState } from "react";
import { NavLink, useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { LOGO_URL } from "@/lib/api";
import BudgetAlertsBell from "@/components/BudgetAlertsBell";
import StreakCheckin from "@/components/StreakCheckin";
import { LayoutDashboard, Receipt, PiggyBank, Target, MessageCircle, TrendingDown, GraduationCap, Calculator, LineChart, Gift, LogOut, Repeat, TrendingUp, Sparkles, Landmark, ShieldCheck, CalendarRange, Settings, MoreHorizontal, X } from "lucide-react";

const sections = [
  { label: "Overview", items: [
    { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true, tid: "nav-dashboard" },
    { to: "/app/actions", label: "Action Center", icon: Sparkles, tid: "nav-actions" },
  ]},
  { label: "Spend", items: [
    { to: "/app/expenses", label: "Transactions", icon: Receipt, tid: "nav-expenses" },
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
    { to: "/app/settings", label: "Settings", icon: Settings, tid: "nav-settings" },
  ]},
];

const bottomNav = [
  { to: "/app", label: "Home", icon: LayoutDashboard, end: true, tid: "bottomnav-home" },
  { to: "/app/actions", label: "Actions", icon: Sparkles, tid: "bottomnav-actions" },
  { to: "/app/expenses", label: "Spend", icon: Receipt, tid: "bottomnav-expenses" },
  { to: "/app/coach", label: "Coach", icon: MessageCircle, tid: "bottomnav-coach" },
];

const moreItems = sections.flatMap((s) => s.items).filter((it) => !bottomNav.some((b) => b.to === it.to));

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [moreOpen, setMoreOpen] = useState(false);
  const doLogout = async () => { await logout(); nav("/"); };

  return (
    <div className="min-h-screen flex">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-64 shrink-0 border-r border-[var(--border)] bg-[var(--surface)] sticky top-0 h-screen p-5 flex-col">
        <a href="/app" className="flex items-center gap-2 mb-5" data-testid="sidebar-logo">
          <img src={LOGO_URL} alt="NugVio" className="h-10 w-auto" />
        </a>
        <nav className="flex-1 overflow-y-auto pr-1 -mr-1">
          {sections.map((sec) => (
            <div key={sec.label} className="mb-3">
              <div className="text-[10px] uppercase tracking-[0.15em] text-[var(--ink-soft)] font-bold px-3 mb-1">{sec.label}</div>
              <div className="flex flex-col gap-0.5">
                {sec.items.map((it) => (
                  <NavLink key={it.to} to={it.to} end={it.end} data-testid={it.tid}
                    className={({ isActive }) => `nav-link flex items-center gap-3 text-sm ${isActive ? "active" : ""}`}>
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

      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile top header */}
        <header className="md:hidden sticky top-0 z-30 bg-[var(--surface)] border-b border-[var(--border)] px-4 py-2 flex items-center justify-between" data-testid="mobile-header">
          <Link to="/app"><img src={LOGO_URL} alt="NugVio" className="h-8 w-auto" /></Link>
          <div className="flex items-center gap-2">
            <StreakCheckin />
            <BudgetAlertsBell />
          </div>
        </header>

        <main className="flex-1 p-4 pb-28 md:p-8 md:pb-8 max-w-[1400px] w-full">
          <div className="hidden md:flex justify-end items-center gap-3 mb-2">
            <StreakCheckin />
            <BudgetAlertsBell />
          </div>
          {children}
        </main>
      </div>

      {/* Mobile bottom navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[var(--surface)] border-t border-[var(--border)] flex" data-testid="bottom-nav" style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
        {bottomNav.map((it) => (
          <NavLink key={it.to} to={it.to} end={it.end} data-testid={it.tid} onClick={() => setMoreOpen(false)}
            className={({ isActive }) => `flex-1 flex flex-col items-center gap-0.5 py-2 text-[10px] font-semibold ${isActive ? "text-[var(--blue)]" : "text-[var(--ink-soft)]"}`}>
            <it.icon size={20} strokeWidth={1.8} />
            {it.label}
          </NavLink>
        ))}
        <button data-testid="bottomnav-more" onClick={() => setMoreOpen(o => !o)}
          className={`flex-1 flex flex-col items-center gap-0.5 py-2 text-[10px] font-semibold ${moreOpen ? "text-[var(--blue)]" : "text-[var(--ink-soft)]"}`}>
          <MoreHorizontal size={20} strokeWidth={1.8} />
          More
        </button>
      </nav>

      {/* Mobile "More" sheet */}
      {moreOpen && (
        <div className="md:hidden fixed inset-0 z-30" onClick={() => setMoreOpen(false)}>
          <div className="absolute inset-0 bg-black/40" />
          <div className="absolute bottom-14 left-0 right-0 bg-[var(--surface)] rounded-t-3xl border-t border-[var(--border)] p-5 max-h-[70vh] overflow-y-auto" data-testid="more-sheet" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <div className="font-bold">All sections</div>
              <button onClick={() => setMoreOpen(false)} className="p-2 rounded-full hover:bg-slate-100" data-testid="more-sheet-close"><X size={18} /></button>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {moreItems.map((it) => (
                <NavLink key={it.to} to={it.to} end={it.end} data-testid={`more-${it.tid}`} onClick={() => setMoreOpen(false)}
                  className={({ isActive }) => `flex flex-col items-center gap-1.5 p-3 rounded-2xl border text-xs font-semibold text-center ${isActive ? "border-[var(--blue)] text-[var(--blue)]" : "border-[var(--border)] text-[var(--ink-soft)]"}`}>
                  <it.icon size={20} strokeWidth={1.7} />
                  {it.label}
                </NavLink>
              ))}
            </div>
            <button data-testid="mobile-logout" onClick={doLogout} className="pill-btn btn-ghost w-full mt-4 flex items-center justify-center gap-2 text-sm">
              <LogOut size={15} /> Sign out ({user?.name})
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
