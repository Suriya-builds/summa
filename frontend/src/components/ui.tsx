import { AlertTriangle, Inbox, Loader2, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export function Spinner({ className = "h-5 w-5" }: { className?: string }) {
  return <Loader2 className={`${className} animate-spin text-ink-400`} aria-hidden />;
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex min-h-[200px] items-center justify-center gap-3 text-ink-500" role="status">
      <Spinner /> <span className="text-sm">{label}…</span>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-xl bg-ink-100 ${className}`} />;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card flex flex-col items-center gap-3 p-8 text-center" role="alert">
      <AlertTriangle className="h-8 w-8 text-amber-500" aria-hidden />
      <p className="max-w-md text-sm text-ink-700">{message}</p>
      {onRetry && <button className="btn-ghost" onClick={onRetry}><RefreshCw className="h-4 w-4" /> Try again</button>}
    </div>
  );
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center gap-3 px-6 py-12 text-center">
      <div className="rounded-2xl bg-ink-50 p-3"><Inbox className="h-7 w-7 text-ink-400" aria-hidden /></div>
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="max-w-md text-sm text-ink-500">{body}</p>
      {action}
    </div>
  );
}

export function NoDataCta() {
  return (
    <EmptyState
      title="No transactions yet"
      body="Import your bank and UPI SMS, or load the sample inbox to see how Summa works."
      action={<Link to="/import" className="btn-brand">Import messages</Link>}
    />
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="h1">{title}</h1>
        {subtitle && <p className="muted mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warn" | "error" | "good"; children: ReactNode }) {
  const styles = {
    info: "border-sky-200 bg-sky-50 text-sky-900",
    warn: "border-amber-200 bg-amber-50 text-amber-900",
    error: "border-red-200 bg-red-50 text-red-800",
    good: "border-brand-200 bg-brand-50 text-brand-800",
  }[tone];
  return <div className={`rounded-xl border px-4 py-3 text-sm ${styles}`} role={tone === "error" ? "alert" : undefined}>{children}</div>;
}

export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: ReactNode; tone?: "good" | "bad" }) {
  return (
    <div className="card p-4 sm:p-5">
      <div className="text-xs font-medium uppercase tracking-wide text-ink-500">{label}</div>
      <div className={`num mt-1.5 text-2xl font-bold ${tone === "good" ? "text-brand-700" : tone === "bad" ? "text-red-600" : "text-ink-900"}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-ink-500">{hint}</div>}
    </div>
  );
}

export function LevelBadge({ level }: { level: "safe" | "suspicious" | "dangerous" }) {
  const map = {
    dangerous: "bg-red-100 text-red-800",
    suspicious: "bg-amber-100 text-amber-800",
    safe: "bg-brand-100 text-brand-800",
  } as const;
  const text = { dangerous: "Dangerous", suspicious: "Suspicious", safe: "Looks safe" }[level];
  return <span className={`chip ${map[level]}`}>{text}</span>;
}
