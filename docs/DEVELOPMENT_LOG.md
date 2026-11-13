# Development Log

## 12 Nov 2026

- Read the Arthaton 2026 brief (3 pages). Wrote PROJECT_ANALYSIS.md: 10 mandatory requirements, 7 unweighted judging criteria, 8 gaps. The arthaton.com site could not be reached from the build environment, so the brief was not cross-checked against it.
- Compared three products (SMS copilot + scam shield, NSE backtester, tax helper) against the judging criteria. Chose the SMS copilot: no external data feed, AI does real work in three places, runs without a key.
- Wrote requirements, roadmap, tech stack and architecture.
- Backend: config, models (money in paise), scrypt auth with hashed session tokens, SMS splitter (text, CSV, JSON, XML), transaction parser, merchant categoriser (keywords + character n-gram model), scam detector (signal rules + text model), synthetic inbox generator, import pipeline, analytics, budgets, redaction, LLM wrapper, assistant tool loop with figure check, all API routes.
- Reviewed demo output and fixed: rent projected daily, ordinary food orders flagged as anomalies, one-off purchase inflating budget suggestions, phone-number UPI IDs parsed as Unknown, Canara `Rs:` amounts.

## 13 Nov 2026

- Worker restarted overnight; all files survived. Committed and pushed immediately.
- Backend test suite (69 tests). Found and fixed a redaction leak (reference number before a comma).
- Frontend: landing with one-click demo, dashboard, transactions, budget planner, Scam Shield, Ask Summa with evidence panel, import, settings. Responsive with a bottom nav on phones.
- Browser journey test on desktop and Pixel 7: all pages, category edit, scam check, import, logout. Fixed console noise.
- Dependency audits: Python clean; React Router upgraded from 6.28 to 7.18.5 to clear open-redirect advisories; re-tested.
- Packaging: Dockerfile (not built: no Docker daemon here), `run.sh`, `.env.example`.
- Documentation: README with credits, API, database, deployment, test report, limitations, demo script, presentation outline, submission checklist.
