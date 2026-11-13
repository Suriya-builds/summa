import { AlertTriangle, ArrowDownRight, ArrowUpRight, CheckCircle2, Info, RefreshCw, ShieldAlert, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type Insight, type RecurringItem, type Summary } from "../api/client";
import { MonthPicker } from "../components/MonthPicker";
import { ErrorState, NoDataCta, Notice, PageHeader, Skeleton, Spinner, Stat } from "../components/ui";
import { colorFor, compactInr, dateLabel, inr, monthLabel, pct, titleCase } from "../format";
import { errorMessage, useApi } from "../hooks";

const TONE = {
  warn: { icon: AlertTriangle, cls: "text-amber-600 bg-amber-50" },
  good: { icon: CheckCircle2, cls: "text-brand-700 bg-brand-50" },
  info: { icon: Info, cls: "text-sky-700 bg-sky-50" },
};

function InsightsCard({ month, items, aiAvailable }: { month: string; items: Insight[]; aiAvailable: boolean }) {
  const [narrative, setNarrative] = useState<{ text: string; unverified: string[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { setNarrative(null); setErr(null); }, [month]);

  const summarise = async () => {
    setBusy(true); setErr(null);
    try {
      const r = await api.post<{ narrative: string; figure_check: { unverified: string[] } }>("/api/analytics/insights/narrative", { month });
      setNarrative({ text: r.narrative, unverified: r.figure_check.unverified });
    } catch (e) { setErr(errorMessage(e)); } finally { setBusy(false); }
  };

  return (
    <div className="card p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-semibold">What stands out</h2>
        {aiAvailable && (
          <button className="btn-ghost px-3 py-1.5 text-xs" onClick={summarise} disabled={busy}>
            {busy ? <Spinner className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5 text-brand-600" />} Summarise with AI
          </button>
        )}
      </div>
      {narrative && (
        <div className="mb-4 rounded-xl bg-gradient-to-br from-brand-50 to-white p-4 text-sm leading-relaxed text-ink-800">
          {narrative.text}
          <div className="mt-2 text-xs text-ink-500">
            {narrative.unverified.length === 0 ? "Every figure above was checked against your data." : `Could not verify: ${narrative.unverified.join(", ")}`}
          </div>
        </div>
      )}
      {err && <div className="mb-4"><Notice tone="error">{err}</Notice></div>}
      {items.length === 0 ? <p className="muted">Nothing unusual this month.</p> : (
        <ul className="space-y-3">
          {items.map((i, n) => {
            const { icon: Icon, cls } = TONE[i.tone];
            return (
              <li key={n} className="flex gap-3">
                <div className={`mt-0.5 h-8 w-8 shrink-0 rounded-lg p-1.5 ${cls}`}><Icon className="h-5 w-5" aria-hidden /></div>
                <div>
                  <div className="text-sm font-semibold">{i.title}</div>
                  <div className="text-sm text-ink-500">{i.detail}</div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default function Dashboard() {
  const months = useApi<{ months: string[]; default: string | null }>("/api/analytics/months");
  const [month, setMonth] = useState<string | null>(null);
  useEffect(() => { if (!month && months.data?.default) setMonth(months.data.default); }, [months.data, month]);

  const q = month ? `?month=${month}` : null;
  const summary = useApi<Summary>(q ? `/api/analytics/summary${q}` : null);
  const insights = useApi<{ items: Insight[]; ai_available: boolean }>(q ? `/api/analytics/insights${q}` : null);
  const recurring = useApi<{ items: RecurringItem[]; monthly_total: number; subscription_total: number }>("/api/analytics/recurring");
  const scams = useApi<{ counts: { dangerous: number; suspicious: number } }>("/api/scam/alerts");

  if (months.error) return <ErrorState message={months.error} onRetry={months.reload} />;
  if (months.loading) return <DashboardSkeleton />;
  if (!months.data?.months.length) return (<><PageHeader title="Dashboard" /><NoDataCta /></>);

  const s = summary.data;
  const prog = s?.progress;
  const change = s?.spend_change_pct ?? null;
  const scamTotal = (scams.data?.counts.dangerous ?? 0) + (scams.data?.counts.suspicious ?? 0);

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle={prog ? (prog.is_current ? `${monthLabel(month!)} so far · day ${prog.days_elapsed} of ${prog.days_total}` : monthLabel(month!)) : " "}
        actions={<>
          <MonthPicker months={months.data.months} value={month ?? ""} onChange={setMonth} />
          <button className="btn-ghost px-3" onClick={() => { summary.reload(); insights.reload(); }} aria-label="Refresh"><RefreshCw className="h-4 w-4" /></button>
        </>}
      />

      {scamTotal > 0 && (
        <Link to="/shield" className="mb-5 flex items-center gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-900 transition hover:bg-red-100">
          <ShieldAlert className="h-6 w-6 shrink-0 text-red-600" aria-hidden />
          <span><b>{scamTotal} risky message{scamTotal > 1 ? "s" : ""}</b> found in your inbox. None were counted as spending. Review them →</span>
        </Link>
      )}

      {summary.error ? <ErrorState message={summary.error} onRetry={summary.reload} /> : !s ? <DashboardSkeleton /> : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
            <Stat label="Money in" value={inr(s.income)} hint={`${s.transaction_count} transactions`} />
            <Stat label="Spent" value={inr(s.spend)}
              hint={change === null ? `${inr(s.average_daily_spend)} a day` : (
                <span className={`inline-flex items-center gap-0.5 ${change > 0 ? "text-red-600" : "text-brand-700"}`}>
                  {change > 0 ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                  {pct(Math.abs(change))} vs {s.previous.compared_days ? `same days of ${monthLabel(s.previous.month, true)}` : monthLabel(s.previous.month, true)}
                </span>)} />
            <Stat label={prog?.is_current ? "Kept so far" : "Saved"} value={inr(s.saved)} tone={s.saved >= 0 ? "good" : "bad"}
              hint={s.savings_rate !== null ? `${pct(s.savings_rate)} of income` : "No income recorded"} />
            <Stat label="Invested" value={inr(s.invested)} hint="SIPs and other investments" />
          </div>

          <div className="grid gap-5 lg:grid-cols-5">
            <div className="card p-5 lg:col-span-3">
              <div className="mb-1 flex items-baseline justify-between">
                <h2 className="font-semibold">Spending through the month</h2>
                <span className="num text-sm text-ink-500">{inr(s.average_daily_spend)}/day avg</span>
              </div>
              <p className="mb-3 text-xs text-ink-500">Running total of spending. Investments are excluded.</p>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={s.daily} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                    <defs><linearGradient id="g" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#10b37c" stopOpacity={0.3} /><stop offset="100%" stopColor="#10b37c" stopOpacity={0} /></linearGradient></defs>
                    <CartesianGrid stroke="#e9edf3" vertical={false} />
                    <XAxis dataKey="date" tickFormatter={(d) => String(Number(d.slice(8)))} tick={{ fontSize: 11, fill: "#7a8aa3" }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                    <YAxis tickFormatter={compactInr} tick={{ fontSize: 11, fill: "#7a8aa3" }} tickLine={false} axisLine={false} width={48} />
                    <Tooltip formatter={(v: number, name) => [inr(v), name === "cumulative_spend" ? "Spent so far" : "Spent that day"]} labelFormatter={(d) => dateLabel(String(d))} />
                    <Area type="monotone" dataKey="cumulative_spend" stroke="#079467" strokeWidth={2} fill="url(#g)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card p-5 lg:col-span-2">
              <h2 className="mb-3 font-semibold">Where it went</h2>
              {s.by_category.length === 0 ? <p className="muted">No spending this month.</p> : (
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center lg:flex-col xl:flex-row">
                  <div className="mx-auto h-40 w-40 shrink-0">
                    <ResponsiveContainer>
                      <PieChart>
                        <Pie data={s.by_category} dataKey="amount" nameKey="label" innerRadius={48} outerRadius={72} paddingAngle={1} stroke="none">
                          {s.by_category.map((c) => <Cell key={c.category} fill={colorFor(c.category)} />)}
                        </Pie>
                        <Tooltip formatter={(v: number) => inr(v)} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <ul className="w-full space-y-1.5 text-sm">
                    {s.by_category.slice(0, 7).map((c) => (
                      <li key={c.category} className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: colorFor(c.category) }} />
                        <Link to={`/transactions?month=${s.month}&category=${c.category}`} className="flex-1 truncate hover:underline">{c.label}</Link>
                        <span className="num font-medium">{inr(c.amount)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            {insights.error ? <ErrorState message={insights.error} onRetry={insights.reload} />
              : insights.data ? <InsightsCard month={s.month} items={insights.data.items} aiAvailable={insights.data.ai_available} />
              : <Skeleton className="h-64" />}

            <div className="space-y-5">
              <div className="card p-5">
                <h2 className="mb-3 font-semibold">Top merchants</h2>
                {s.top_merchants.length === 0 ? <p className="muted">No spending yet.</p> : (
                  <ul className="divide-y divide-ink-100">
                    {s.top_merchants.slice(0, 6).map((m) => (
                      <li key={m.counterparty} className="flex items-center gap-3 py-2 text-sm">
                        <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: colorFor(m.category) }} />
                        <span className="min-w-0 flex-1 truncate">{titleCase(m.counterparty)}</span>
                        <span className="text-xs text-ink-400">{m.count}×</span>
                        <span className="num w-20 text-right font-medium">{inr(m.amount)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="card p-5">
                <div className="mb-3 flex items-baseline justify-between">
                  <h2 className="font-semibold">Recurring payments</h2>
                  {recurring.data && <span className="num text-sm text-ink-500">{inr(recurring.data.monthly_total)}/month</span>}
                </div>
                {!recurring.data ? <Skeleton className="h-24" /> : recurring.data.items.length === 0 ? <p className="muted">None detected yet. They appear after two monthly payments.</p> : (
                  <ul className="divide-y divide-ink-100">
                    {recurring.data.items.map((r) => (
                      <li key={r.counterparty} className="flex items-center gap-3 py-2 text-sm">
                        <span className="min-w-0 flex-1 truncate">{titleCase(r.counterparty)}</span>
                        <span className={`chip ${r.kind === "subscription" ? "bg-pink-50 text-pink-700" : r.kind === "bill" ? "bg-yellow-50 text-yellow-800" : "bg-ink-100 text-ink-600"}`}>{r.kind}</span>
                        <span className="hidden text-xs text-ink-400 sm:inline">next {dateLabel(r.next_expected)}</span>
                        <span className="num w-16 text-right font-medium">{inr(r.amount)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-5">
      <Skeleton className="h-10 w-48" />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-28" />)}</div>
      <div className="grid gap-5 lg:grid-cols-5"><Skeleton className="h-72 lg:col-span-3" /><Skeleton className="h-72 lg:col-span-2" /></div>
    </div>
  );
}
