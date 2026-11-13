import { ArrowDownLeft, ArrowUpRight, Download, Plus, Search, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type Meta, type Txn } from "../api/client";
import { EmptyState, ErrorState, Notice, PageHeader, Skeleton, Spinner } from "../components/ui";
import { colorFor, dateLabel, inr, monthLabel, titleCase } from "../format";
import { errorMessage, useApi } from "../hooks";

interface Page { items: Txn[]; total: number; page: number; page_size: number; total_debit: number; total_credit: number }

const SOURCE: Record<string, string> = { user: "set by you", rule: "known merchant", ml: "AI guess" };

function EditPanel({ txn, meta, onClose, onSaved }: { txn: Txn; meta: Meta; onClose: () => void; onSaved: (msg: string) => void }) {
  const options = txn.direction === "credit" ? meta.categories.income : meta.categories.expense;
  const [category, setCategory] = useState(txn.category);
  const [note, setNote] = useState(txn.note ?? "");
  const [applyAll, setApplyAll] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const save = async () => {
    setBusy(true); setErr(null);
    try {
      const r = await api.patch<{ also_updated: number }>(`/api/transactions/${txn.id}`, { category, note, apply_to_merchant: applyAll });
      onSaved(r.also_updated ? `Saved. ${r.also_updated} other ${titleCase(txn.counterparty)} payment${r.also_updated > 1 ? "s" : ""} updated, and future ones will follow.` : "Saved.");
    } catch (e) { setErr(errorMessage(e)); } finally { setBusy(false); }
  };
  const remove = async () => {
    if (!confirm("Delete this transaction? It will no longer count in totals.")) return;
    setBusy(true);
    try { await api.del(`/api/transactions/${txn.id}`); onSaved("Transaction deleted."); } catch (e) { setErr(errorMessage(e)); setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-ink-900/40 sm:items-center" onClick={onClose}>
      <div className="w-full max-w-md rounded-t-3xl bg-white p-6 sm:rounded-3xl" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Edit transaction">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <div className="text-lg font-semibold">{titleCase(txn.counterparty)}</div>
            <div className="text-sm text-ink-500">{dateLabel(txn.date, true)} · {txn.channel.toUpperCase()}{txn.account_tail ? ` · a/c ••${txn.account_tail}` : ""}</div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1 text-ink-400 hover:bg-ink-50" aria-label="Close"><X className="h-5 w-5" /></button>
        </div>
        <div className={`num mb-5 text-3xl font-bold ${txn.direction === "credit" ? "text-brand-700" : ""}`}>{txn.direction === "credit" ? "+" : "−"}{inr(txn.amount, true)}</div>
        <label className="label" htmlFor="cat">Category</label>
        <select id="cat" className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
          {options.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
        </select>
        <p className="mt-1 text-xs text-ink-500">Currently {SOURCE[txn.category_source] ?? txn.category_source}{txn.category_source === "ml" ? ` (${Math.round(txn.category_confidence * 100)}% confident)` : ""}.</p>
        {txn.direction === "debit" && (
          <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={applyAll} onChange={(e) => setApplyAll(e.target.checked)} className="h-4 w-4 accent-brand-600" />
            Apply to every payment to {titleCase(txn.counterparty)}</label>
        )}
        <label className="label mt-4" htmlFor="note">Note</label>
        <input id="note" className="input" maxLength={200} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Optional" />
        {txn.reference && <p className="mt-3 text-xs text-ink-400">Reference {txn.reference}</p>}
        {err && <div className="mt-3"><Notice tone="error">{err}</Notice></div>}
        <div className="mt-6 flex gap-2">
          <button className="btn-danger px-3" onClick={remove} disabled={busy} aria-label="Delete"><Trash2 className="h-4 w-4" /></button>
          <button className="btn-ghost flex-1" onClick={onClose}>Cancel</button>
          <button className="btn-primary flex-1" onClick={save} disabled={busy}>{busy && <Spinner className="h-4 w-4 text-white" />} Save</button>
        </div>
      </div>
    </div>
  );
}

function AddPanel({ meta, onClose, onSaved }: { meta: Meta; onClose: () => void; onSaved: (msg: string) => void }) {
  const today = new Date().toISOString().slice(0, 10);
  const [f, setF] = useState({ date: today, amount: "", direction: "debit", counterparty: "", category: "" });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const options = f.direction === "credit" ? meta.categories.income : meta.categories.expense;
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      await api.post("/api/transactions", { ...f, amount: Number(f.amount), category: f.category || null });
      onSaved("Transaction added.");
    } catch (e2) { setErr(errorMessage(e2)); setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-ink-900/40 sm:items-center" onClick={onClose}>
      <form onSubmit={submit} className="w-full max-w-md space-y-3 rounded-t-3xl bg-white p-6 sm:rounded-3xl" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Add transaction">
        <div className="mb-1 text-lg font-semibold">Add a cash or missing payment</div>
        <div className="grid grid-cols-2 gap-2 border border-dashed border-ink-900/30 bg-ink-50 p-1 text-sm font-semibold">
          {["debit", "credit"].map((d) => <button type="button" key={d} onClick={() => setF({ ...f, direction: d, category: "" })} className={`rounded-lg py-1.5 ${f.direction === d ? "bg-white shadow-card" : "text-ink-500"}`}>{d === "debit" ? "Money out" : "Money in"}</button>)}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label" htmlFor="a-amt">Amount (₹)</label><input id="a-amt" className="input" type="number" min="0.01" step="0.01" required value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></div>
          <div><label className="label" htmlFor="a-date">Date</label><input id="a-date" className="input" type="date" required max={today} value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></div>
        </div>
        <div><label className="label" htmlFor="a-cp">Paid to / received from</label><input id="a-cp" className="input" required maxLength={120} value={f.counterparty} onChange={(e) => setF({ ...f, counterparty: e.target.value })} /></div>
        <div><label className="label" htmlFor="a-cat">Category</label>
          <select id="a-cat" className="input" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>
            <option value="">Let Summa decide</option>{options.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
          </select></div>
        {err && <Notice tone="error">{err}</Notice>}
        <div className="flex gap-2 pt-2"><button type="button" className="btn-ghost flex-1" onClick={onClose}>Cancel</button><button className="btn-primary flex-1" disabled={busy}>{busy && <Spinner className="h-4 w-4 text-white" />}Add</button></div>
      </form>
    </div>
  );
}

export default function Transactions() {
  const [params, setParams] = useSearchParams();
  const meta = useApi<Meta>("/api/meta");
  const months = useApi<{ months: string[] }>("/api/analytics/months");
  const [search, setSearch] = useState(params.get("q") ?? "");
  const [editing, setEditing] = useState<Txn | null>(null);
  const [adding, setAdding] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  const month = params.get("month") ?? "";
  const category = params.get("category") ?? "";
  const direction = params.get("direction") ?? "";
  const page = Number(params.get("page") ?? "1");

  const set = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v); else next.delete(k);
    if (k !== "page") next.delete("page");
    setParams(next, { replace: true });
  };
  useEffect(() => { const t = setTimeout(() => { if ((params.get("q") ?? "") !== search) set("q", search.trim()); }, 300); return () => clearTimeout(t); }, [search]); // eslint-disable-line

  const query = useMemo(() => {
    const q = new URLSearchParams({ page: String(page), page_size: "30" });
    for (const k of ["month", "category", "direction", "q", "sort"]) { const v = params.get(k); if (v) q.set(k, v); }
    return `/api/transactions?${q}`;
  }, [params, page]);
  const list = useApi<Page>(query);
  const allCats = meta.data ? [...meta.data.categories.expense, ...meta.data.categories.income] : [];
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / list.data.page_size)) : 1;

  const saved = (msg: string) => { setEditing(null); setAdding(false); setFlash(msg); list.reload(); setTimeout(() => setFlash(null), 5000); };
  const exportHref = `/api/transactions/export.csv${month ? `?month=${month}` : ""}`;

  return (
    <>
      <PageHeader title="Transactions" subtitle="Every payment Summa read from your messages. Tap one to fix its category."
        actions={<>
          <a className="btn-ghost" href={exportHref} download><Download className="h-4 w-4" /> CSV</a>
          <button className="btn-primary" onClick={() => setAdding(true)} disabled={!meta.data}><Plus className="h-4 w-4" /> Add</button>
        </>} />

      <div className="card mb-4 grid gap-2 p-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="relative sm:col-span-2 lg:col-span-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" aria-hidden />
          <input className="input pl-9" placeholder="Search merchant or person" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search" maxLength={80} />
        </div>
        <select className="input" value={month} onChange={(e) => set("month", e.target.value)} aria-label="Month">
          <option value="">All months</option>{months.data?.months.map((m) => <option key={m} value={m}>{monthLabel(m)}</option>)}
        </select>
        <select className="input" value={category} onChange={(e) => set("category", e.target.value)} aria-label="Category">
          <option value="">All categories</option>{allCats.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
        </select>
        <select className="input" value={direction} onChange={(e) => set("direction", e.target.value)} aria-label="Direction">
          <option value="">Money in and out</option><option value="debit">Money out</option><option value="credit">Money in</option>
        </select>
      </div>

      {flash && <div className="mb-4"><Notice tone="good">{flash}</Notice></div>}

      {list.error ? <ErrorState message={list.error} onRetry={list.reload} /> : !list.data ? <Skeleton className="h-96" /> : list.data.total === 0 ? (
        <EmptyState title="No matching transactions" body={params.toString() ? "Try clearing the filters." : "Import your SMS to see transactions here."} />
      ) : (
        <>
          <div className="mb-2 flex flex-wrap gap-x-5 gap-y-1 px-1 text-sm text-ink-500">
            <span>{list.data.total} transactions</span>
            <span>Out <b className="num text-ink-800">{inr(list.data.total_debit)}</b></span>
            <span>In <b className="num text-brand-700">{inr(list.data.total_credit)}</b></span>
          </div>
          <ul className={`card divide-y divide-ink-100 ${list.loading ? "opacity-60" : ""}`}>
            {list.data.items.map((t) => (
              <li key={t.id}>
                <button className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-ink-50" onClick={() => setEditing(t)}>
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl" style={{ background: `${colorFor(t.category)}1f`, color: colorFor(t.category) }}>
                    {t.direction === "credit" ? <ArrowDownLeft className="h-4 w-4" /> : <ArrowUpRight className="h-4 w-4" />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{titleCase(t.counterparty)}</div>
                    <div className="flex items-center gap-1.5 truncate text-xs text-ink-500">
                      {dateLabel(t.date, true)} · {t.category_label}
                      {t.category_source === "ml" && <span className="chip bg-violet-50 px-1.5 text-[10px] text-violet-700">AI</span>}
                      {t.note && <span className="truncate italic">· {t.note}</span>}
                    </div>
                  </div>
                  <div className={`num text-sm font-semibold ${t.direction === "credit" ? "text-brand-700" : ""}`}>{t.direction === "credit" ? "+" : "−"}{inr(t.amount, true)}</div>
                </button>
              </li>
            ))}
          </ul>
          {pages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-3 text-sm">
              <button className="btn-ghost" disabled={page <= 1} onClick={() => set("page", String(page - 1))}>Previous</button>
              <span className="text-ink-500">Page {page} of {pages}</span>
              <button className="btn-ghost" disabled={page >= pages} onClick={() => set("page", String(page + 1))}>Next</button>
            </div>
          )}
        </>
      )}
      {editing && meta.data && <EditPanel txn={editing} meta={meta.data} onClose={() => setEditing(null)} onSaved={saved} />}
      {adding && meta.data && <AddPanel meta={meta.data} onClose={() => setAdding(false)} onSaved={saved} />}
    </>
  );
}
