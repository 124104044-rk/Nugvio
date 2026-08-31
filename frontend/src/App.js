import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import { Toaster } from "sonner";
import AuthCallback from "@/components/AuthCallback";

import Landing from "@/pages/Landing";
import AuthPage from "@/pages/Auth";
import AppShell from "@/components/AppShell";
import Dashboard from "@/pages/Dashboard";
import Expenses from "@/pages/Expenses";
import Recurring from "@/pages/Recurring";
import Budgets from "@/pages/Budgets";
import Goals from "@/pages/Goals";
import Coach from "@/pages/Coach";
import Debts from "@/pages/Debts";
import Learn from "@/pages/Learn";
import Tax from "@/pages/Tax";
import Cashflow from "@/pages/Cashflow";
import Rewards from "@/pages/Rewards";
import Investments from "@/pages/Investments";
import ActionCenter from "@/pages/ActionCenter";
import NetWorth from "@/pages/NetWorth";
import Emergency from "@/pages/Emergency";
import Recap from "@/pages/Recap";

function Protected({ children }) {
  const { user } = useAuth();
  if (user === null) return <div className="p-10 text-[var(--ink-soft)]">Loading…</div>;
  if (user === false) return <Navigate to="/login" replace />;
  return <AppShell>{children}</AppShell>;
}

function AppRoutes() {
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const location = useLocation(); // read hash from here, not window.location.hash (not reactive)
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<AuthPage mode="login" />} />
            <Route path="/signup" element={<AuthPage mode="signup" />} />
            <Route path="/app" element={<Protected><Dashboard /></Protected>} />
            <Route path="/app/expenses" element={<Protected><Expenses /></Protected>} />
            <Route path="/app/recurring" element={<Protected><Recurring /></Protected>} />
            <Route path="/app/budgets" element={<Protected><Budgets /></Protected>} />
            <Route path="/app/goals" element={<Protected><Goals /></Protected>} />
            <Route path="/app/coach" element={<Protected><Coach /></Protected>} />
            <Route path="/app/debts" element={<Protected><Debts /></Protected>} />
            <Route path="/app/learn" element={<Protected><Learn /></Protected>} />
            <Route path="/app/tax" element={<Protected><Tax /></Protected>} />
            <Route path="/app/cashflow" element={<Protected><Cashflow /></Protected>} />
            <Route path="/app/rewards" element={<Protected><Rewards /></Protected>} />
            <Route path="/app/investments" element={<Protected><Investments /></Protected>} />
            <Route path="/app/actions" element={<Protected><ActionCenter /></Protected>} />
            <Route path="/app/networth" element={<Protected><NetWorth /></Protected>} />
            <Route path="/app/emergency" element={<Protected><Emergency /></Protected>} />
            <Route path="/app/recap" element={<Protected><Recap /></Protected>} />
            <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <Toaster position="top-right" richColors />
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
