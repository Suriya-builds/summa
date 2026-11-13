import { Sparkles, Wand2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type BudgetStatus, type BudgetSuggestions } from "../api/client";
import { MonthPicker } from "../components/MonthPicker";
import { ErrorState, NoDataCta, Notice, PageHeader, Skeleton, Spinner, Stat } from "../components/ui";
import { colorFor, inr, monthLabel } from "../format";
import { errorMessage, useApi } from "../hooks";

const BAR = { ok: "bg-brand-500", warning: "bg-amber-500", over: "bg-red-500", unbudgeted: "bg-ink-300" };
const LABEL = { ok: "On track", warning: "At risk", over: "Over", unbudgeted: "No budget" };
const CHIP = { ok: "bg-brand-50 text-brand-700", warning: "bg-amber-50 text-amber-800", over: "bg-red-50 text-red-700", unbudgeted: "bg-ink-100 text-ink-600" };

function Planner({ suggestions, current, onDone }: { suggestions: BudgetSuggestions; current: BudgetStatus; onDone: (msg: string) => void }) {
  const initial: Record<string, string> = {};
  for (const s of suggestions.items) initial[s.category] = String(s.suggested);
  for (const i of current.items) if (i.limit > 0) initial[i.category] = String(i.limit);
  const [values, setValues] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const total = Object.values(values).reduce((a, v) => a + (Number(v) || 0), 0);
  const rows = Array.from(new Set([...suggestions.items.map((s) => s.category), ...current.items.map((i) => i.category)]));
  const lookup = Object.fromEntries(suggestions.items.map((s) => [s.category, s]));
  const labels = Object.fromEntries([...suggestions.items, ...current.items].map((x) => [x.category, x.label]));

  const save = async () => {
    setBusy(true); setErr(null);
    try {
      const limits = Object.fromEntries(rows.map((c) => [c, Math.max(0, Number(values[c]) || 0)]));
      await api.put(`/api/budgets?month=${current.month}`, { limits });
      onDone("Budget saved.");
    } catch (e) { setErr(errorMessage(e)); setBusy(false); }
  };

  return (
    <div className="card p-5">
      <div className="mb-1 flex items-center gap-2"><Wand2 className="h-5 w-5 text-brand-600" /><h2 className="font-semibold">Plan your monthly budget</h2></div>
      <p className="mb-4 text-sm text-ink-500">
        {suggestions.basis_months.length ? <>Suggested from {suggestions.basis_months.map((m) => monthLabel(m, true)).join(" and ")}. Flexible categories are set about 10% under your average.</> : "Set a limit for each category."}
        {suggestions.excluded_one_offs.length > 0 && <> One-off purchases left out: {suggestions.excluded_one_offs.map((o) => `${o.counterparty} (${inr(o.amount)})`).join(", ")}.</>}
      </p>
      <div className="divide-y divide-ink-100">
        {rows.map((c) => (
          <div key={c} className="flex items-center gap-3 py-2.5">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: colorFor(c) }} />
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium">{labels[c]}</div>
              {lookup[c] && <div className="text-xs text-ink-500">Avg {inr(lookup[c].average)} · {lookup[c].reason}</div>}
            </div>
            <div className="relative w-28">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-ink-400">₹</span>
              <input className="input num py-2 pl-7 text-right" type="number" min={0} step={100} inputMode="numeric" aria-label={`${labels[c]} budget`}
                value={values[c] ?? ""} onChange={(e) => setValues({ ...values, [c]: e.target.value })} />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border border-dashed border-ink-900/30 bg-ink-50 p-3 text-sm">
        <span>Total <b className="num">{inr(total)}</b>{suggestions.average_income > 0 && <> of {inr(suggestions.average_income)} average income · leaves <b className={`num ${suggestions.average_income - total < 0 ? "text-red-600" : "text-brand-700"}`}>{inr(suggestions.average_income - total)}</b></>}</span>
        <button className="btn-brand" onClick={save} disabled={busy}>{busy && <Spinner className="h-4 w-4 text-white" />}Save budget</button>
      </div>
      {err && <div className="mt-3"><Notice tone="error">{err}</Notice></div>}
    </div>
  );
}

export default function Budget() {
  const months = useApi<{ months: string[]; default: string | null }>("/api/analytics/months");
  const [month, setMonth] = useState<string | null>(null);
  useEffect(() => { if (!month && months.data?.default) setMonth(months.data.default); }, [months.data, month]);
  const status = useApi<BudgetStatus>(month ? `/api/budgets?month=${month}` : null);
  const suggestions = useApi<BudgetSuggestions>("/api/budgets/suggestions");
  const [planning, setPlanning] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  if (months.error) return <ErrorState message={months.error} onRetry={months.reload} />;
  if (months.loading) return <Skeleton className="h-96" />;
  if (!months.data?.months.length) return (<><PageHeader title="Budget" /><NoDataCta /></>);
  const s = status.data;
  const budgeted = s?.items.filter((i) => i.limit > 0) ?? [];
  const unbudgeted = s?.items.filter((i) => i.limit <= 0) ?? [];

  return (
    <>
      <PageHeader title="Budget" subtitle="Limits per category, with a projection to month end."
        actions={<>
          <MonthPicker months={months.data.months} value={month ?? ""} onChange={setMonth} />
          <button className="btn-primary" onClick={() => setPlanning((p) => !p)}><Sparkles className="h-4 w-4" />{planning ? "Close planner" : s?.has_budget ? "Adjust budget" : "Suggest a budget"}</button>
        </>} />
      {flash && <div className="mb-4"><Notice tone="good">{flash}</Notice></div>}
      {status.error ? <ErrorState message={status.error} onRetry={status.reload} /> : !s ? <Skeleton className="h-96" /> : (
        <div className="space-y-5">
          {(planning || !s.has_budget) && (suggestions.data ? <Planner suggestions={suggestions.data} current={s} onDone={(m) => { setPlanning(false); setFlash(m); status.reload(); }} /> : <Skeleton className="h-64" />)}
          {s.has_budget && (
            <>
              <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
                <Stat label="Budget" value={inr(s.total_limit)} hint={monthLabel(s.month)} />
                <Stat label="Spent (budgeted)" value={inr(s.budgeted_spent)} hint={`${s.total_limit ? Math.round((s.budgeted_spent / s.total_limit) * 100) : 0}% used`} />
                <Stat label="Left" value={inr(s.total_remaining)} tone={s.total_remaining < 0 ? "bad" : "good"} />
                <Stat label="Per day left" value={s.daily_allowance !== null ? inr(s.daily_allowance) : "—"}
                  hint={s.progress.is_current ? `${s.progress.days_total - s.progress.days_elapsed} days to go` : "Month complete"} />
              </div>
              <div className="card divide-y divide-ink-100">
                {budgeted.map((i) => {
                  const used = Math.min(100, (i.spent / i.limit) * 100);
                  const projected = Math.min(100, (i.projected / i.limit) * 100);
                  return (
                    <div key={i.category} className="p-4">
                      <div className="mb-2 flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ background: colorFor(i.category) }} />
                        <span className="flex-1 text-sm font-medium">{i.label}</span>
                        <span className={`chip ${CHIP[i.status]}`}>{LABEL[i.status]}</span>
                      </div>
                      <div className="relative h-3 overflow-hidden border border-ink-900/70 bg-white" role="progressbar" aria-valuenow={Math.round(used)} aria-valuemin={0} aria-valuemax={100} aria-label={`${i.label} budget used`}>
                        {s.progress.is_current && <div className="absolute inset-y-0 left-0 bg-ink-200" style={{ width: `${projected}%` }} />}
                        <div className={`absolute inset-y-0 left-0 ${BAR[i.status]}`} style={{ width: `${used}%` }} />
                      </div>
                      <div className="mt-1.5 flex flex-wrap justify-between gap-x-3 text-xs text-ink-500">
                        <span className="num"><b className="text-ink-800">{inr(i.spent)}</b> of {inr(i.limit)}</span>
                        <span className="num">{i.status === "over" ? <span className="text-red-600">{inr(i.spent - i.limit)} over</span> : <>{inr(i.remaining ?? 0)} left</>}
                          {s.progress.is_current && <> · heading for {inr(i.projected)}</>}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
              {s.progress.is_current && <p className="px-1 text-xs text-ink-500">The grey bar is the month-end projection. Rent and subscriptions are counted once; everyday spending is extended at its current daily pace.</p>}
              {unbudgeted.length > 0 && (
                <div className="card p-4 text-sm">
                  <div className="mb-2 font-medium">Spending without a budget</div>
                  <ul className="flex flex-wrap gap-2">{unbudgeted.map((i) => <li key={i.category} className="chip bg-ink-100 text-ink-700">{i.label} · {inr(i.spent)}</li>)}</ul>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </>
  );
}
