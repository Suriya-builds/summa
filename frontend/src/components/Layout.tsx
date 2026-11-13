import { LogOut, Settings, Upload } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const NAV = [
  { to: "/dashboard", label: "Dashboard", short: "Home" },
  { to: "/ask", label: "Ask Summa", short: "Ask" },
  { to: "/transactions", label: "Transactions", short: "Ledger" },
  { to: "/budget", label: "Budget", short: "Budget" },
  { to: "/shield", label: "Scam Shield", short: "Shield" },
  { to: "/import", label: "Import", short: "Import" },
  { to: "/settings", label: "Settings", short: "Settings" },
];
const MOBILE = NAV.slice(0, 5);

export function Logo({ size = "md" }: { size?: "md" | "lg" }) {
  const box = size === "lg" ? "h-11 w-11 text-3xl" : "h-9 w-9 text-2xl";
  return (
    <div className="flex items-center gap-2.5">
      <span className={`flex ${box} items-center justify-center bg-ink-900 font-display font-semibold leading-none text-white`} style={{ borderRadius: 2 }} aria-hidden>Σ</span>
      <span className={`font-display font-semibold italic tracking-tight text-ink-900 ${size === "lg" ? "text-3xl" : "text-2xl"}`}>Summa</span>
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const onLogout = async () => { await logout(); navigate("/"); };

  return (
    <div className="min-h-screen lg:flex">
      {/* Sidebar: the index page of a passbook */}
      <aside className="hidden w-60 shrink-0 flex-col border-r-2 border-ink-900 bg-ink-100 lg:sticky lg:top-0 lg:flex lg:h-screen">
        <div className="border-b-2 border-ink-900 px-5 py-5"><Logo /><div className="kicker mt-2">Money passbook</div></div>
        <nav className="flex flex-1 flex-col py-3" aria-label="Main">
          {NAV.map(({ to, label }, i) => (
            <NavLink key={to} to={to} className={({ isActive }) =>
              `group flex items-baseline gap-3 border-b border-dashed border-ink-900/25 px-5 py-3 transition ${isActive ? "bg-ink-900 text-white" : "text-ink-800 hover:bg-ink-200"}`}>
              {({ isActive }) => (<>
                <span className={`font-mono text-[11px] ${isActive ? "text-brand-200" : "text-ink-400"}`}>{String(i + 1).padStart(2, "0")}</span>
                <span className="font-display text-[17px] font-medium">{label}</span>
              </>)}
            </NavLink>
          ))}
        </nav>
        <div className="border-t-2 border-ink-900 px-5 py-4">
          <div className="kicker">Account holder</div>
          <div className="mt-1 truncate font-display text-lg font-medium leading-tight">{user?.name}</div>
          <div className="truncate font-mono text-[11px] text-ink-500">{user?.is_demo ? "DEMO · SYNTHETIC DATA" : user?.email}</div>
          <button onClick={onLogout} className="mt-3 flex items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-wider text-ink-700 underline decoration-dashed underline-offset-4 hover:text-red-700">
            <LogOut className="h-3.5 w-3.5" /> Log out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b-2 border-ink-900 bg-ink-100 px-4 py-2.5 lg:hidden">
          <Logo />
          <div className="flex items-center gap-1">
            <NavLink to="/import" className="p-2 text-ink-800" aria-label="Import"><Upload className="h-5 w-5" /></NavLink>
            <NavLink to="/settings" className="p-2 text-ink-800" aria-label="Settings"><Settings className="h-5 w-5" /></NavLink>
          </div>
        </header>
        {user?.is_demo && (
          <div className="border-b border-dashed border-ink-900/40 bg-amber-100 px-4 py-1.5 text-center font-mono text-[11px] uppercase tracking-wider text-amber-900">
            Specimen account · synthetic SMS · deleted after 24 hours
          </div>
        )}
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-28 pt-7 sm:px-6 lg:px-10 lg:pb-14 lg:pt-10">
          <Outlet />
        </main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t-2 border-ink-900 bg-ink-100 pb-[env(safe-area-inset-bottom)] lg:hidden" aria-label="Main">
        {MOBILE.map(({ to, short }, i) => (
          <NavLink key={to} to={to} className={({ isActive }) =>
            `flex flex-col items-center gap-0.5 border-r border-dashed border-ink-900/25 py-2 last:border-r-0 ${isActive ? "bg-ink-900 text-white" : "text-ink-700"}`}>
            <span className="font-mono text-[10px] opacity-60">{String(i + 1).padStart(2, "0")}</span>
            <span className="font-display text-sm font-medium">{short}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
