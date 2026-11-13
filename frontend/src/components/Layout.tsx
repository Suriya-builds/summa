import { LayoutDashboard, ListOrdered, LogOut, MessageSquareText, PiggyBank, Settings, ShieldAlert, Upload } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/ask", label: "Ask Summa", icon: MessageSquareText },
  { to: "/transactions", label: "Transactions", icon: ListOrdered },
  { to: "/budget", label: "Budget", icon: PiggyBank },
  { to: "/shield", label: "Scam Shield", icon: ShieldAlert },
  { to: "/import", label: "Import", icon: Upload },
  { to: "/settings", label: "Settings", icon: Settings },
];
const MOBILE = NAV.filter((n) => ["/dashboard", "/ask", "/transactions", "/budget", "/shield"].includes(n.to));

export function Logo({ light = false }: { light?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <svg viewBox="0 0 64 64" className="h-8 w-8" aria-hidden>
        <rect width="64" height="64" rx="14" fill={light ? "#ffffff" : "#111a2b"} />
        <path d="M42 18H22l12 14-12 14h20" fill="none" stroke="#10b37c" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className={`text-lg font-bold tracking-tight ${light ? "text-ink-900" : "text-white"}`}>Summa</span>
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const onLogout = async () => { await logout(); navigate("/"); };

  return (
    <div className="min-h-screen lg:flex">
      <aside className="hidden w-64 shrink-0 flex-col bg-ink-900 px-4 py-6 lg:flex lg:sticky lg:top-0 lg:h-screen">
        <div className="px-2"><Logo /></div>
        <nav className="mt-8 flex flex-1 flex-col gap-1" aria-label="Main">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${isActive ? "bg-white/10 text-white" : "text-ink-300 hover:bg-white/5 hover:text-white"}`}>
              <Icon className="h-[18px] w-[18px]" aria-hidden /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="rounded-xl bg-white/5 p-3">
          <div className="truncate text-sm font-semibold text-white">{user?.name}</div>
          <div className="truncate text-xs text-ink-400">{user?.is_demo ? "Demo account · synthetic data" : user?.email}</div>
          <button onClick={onLogout} className="mt-3 flex items-center gap-2 text-xs font-medium text-ink-300 hover:text-white">
            <LogOut className="h-3.5 w-3.5" /> Log out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between bg-ink-900 px-4 py-3 lg:hidden">
          <Logo />
          <div className="flex items-center gap-1">
            <NavLink to="/import" className="rounded-lg p-2 text-ink-300 hover:text-white" aria-label="Import"><Upload className="h-5 w-5" /></NavLink>
            <NavLink to="/settings" className="rounded-lg p-2 text-ink-300 hover:text-white" aria-label="Settings"><Settings className="h-5 w-5" /></NavLink>
          </div>
        </header>
        {user?.is_demo && (
          <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900">
            You are exploring a demo account filled with synthetic SMS. It is deleted after 24 hours.
          </div>
        )}
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-28 pt-6 sm:px-6 lg:px-8 lg:pb-12 lg:pt-8">
          <Outlet />
        </main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-ink-100 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden" aria-label="Main">
        {MOBILE.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) =>
            `flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium ${isActive ? "text-brand-700" : "text-ink-500"}`}>
            <Icon className="h-5 w-5" aria-hidden /> {label.replace("Ask Summa", "Ask").replace("Scam Shield", "Shield").replace("Transactions", "Activity")}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
