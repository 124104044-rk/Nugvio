import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import { Toaster } from "sonner";

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

function Protected({ children }) {
  const { user } = useAuth();
  if (user === null) return <div className="p-10 text-[var(--ink-soft)]">Loading…</div>;
  if (user === false) return <Navigate to="/login" replace />;
  return <AppShell>{children}</AppShell>;
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <Toaster position="top-right" richColors />
        <BrowserRouter>
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
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
