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
  return <div className={`animate-pulse bg-ink-200/70 ${className}`} />;
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
      <div className="border border-dashed border-ink-900/50 p-3"><Inbox className="h-7 w-7 text-ink-500" aria-hidden /></div>
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
    <div className="mb-7 flex flex-col gap-4 border-b-2 border-ink-900 pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="h1">{title}</h1>
        {subtitle && <p className="mt-2.5 font-mono text-xs text-ink-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warn" | "error" | "good"; children: ReactNode }) {
  const styles = {
    info: "border-sky-700 bg-sky-50 text-sky-900",
    warn: "border-amber-600 bg-amber-50 text-amber-900",
    error: "border-red-600 bg-red-50 text-red-800",
    good: "border-brand-600 bg-brand-50 text-brand-800",
  }[tone];
  return <div className={`border border-l-4 px-4 py-3 text-sm ${styles}`} role={tone === "error" ? "alert" : undefined}>{children}</div>;
}

export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: ReactNode; tone?: "good" | "bad" }) {
  return (
    <div className="border-t-[3px] border-ink-900 bg-white px-4 pb-4 pt-3" style={{ boxShadow: "inset -1px 0 0 rgba(22,20,17,.8), inset 1px 0 0 rgba(22,20,17,.8), inset 0 -1px 0 rgba(22,20,17,.8)" }}>
      <div className="kicker">{label}</div>
      <div className={`num mt-2 text-[26px] font-semibold leading-none sm:text-[30px] ${tone === "good" ? "text-brand-600" : tone === "bad" ? "text-red-600" : "text-ink-900"}`}>{value}</div>
      {hint && <div className="mt-2 border-t border-dashed border-ink-900/30 pt-2 font-mono text-[11px] text-ink-500">{hint}</div>}
    </div>
  );
}

export function LevelBadge({ level }: { level: "safe" | "suspicious" | "dangerous" }) {
  const map = { dangerous: "border-red-600 text-red-600", suspicious: "border-amber-600 text-amber-700", safe: "border-brand-600 text-brand-600" } as const;
  const text = { dangerous: "Scam", suspicious: "Suspect", safe: "Clear" }[level];
  return <span className={`stamp ${map[level]}`}>{text}</span>;
}
