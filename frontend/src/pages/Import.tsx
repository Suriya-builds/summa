import { CheckCircle2, FileUp, Sparkles, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, type ImportResult, type Meta } from "../api/client";
import { Notice, PageHeader, Spinner } from "../components/ui";
import { errorMessage, useApi } from "../hooks";

const EXAMPLE = `VM-HDFCBK: Sent Rs.250.00 From HDFC Bank A/C *1234 To SWIGGY On 03/11/26 Ref 427612345678 Not You? Call 18002586161
AD-SBIUPI: Dear UPI user A/C X7730 debited by 45.0 on date 04Nov26 trf to SRI GANESH TEA STALL Refno 427612345679. -SBI
+919812045567: Dear Customer, your HDFC Bank account will be blocked today. Update your KYC immediately at hdfc-kyc-update.in/verify`;

function ResultCard({ r }: { r: ImportResult }) {
  return (
    <div className="card p-5" aria-live="polite">
      <div className="mb-3 flex items-center gap-2"><CheckCircle2 className="h-5 w-5 text-brand-600" /><h2 className="font-semibold">Read {r.imported} new message{r.imported === 1 ? "" : "s"}</h2></div>
      <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-5">
        {[["Transactions", r.transactions, "text-brand-700"], ["Scams flagged", r.scams, "text-red-600"], ["OTPs", r.otps, ""], ["Promotions", r.promos, ""], ["Other", r.others, ""]].map(([l, v, c]) => (
          <div key={l as string} className="border border-dashed border-ink-900/30 bg-ink-50 p-3"><div className="text-xs text-ink-500">{l}</div><div className={`num text-xl font-bold ${c}`}>{v}</div></div>
        ))}
      </div>
      <ul className="mt-3 space-y-1 text-sm text-ink-600">
        {r.duplicates > 0 && <li>{r.duplicates} already imported, skipped.</li>}
        {r.llm_parsed > 0 && <li>{r.llm_parsed} unusual format{r.llm_parsed > 1 ? "s" : ""} read by AI.</li>}
        {r.unparsed_money_messages > 0 && <li>{r.unparsed_money_messages} message{r.unparsed_money_messages > 1 ? "s" : ""} mentioned money but were not recognised as a completed payment.</li>}
        {r.llm_error && <li className="text-amber-700">AI parsing failed: {r.llm_error}</li>}
        {r.skipped_over_limit > 0 && <li className="text-amber-700">{r.skipped_over_limit} messages over the per-import limit were skipped. Import them separately.</li>}
        {r.first_date && <li>Messages span {r.first_date} to {r.last_date}.</li>}
      </ul>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link to="/dashboard" className="btn-primary">See dashboard</Link>
        {r.scams > 0 && <Link to="/shield" className="btn-ghost">Review scams</Link>}
      </div>
    </div>
  );
}

export default function ImportPage() {
  const meta = useApi<Meta>("/api/meta");
  const [text, setText] = useState("");
  const [useAi, setUseAi] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const aiOn = !!meta.data?.llm.enabled;

  const run = async (kind: string, fn: () => Promise<ImportResult>) => {
    setBusy(kind); setErr(null); setResult(null);
    try { setResult(await fn()); } catch (e) { setErr(errorMessage(e)); } finally { setBusy(null); }
  };
  const onFile = (f: File | undefined) => {
    if (!f) return;
    const form = new FormData(); form.append("file", f); form.append("use_ai", String(useAi && aiOn));
    void run("file", () => api.upload<ImportResult>("/api/messages/import-file", form));
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <>
      <PageHeader title="Import messages" subtitle="Bring in your bank, card and UPI SMS. Importing the same messages twice is safe; duplicates are skipped." />
      <div className="grid gap-5 lg:grid-cols-5">
        <div className="space-y-5 lg:col-span-3">
          <div className="card p-5">
            <h2 className="font-semibold">Paste messages</h2>
            <p className="mb-3 text-sm text-ink-500">One message per line, or separate them with a blank line. A sender prefix like <code>VM-HDFCBK:</code> helps scam detection.</p>
            <textarea className="input min-h-[200px] font-mono text-[13px]" value={text} onChange={(e) => setText(e.target.value)} placeholder={EXAMPLE} aria-label="Messages to import" />
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button className="btn-primary" disabled={!!busy || !text.trim()} onClick={() => run("text", () => api.post<ImportResult>("/api/messages/import", { text, use_ai: useAi && aiOn }))}>
                {busy === "text" ? <Spinner className="h-4 w-4 text-white" /> : <Upload className="h-4 w-4" />}Import
              </button>
              <button className="text-sm font-medium text-brand-700 hover:underline" onClick={() => setText(EXAMPLE)} type="button">Use the example</button>
            </div>
          </div>
          <div className="card p-5">
            <h2 className="font-semibold">Upload an export</h2>
            <p className="mb-3 text-sm text-ink-500">Accepts .txt, .csv (with a body column), .json, or the .xml file from the Android app “SMS Backup &amp; Restore”. Up to 2 MB.</p>
            <input ref={fileRef} type="file" accept=".txt,.csv,.json,.xml,text/plain,text/csv,application/json,text/xml" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
            <button className="btn-ghost" disabled={!!busy} onClick={() => fileRef.current?.click()}>{busy === "file" ? <Spinner className="h-4 w-4" /> : <FileUp className="h-4 w-4" />}Choose file</button>
          </div>
          {err && <Notice tone="error">{err}</Notice>}
          {result && <ResultCard r={result} />}
        </div>
        <div className="space-y-5 lg:col-span-2">
          <div className="card p-5">
            <h2 className="font-semibold">No messages handy?</h2>
            <p className="mb-3 text-sm text-ink-500">Generate about ten weeks of realistic synthetic SMS, including a few scams, and run them through the same pipeline.</p>
            <button className="btn-brand" disabled={!!busy} onClick={() => run("sample", () => api.post<ImportResult>("/api/messages/sample"))}>
              {busy === "sample" ? <Spinner className="h-4 w-4 text-white" /> : <Sparkles className="h-4 w-4" />}Load sample inbox
            </button>
          </div>
          <div className="card p-5">
            <label className={`flex items-start gap-3 ${aiOn ? "" : "opacity-60"}`}>
              <input type="checkbox" className="mt-1 h-4 w-4 accent-brand-600" checked={useAi && aiOn} disabled={!aiOn} onChange={(e) => setUseAi(e.target.checked)} />
              <span className="text-sm"><b>Read unusual formats with AI</b><br /><span className="text-ink-500">
                {aiOn ? "Messages the built-in parser cannot read are sent to Claude, with account numbers, phone numbers and UPI references masked first. Amounts the AI returns are only accepted if they appear in the original message." : "Not available: the server has no AI key configured."}
              </span></span>
            </label>
          </div>
          <div className="card p-5 text-sm text-ink-600">
            <h2 className="mb-2 font-semibold text-ink-900">How to get your SMS</h2>
            <ol className="list-decimal space-y-1.5 pl-5">
              <li>On Android, install “SMS Backup &amp; Restore” and back up messages to a file.</li>
              <li>Upload the .xml file here. Only received messages are read.</li>
              <li>On any phone you can also copy bank messages and paste them in the box.</li>
            </ol>
            <p className="mt-3 text-xs text-ink-500">Messages are stored on this Summa server only. You can delete all of them at any time in Settings.</p>
          </div>
        </div>
      </div>
    </>
  );
}
