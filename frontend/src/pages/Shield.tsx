import { CheckCircle2, ExternalLink, RotateCcw, ShieldAlert, ShieldCheck, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";
import { api, type ScamAlert, type ScamVerdict } from "../api/client";
import { EmptyState, ErrorState, LevelBadge, Notice, PageHeader, Skeleton, Spinner } from "../components/ui";
import { dateLabel } from "../format";
import { errorMessage, useApi } from "../hooks";

function Meter({ score, level }: { score: number; level: ScamVerdict["level"] }) {
  const color = level === "dangerous" ? "bg-red-500" : level === "suspicious" ? "bg-amber-500" : "bg-brand-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-ink-100"><div className={`h-full ${color}`} style={{ width: `${Math.round(score * 100)}%` }} /></div>
      <span className="num text-xs text-ink-500">{Math.round(score * 100)}/100</span>
    </div>
  );
}

function Checker({ aiEnabled }: { aiEnabled: boolean }) {
  const [text, setText] = useState("");
  const [sender, setSender] = useState("");
  const [result, setResult] = useState<ScamVerdict | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const check = async (e: FormEvent, explain = false) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { setResult(await api.post<ScamVerdict>("/api/scam/check", { text, sender, explain })); } catch (e2) { setErr(errorMessage(e2)); } finally { setBusy(false); }
  };
  return (
    <form className="card p-5" onSubmit={(e) => check(e)}>
      <h2 className="font-semibold">Check a message</h2>
      <p className="mb-3 text-sm text-ink-500">Got a text you are unsure about? Paste it here. It is checked and not saved.</p>
      <textarea className="input min-h-[110px]" required minLength={5} maxLength={4000} placeholder="Paste the SMS or WhatsApp message" value={text} onChange={(e) => setText(e.target.value)} aria-label="Message to check" />
      <input className="input mt-2" placeholder="Sender (optional), e.g. VM-HDFCBK or +91 98…" value={sender} maxLength={64} onChange={(e) => setSender(e.target.value)} aria-label="Sender" />
      <div className="mt-3 flex flex-wrap gap-2">
        <button className="btn-primary" disabled={busy || text.trim().length < 5}>{busy ? <Spinner className="h-4 w-4 text-white" /> : <ShieldCheck className="h-4 w-4" />}Check</button>
        {aiEnabled && <button type="button" className="btn-ghost" disabled={busy || text.trim().length < 5} onClick={(e) => check(e as unknown as FormEvent, true)}><Sparkles className="h-4 w-4 text-brand-600" />Check and explain with AI</button>}
      </div>
      {err && <div className="mt-3"><Notice tone="error">{err}</Notice></div>}
      {result && (
        <div className={`mt-4 rounded-xl border p-4 ${result.level === "dangerous" ? "border-red-200 bg-red-50" : result.level === "suspicious" ? "border-amber-200 bg-amber-50" : "border-brand-200 bg-brand-50"}`} aria-live="polite">
          <div className="flex flex-wrap items-center gap-3"><LevelBadge level={result.level} /><Meter score={result.score} level={result.level} /></div>
          {result.reasons.length > 0 && <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-ink-800">{result.reasons.map((r) => <li key={r.code}>{r.text}</li>)}</ul>}
          {result.ai_explanation && <div className="mt-3 rounded-lg bg-white/70 p-3 text-sm"><div className="mb-1 flex items-center gap-1 text-xs font-semibold text-brand-700"><Sparkles className="h-3 w-3" />AI explanation</div>{result.ai_explanation}</div>}
          {result.ai_error && <p className="mt-2 text-xs text-ink-500">AI explanation unavailable: {result.ai_error}</p>}
          <p className="mt-3 text-sm font-medium text-ink-800">{result.advice}</p>
        </div>
      )}
    </form>
  );
}

export default function Shield() {
  const [showDismissed, setShowDismissed] = useState(false);
  const alerts = useApi<{ counts: { dangerous: number; suspicious: number }; scanned: number; items: ScamAlert[] }>(`/api/scam/alerts${showDismissed ? "?include_dismissed=true" : ""}`);
  const meta = useApi<{ llm: { enabled: boolean } }>("/api/meta");
  const [flash, setFlash] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const act = async (a: ScamAlert, action: "dismiss" | "restore") => {
    setBusyId(a.id);
    try {
      const r = await api.post<{ transaction: { amount: number } | null }>(`/api/scam/alerts/${a.id}/${action}`);
      setFlash(action === "restore" ? "Message flagged again." : r.transaction ? "Marked as genuine and added to your transactions." : "Marked as genuine.");
      alerts.reload();
    } catch (e) { setFlash(errorMessage(e)); } finally { setBusyId(null); }
  };

  return (
    <>
      <PageHeader title="Scam Shield" subtitle="Messages that try to trick you into paying, sharing a PIN or clicking a fake link." />
      <div className="grid gap-5 lg:grid-cols-5">
        <div className="space-y-4 lg:col-span-3">
          {alerts.data && (
            <div className="grid grid-cols-3 gap-3">
              <div className="card p-4"><div className="text-xs text-ink-500">Scanned</div><div className="num text-2xl font-bold">{alerts.data.scanned}</div></div>
              <div className="card p-4"><div className="text-xs text-ink-500">Dangerous</div><div className="num text-2xl font-bold text-red-600">{alerts.data.counts.dangerous}</div></div>
              <div className="card p-4"><div className="text-xs text-ink-500">Suspicious</div><div className="num text-2xl font-bold text-amber-600">{alerts.data.counts.suspicious}</div></div>
            </div>
          )}
          {flash && <Notice tone="good">{flash}</Notice>}
          {alerts.error ? <ErrorState message={alerts.error} onRetry={alerts.reload} /> : !alerts.data ? <Skeleton className="h-80" /> : alerts.data.items.length === 0 ? (
            <EmptyState title="No risky messages" body={alerts.data.scanned ? `All ${alerts.data.scanned} imported messages look clean.` : "Import messages and they are scanned automatically."} />
          ) : (
            <ul className="space-y-3">
              {alerts.data.items.map((a) => (
                <li key={a.id} className={`card overflow-hidden ${a.dismissed ? "opacity-60" : ""}`}>
                  <div className={`h-1 ${a.level === "dangerous" ? "bg-red-500" : "bg-amber-400"}`} />
                  <div className="p-4">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <LevelBadge level={a.level} /><Meter score={a.score} level={a.level} />
                      <span className="ml-auto text-xs text-ink-500">{a.sender || "Unknown sender"} · {dateLabel(a.received_at)}</span>
                    </div>
                    <p className="rounded-lg bg-ink-50 p-3 font-mono text-[13px] leading-relaxed text-ink-800">{a.body}</p>
                    <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-ink-500">Why it was flagged</div>
                    <ul className="mt-1 space-y-1 text-sm">{a.reasons.map((r) => <li key={r.code} className="flex gap-2"><ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-red-500" aria-hidden />{r.text}</li>)}</ul>
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                      <p className="text-xs text-ink-500">Not counted in your spending.</p>
                      {a.dismissed
                        ? <button className="btn-ghost px-3 py-1.5 text-xs" disabled={busyId === a.id} onClick={() => act(a, "restore")}><RotateCcw className="h-3.5 w-3.5" />Flag again</button>
                        : <button className="btn-ghost px-3 py-1.5 text-xs" disabled={busyId === a.id} onClick={() => act(a, "dismiss")}><CheckCircle2 className="h-3.5 w-3.5" />This is genuine</button>}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <label className="flex items-center gap-2 px-1 text-sm text-ink-600"><input type="checkbox" className="h-4 w-4 accent-brand-600" checked={showDismissed} onChange={(e) => setShowDismissed(e.target.checked)} />Show messages marked genuine</label>
        </div>
        <div className="space-y-4 lg:col-span-2">
          <Checker aiEnabled={!!meta.data?.llm.enabled} />
          <div className="card p-5 text-sm">
            <h2 className="mb-2 font-semibold">If you were scammed</h2>
            <ul className="list-disc space-y-1.5 pl-5 text-ink-700">
              <li>Call the national cyber fraud helpline <b>1930</b> immediately. Fast reports can freeze the money.</li>
              <li>Report online at <a className="font-medium text-brand-700 underline" href="https://cybercrime.gov.in" target="_blank" rel="noreferrer noopener">cybercrime.gov.in <ExternalLink className="inline h-3 w-3" /></a>.</li>
              <li>Block your card or UPI through your bank's official app or the number printed on your card.</li>
              <li>Remember: you never need a UPI PIN to <i>receive</i> money.</li>
            </ul>
          </div>
        </div>
      </div>
    </>
  );
}
