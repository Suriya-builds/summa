import { ArrowRight } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, type User } from "../api/client";
import { useAuth } from "../auth";
import { Logo } from "../components/Layout";
import { Notice, Spinner } from "../components/ui";
import { errorMessage } from "../hooks";

const TAPE = [
  { s: "VM-HDFCBK", b: "Sent Rs.412.00 From HDFC Bank A/C *4821 To SWIGGY On 08/11/26", out: "FOOD & DINING", amt: "−412.00", scam: false },
  { s: "AD-SBIUPI", b: "A/C X7730 debited by 45.0 on date 08Nov26 trf to SRI GANESH TEA STALL", out: "FOOD & DINING", amt: "−45.00", scam: false },
  { s: "+91 98120 45567", b: "Your HDFC Bank account will be blocked today. Update KYC at hdfc-kyc-update.in", out: "NOT COUNTED", amt: "", scam: true },
  { s: "VM-HDFCBK", b: "Your a/c XX4821 is credited with INR 45,000.00 by NEFT from ACME TECH PVT LTD", out: "SALARY", amt: "+45,000.00", scam: false },
];

export default function Landing() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signup" | "login">("signup");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState<"form" | "demo" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy("form"); setError(null);
    try {
      const body = mode === "signup" ? form : { email: form.email, password: form.password };
      const r = await api.post<{ user: User }>(`/api/auth/${mode}`, body);
      setUser(r.user);
      navigate(mode === "signup" ? "/import" : "/dashboard");
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(null); }
  };
  const demo = async () => {
    setBusy("demo"); setError(null);
    try {
      const r = await api.post<{ user: User }>("/api/auth/demo");
      setUser(r.user);
      navigate("/dashboard");
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(null); }
  };

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b-2 border-ink-900 px-5 py-4 sm:px-10">
        <Logo size="lg" />
        <span className="kicker hidden sm:block">Passbook No. 2026 / UPI</span>
      </header>

      <div className="mx-auto grid max-w-6xl gap-12 px-5 py-10 sm:px-10 lg:grid-cols-[1.2fr_1fr] lg:gap-16 lg:py-16">
        <section>
          <div className="kicker">Bank SMS in · budget and scam warnings out</div>
          <h1 className="mt-4 font-display text-[44px] font-semibold leading-[0.98] tracking-tight sm:text-7xl">
            Your inbox<br />already kept<br /><em className="text-brand-600">the accounts.</em>
          </h1>
          <p className="mt-6 max-w-lg text-lg leading-relaxed text-ink-700">
            Every UPI payment sends you a text. Summa reads them, adds them up, tells you where the month went, and stamps the fake ones before they cost you.
          </p>

          {/* receipt tape */}
          <div className="mt-10 max-w-xl">
            <div className="border border-b-0 border-ink-900 bg-white px-4 pt-4">
              <div className="flex justify-between border-b border-dashed border-ink-900/40 pb-2 font-mono text-[11px] uppercase tracking-widest text-ink-500"><span>Message</span><span>Entry</span></div>
              <ul>
                {TAPE.map((m, i) => (
                  <li key={i} className="grid grid-cols-[1fr_auto] items-center gap-4 border-b border-dashed border-ink-900/30 py-3 last:border-b-0">
                    <div className="min-w-0">
                      <div className="font-mono text-[10px] uppercase tracking-wider text-ink-400">{m.s}</div>
                      <div className={`truncate font-mono text-[12.5px] ${m.scam ? "text-ink-400 line-through decoration-red-600" : "text-ink-800"}`}>{m.b}</div>
                    </div>
                    <div className="text-right">
                      {m.scam ? <span className="stamp border-red-600 text-red-600">Scam</span> : <div className={`num text-sm font-semibold ${m.amt.startsWith("+") ? "text-brand-600" : ""}`}>{m.amt}</div>}
                      <div className="mt-1 font-mono text-[9.5px] uppercase tracking-wider text-ink-400">{m.out}</div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            <div className="perforated h-3 border-x border-ink-900 bg-white" />
          </div>

          <dl className="mt-10 grid max-w-xl grid-cols-1 gap-x-10 gap-y-5 sm:grid-cols-2">
            {[
              ["01", "A budget that writes itself", "Parsed, categorised and totalled from the alerts you already get."],
              ["02", "Scam Shield", "Fake KYC, collect requests and parcel fees, flagged with the reason."],
              ["03", "Ask in plain words", "Answers come with the transactions behind them. No guessed numbers."],
              ["04", "Yours to delete", "Runs on a server you control. Identifiers are masked before any AI call."],
            ].map(([n, t, d]) => (
              <div key={n} className="border-t border-ink-900 pt-3">
                <dt className="flex items-baseline gap-2"><span className="font-mono text-[11px] text-ink-400">{n}</span><span className="font-display text-lg font-medium">{t}</span></dt>
                <dd className="mt-1 text-sm text-ink-600">{d}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="lg:pt-6">
          <div className="border-2 border-ink-900 bg-white p-6 shadow-hard sm:p-8">
            <div className="kicker">Specimen account</div>
            <button onClick={demo} disabled={busy !== null} className="btn-brand mt-3 w-full py-3.5 text-sm">
              {busy === "demo" ? <><Spinner className="h-4 w-4 text-white" />Reading 200+ sample messages…</> : <>Try the demo, no sign-up <ArrowRight className="h-4 w-4" /></>}
            </button>
            <p className="mt-2 font-mono text-[11px] text-ink-500">Synthetic inbox, real parser. Nothing of yours is used.</p>

            <div className="my-7 flex items-center gap-3 font-mono text-[10px] uppercase tracking-widest text-ink-400"><div className="h-px flex-1 border-t border-dashed border-ink-900/40" />or open your own<div className="h-px flex-1 border-t border-dashed border-ink-900/40" /></div>

            <div className="mb-5 grid grid-cols-2 border border-ink-900" role="tablist">
              {(["signup", "login"] as const).map((m) => (
                <button key={m} role="tab" aria-selected={mode === m} onClick={() => { setMode(m); setError(null); }}
                  className={`py-2 font-mono text-xs font-semibold uppercase tracking-wider ${mode === m ? "bg-ink-900 text-white" : "bg-white text-ink-600 hover:bg-ink-100"}`}>
                  {m === "signup" ? "Create account" : "Log in"}
                </button>
              ))}
            </div>

            <form onSubmit={submit} className="space-y-4">
              {mode === "signup" && (
                <div><label className="label" htmlFor="name">Name</label>
                  <input id="name" className="input" autoComplete="name" required maxLength={80} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
              )}
              <div><label className="label" htmlFor="email">Email</label>
                <input id="email" type="email" className="input" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
              <div><label className="label" htmlFor="password">Password</label>
                <input id="password" type="password" className="input" required minLength={mode === "signup" ? 8 : 1}
                  autoComplete={mode === "signup" ? "new-password" : "current-password"} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
                {mode === "signup" && <p className="mt-1 font-mono text-[11px] text-ink-500">At least 8 characters.</p>}</div>
              {error && <Notice tone="error">{error}</Notice>}
              <button className="btn-primary w-full py-3" disabled={busy !== null}>
                {busy === "form" && <Spinner className="h-4 w-4 text-white" />}
                {mode === "signup" ? "Create account" : "Log in"}
              </button>
            </form>
          </div>
          <p className="mt-6 font-mono text-[11px] leading-relaxed text-ink-500">
            Summa explains your own spending. It is not a licensed financial adviser and never moves money.
          </p>
        </section>
      </div>
    </div>
  );
}
