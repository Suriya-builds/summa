import { Bot, CheckCircle2, ChevronDown, Send, Trash2, TriangleAlert, User as UserIcon, Wrench } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, type ChatTurn } from "../api/client";
import { ErrorState, Notice, PageHeader, Skeleton, Spinner } from "../components/ui";
import { dateLabel, inr, titleCase } from "../format";
import { errorMessage, useApi } from "../hooks";

interface Status { enabled: boolean; model: string | null; setup_hint: string | null; has_data: boolean; suggested_questions: string[] }

/** Minimal, safe markdown: bold and line breaks only. Text is rendered as React text nodes. */
function Rich({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, i) => (
        <p key={i} className={line.trim() ? "" : "h-2"}>
          {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) => part.startsWith("**") && part.endsWith("**") ? <b key={j}>{part.slice(2, -2)}</b> : <span key={j}>{part.replace(/^[-*] /, "• ")}</span>)}
        </p>
      ))}
    </>
  );
}

function Evidence({ turn }: { turn: ChatTurn }) {
  const [open, setOpen] = useState(false);
  const fc = turn.figure_check;
  const cites = turn.citations ?? [];
  const tools = turn.tools ?? [];
  if (!fc && !cites.length && !tools.length) return null;
  return (
    <div className="mt-2 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        {fc && fc.checked > 0 && (fc.unverified.length === 0
          ? <span className="chip bg-brand-50 text-brand-700"><CheckCircle2 className="h-3 w-3" />{fc.verified} figure{fc.verified > 1 ? "s" : ""} checked against your data</span>
          : <span className="chip bg-amber-50 text-amber-800"><TriangleAlert className="h-3 w-3" />Could not verify {fc.unverified.join(", ")}</span>)}
        {(cites.length > 0 || tools.length > 0) && (
          <button onClick={() => setOpen(!open)} className="inline-flex items-center gap-1 font-medium text-ink-500 hover:text-ink-800">
            Show evidence <ChevronDown className={`h-3 w-3 transition ${open ? "rotate-180" : ""}`} />
          </button>
        )}
      </div>
      {open && (
        <div className="mt-2 space-y-2 rounded-xl border border-ink-100 bg-white p-3">
          {tools.length > 0 && <div className="flex flex-wrap gap-1.5">{tools.map((t, i) => <span key={i} className={`chip ${t.ok ? "bg-ink-100 text-ink-700" : "bg-red-50 text-red-700"}`} title={JSON.stringify(t.input)}><Wrench className="h-3 w-3" />{t.name}</span>)}</div>}
          {cites.length > 0 && (
            <ul className="divide-y divide-ink-100">
              {cites.slice(0, 10).map((c) => (
                <li key={c.id} className="flex items-center gap-2 py-1.5">
                  <span className="w-14 shrink-0 text-ink-500">{dateLabel(c.date)}</span>
                  <span className="min-w-0 flex-1 truncate">{titleCase(c.counterparty)}</span>
                  <span className={`num font-medium ${c.direction === "credit" ? "text-brand-700" : ""}`}>{inr(c.amount)}</span>
                </li>
              ))}
              {cites.length > 10 && <li className="pt-1.5 text-ink-500">and {cites.length - 10} more</li>}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default function Ask() {
  const status = useApi<Status>("/api/assistant/status");
  const history = useApi<{ items: ChatTurn[] }>("/api/assistant/history");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => { if (history.data) setTurns(history.data.items); }, [history.data]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [turns, busy]);

  const ask = async (question: string) => {
    const text = question.trim();
    if (!text || busy) return;
    setErr(null); setBusy(true); setQ("");
    const pending: ChatTurn = { id: -Date.now(), role: "user", content: text, created_at: new Date().toISOString() };
    setTurns((t) => [...t, pending]);
    try {
      const reply = await api.post<ChatTurn>("/api/assistant/ask", { question: text });
      setTurns((t) => [...t, reply]);
    } catch (e) {
      setErr(errorMessage(e));
      setTurns((t) => t.filter((x) => x.id !== pending.id));
      setQ(text);
    } finally { setBusy(false); }
  };
  const submit = (e: FormEvent) => { e.preventDefault(); void ask(q); };
  const clear = async () => { await api.del("/api/assistant/history"); setTurns([]); };

  if (status.error) return <ErrorState message={status.error} onRetry={status.reload} />;
  if (!status.data) return <Skeleton className="h-96" />;
  const s = status.data;

  return (
    <div className="flex min-h-[calc(100vh-12rem)] flex-col">
      <PageHeader title="Ask Summa" subtitle="Questions about your own money, answered from your transactions. Every figure is computed, not guessed."
        actions={turns.length > 0 && <button className="btn-ghost" onClick={clear}><Trash2 className="h-4 w-4" />Clear chat</button>} />

      {!s.enabled && (
        <Notice tone="warn">
          <b>The AI assistant is not switched on for this server.</b> Everything else in Summa works without it. To enable it, the person running the server sets <code className="rounded bg-white/60 px-1">ANTHROPIC_API_KEY</code> in the <code className="rounded bg-white/60 px-1">.env</code> file and restarts.
        </Notice>
      )}
      {s.enabled && !s.has_data && <Notice tone="info">You have no transactions yet. <Link className="font-semibold underline" to="/import">Import your messages</Link> first.</Notice>}

      <div className="mt-4 flex-1 space-y-4">
        {turns.length === 0 && s.enabled && s.has_data && (
          <div className="card p-5">
            <div className="mb-3 text-sm font-semibold text-ink-700">Try asking</div>
            <div className="grid gap-2 sm:grid-cols-2">
              {s.suggested_questions.map((sq) => <button key={sq} onClick={() => ask(sq)} disabled={busy} className="rounded-xl border border-ink-100 bg-ink-50 px-3 py-2.5 text-left text-sm hover:border-brand-200 hover:bg-brand-50">{sq}</button>)}
            </div>
          </div>
        )}
        {turns.map((t) => (
          <div key={t.id} className={`flex gap-3 ${t.role === "user" ? "flex-row-reverse" : ""}`}>
            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${t.role === "user" ? "bg-ink-200 text-ink-700" : "bg-ink-900 text-brand-400"}`}>
              {t.role === "user" ? <UserIcon className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>
            <div className={`max-w-[85%] ${t.role === "user" ? "text-right" : ""}`}>
              <div className={`inline-block space-y-1 rounded-2xl px-4 py-3 text-left text-sm leading-relaxed ${t.role === "user" ? "bg-ink-900 text-white" : "card"}`}>
                {t.role === "assistant" ? <Rich text={t.content} /> : t.content}
              </div>
              {t.role === "assistant" && <Evidence turn={t} />}
            </div>
          </div>
        ))}
        {busy && <div className="flex items-center gap-3 text-sm text-ink-500"><div className="flex h-8 w-8 items-center justify-center rounded-full bg-ink-900"><Spinner className="h-4 w-4 text-brand-400" /></div>Looking through your transactions…</div>}
        <div ref={end} />
      </div>

      {err && <div className="mt-3"><Notice tone="error">{err}</Notice></div>}
      <form onSubmit={submit} className="sticky bottom-20 mt-4 flex gap-2 rounded-2xl border border-ink-200 bg-white p-2 shadow-card lg:bottom-4">
        <input className="flex-1 bg-transparent px-2 text-sm focus:outline-none" placeholder={s.enabled ? "e.g. How much did I spend on Swiggy last month?" : "Assistant unavailable"}
          value={q} onChange={(e) => setQ(e.target.value)} disabled={!s.enabled || busy} maxLength={1000} aria-label="Your question" />
        <button className="btn-brand px-3" disabled={!s.enabled || busy || q.trim().length < 2} aria-label="Send"><Send className="h-4 w-4" /></button>
      </form>
    </div>
  );
}
