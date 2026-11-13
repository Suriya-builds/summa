import { Trash2 } from "lucide-react";
import { Fragment, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Meta } from "../api/client";
import { useAuth } from "../auth";
import { ErrorState, Notice, PageHeader, Skeleton } from "../components/ui";
import { errorMessage, useApi } from "../hooks";

interface Overview { messages: number; transactions: number; budgets: number; merchant_rules: number; chat_messages: number; first_transaction: string | null; last_transaction: string | null }

function ModelCard({ title, m }: { title: string; m: Record<string, unknown> }) {
  const rows = Object.entries(m).filter(([k]) => k !== "note" && k !== "model");
  return (
    <div className="border border-dashed border-ink-900/30 bg-ink-50 p-4 text-sm">
      <div className="font-semibold">{title}</div>
      <div className="text-xs text-ink-500">{String(m.model ?? "")}</div>
      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
        {rows.map(([k, v]) => (<Fragment key={k}><dt className="text-ink-500">{k.replace(/_/g, " ")}</dt><dd className="num text-right font-medium">{typeof v === "number" && v <= 1 ? `${(v * 100).toFixed(1)}%` : String(v)}</dd></Fragment>))}
      </dl>
      {typeof m.note === "string" && <p className="mt-2 text-xs text-ink-500">{m.note}</p>}
    </div>
  );
}

export default function SettingsPage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const overview = useApi<Overview>("/api/account/overview");
  const meta = useApi<Meta>("/api/meta");
  const [msg, setMsg] = useState<{ tone: "good" | "error"; text: string } | null>(null);

  const wipe = async () => {
    if (!confirm("Delete all imported messages, transactions, budgets and chat history? This cannot be undone.")) return;
    try { await api.del("/api/account/data"); setMsg({ tone: "good", text: "All your data was deleted." }); overview.reload(); } catch (e) { setMsg({ tone: "error", text: errorMessage(e) }); }
  };
  const remove = async () => {
    if (!confirm("Delete your account and all data permanently?")) return;
    try { await api.del("/api/account"); setUser(null); navigate("/"); } catch (e) { setMsg({ tone: "error", text: errorMessage(e) }); }
  };

  return (
    <>
      <PageHeader title="Settings" subtitle={user?.is_demo ? "Demo account" : user?.email} />
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="mb-3 font-semibold">Your data</h2>
          {overview.error ? <ErrorState message={overview.error} onRetry={overview.reload} /> : !overview.data ? <Skeleton className="h-32" /> : (
            <dl className="grid grid-cols-2 gap-y-2 text-sm">
              <dt className="text-ink-500">Messages</dt><dd className="num text-right">{overview.data.messages}</dd>
              <dt className="text-ink-500">Transactions</dt><dd className="num text-right">{overview.data.transactions}</dd>
              <dt className="text-ink-500">Budgets</dt><dd className="num text-right">{overview.data.budgets}</dd>
              <dt className="text-ink-500">Merchant corrections</dt><dd className="num text-right">{overview.data.merchant_rules}</dd>
              <dt className="text-ink-500">Date range</dt><dd className="text-right">{overview.data.first_transaction ? `${overview.data.first_transaction} to ${overview.data.last_transaction}` : "—"}</dd>
            </dl>
          )}
          {msg && <div className="mt-4"><Notice tone={msg.tone}>{msg.text}</Notice></div>}
          <div className="mt-5 flex flex-wrap gap-2">
            <a className="btn-ghost" href="/api/transactions/export.csv" download>Export transactions (CSV)</a>
            <button className="btn-danger" onClick={wipe}><Trash2 className="h-4 w-4" />Delete all my data</button>
            {!user?.is_demo && <button className="btn-danger" onClick={remove}>Delete account</button>}
          </div>
        </div>
        <div className="card p-5">
          <h2 className="mb-1 font-semibold">How Summa's AI works</h2>
          <p className="mb-3 text-sm text-ink-500">Reading, categorising and scam scoring run on the server with small local models. The language model is used only for Ask Summa, AI summaries and, if you opt in, unusual SMS formats.</p>
          {!meta.data ? <Skeleton className="h-40" /> : (
            <div className="space-y-3">
              <div className="border border-dashed border-ink-900/30 bg-ink-50 p-4 text-sm">
                <div className="font-semibold">Language model</div>
                <div className="text-ink-600">{meta.data.llm.enabled ? `${meta.data.llm.provider} · ${meta.data.llm.model}` : "Not configured on this server"}</div>
              </div>
              {meta.data.models.scam_text && <ModelCard title="Scam text model" m={meta.data.models.scam_text} />}
              {meta.data.models.merchant_category && <ModelCard title="Merchant category model" m={meta.data.models.merchant_category} />}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
