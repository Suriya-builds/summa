import { ArrowRight, Bot, Lock, MessageSquareText, PiggyBank, ShieldAlert, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, type User } from "../api/client";
import { useAuth } from "../auth";
import { Logo } from "../components/Layout";
import { Notice, Spinner } from "../components/ui";
import { errorMessage } from "../hooks";

const SAMPLE_IN = [
  { s: "VM-HDFCBK", b: "Sent Rs.412.00 From HDFC Bank A/C *4821 To SWIGGY On 08/11/26 Ref 427612…", ok: true },
  { s: "+91 98120 45567", b: "Your HDFC Bank account will be blocked today. Update KYC at hdfc-kyc-update.in", ok: false },
  { s: "AD-SBIUPI", b: "A/C X7730 debited by 45.0 on date 08Nov26 trf to SRI GANESH TEA STALL", ok: true },
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
    <div className="min-h-screen bg-ink-900 text-white">
      <div className="mx-auto grid max-w-6xl gap-12 px-5 py-8 lg:grid-cols-[1.15fr_1fr] lg:gap-16 lg:py-14">
        <section>
          <Logo />
          <h1 className="mt-10 text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
            Your SMS inbox already knows where your money went.
          </h1>
          <p className="mt-5 max-w-xl text-lg text-ink-300">
            Summa reads the bank and UPI alerts on your phone and turns them into a budget, scam warnings and answers you can check.
          </p>

          <div className="mt-8 rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-400">Same inbox, two jobs</div>
            <ul className="space-y-2">
              {SAMPLE_IN.map((m) => (
                <li key={m.s} className="flex items-start gap-3 rounded-xl bg-ink-800/80 p-3 text-sm">
                  <span className={`mt-0.5 shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-bold ${m.ok ? "bg-brand-500/20 text-brand-200" : "bg-red-500/20 text-red-200"}`}>
                    {m.ok ? "LEDGER" : "SCAM"}
                  </span>
                  <div className="min-w-0"><div className="text-xs text-ink-400">{m.s}</div><div className="truncate text-ink-100">{m.b}</div></div>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            {[
              { icon: PiggyBank, t: "A budget that builds itself", d: "Every UPI, card and ATM alert is parsed, categorised and totalled." },
              { icon: ShieldAlert, t: "Scam Shield", d: "Fake KYC, collect requests and parcel scams flagged with the reason why." },
              { icon: MessageSquareText, t: "Ask in plain words", d: "“How much did I spend on food this month?” Answers cite the transactions." },
              { icon: Lock, t: "Private by default", d: "Parsing runs on the server you control. Identifiers are masked before any AI call." },
            ].map(({ icon: Icon, t, d }) => (
              <div key={t} className="flex gap-3">
                <Icon className="mt-0.5 h-5 w-5 shrink-0 text-brand-400" aria-hidden />
                <div><div className="font-semibold">{t}</div><div className="text-sm text-ink-400">{d}</div></div>
              </div>
            ))}
          </div>
        </section>

        <section className="lg:pt-16">
          <div className="rounded-3xl bg-white p-6 text-ink-900 shadow-2xl sm:p-8">
            <button onClick={demo} disabled={busy !== null} className="btn-brand w-full py-3 text-base">
              {busy === "demo" ? <Spinner className="h-5 w-5 text-white" /> : <Sparkles className="h-5 w-5" />}
              {busy === "demo" ? "Reading 200+ sample messages…" : "Try the demo, no sign-up"}
            </button>
            <p className="mt-2 text-center text-xs text-ink-500">Loads a synthetic inbox through the real parser. Nothing real is used.</p>

            <div className="my-6 flex items-center gap-3 text-xs text-ink-400"><div className="h-px flex-1 bg-ink-100" />or use your own messages<div className="h-px flex-1 bg-ink-100" /></div>

            <div className="mb-5 grid grid-cols-2 rounded-xl bg-ink-50 p-1 text-sm font-semibold" role="tablist">
              {(["signup", "login"] as const).map((m) => (
                <button key={m} role="tab" aria-selected={mode === m} onClick={() => { setMode(m); setError(null); }}
                  className={`rounded-lg py-2 ${mode === m ? "bg-white shadow-card" : "text-ink-500"}`}>
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
                {mode === "signup" && <p className="mt-1 text-xs text-ink-500">At least 8 characters.</p>}</div>
              {error && <Notice tone="error">{error}</Notice>}
              <button className="btn-primary w-full py-3" disabled={busy !== null}>
                {busy === "form" ? <Spinner className="h-4 w-4 text-white" /> : <ArrowRight className="h-4 w-4" />}
                {mode === "signup" ? "Create account" : "Log in"}
              </button>
            </form>
          </div>
          <p className="mt-6 flex items-start gap-2 text-xs text-ink-400">
            <Bot className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            Summa explains your own spending. It is not a licensed financial adviser and does not move money.
          </p>
        </section>
      </div>
    </div>
  );
}
