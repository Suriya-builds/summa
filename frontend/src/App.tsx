import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import Layout from "./components/Layout";
import { Loading } from "./components/ui";
import Landing from "./pages/Landing";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Transactions = lazy(() => import("./pages/Transactions"));
const Budget = lazy(() => import("./pages/Budget"));
const Shield = lazy(() => import("./pages/Shield"));
const Ask = lazy(() => import("./pages/Ask"));
const ImportPage = lazy(() => import("./pages/Import"));
const SettingsPage = lazy(() => import("./pages/Settings"));

function Protected() {
  const { user, loading } = useAuth();
  if (loading) return <Loading label="Starting" />;
  if (!user) return <Navigate to="/" replace />;
  return <Layout />;
}

function Home() {
  const { user, loading } = useAuth();
  if (loading) return <Loading label="Starting" />;
  return user ? <Navigate to="/dashboard" replace /> : <Landing />;
}

export default function App() {
  return (
    <AuthProvider>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route element={<Protected />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/budget" element={<Budget />} />
            <Route path="/shield" element={<Shield />} />
            <Route path="/ask" element={<Ask />} />
            <Route path="/import" element={<ImportPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AuthProvider>
  );
}
