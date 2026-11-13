# Product Requirements — Summa

## 1. Strategy: three approaches compared

Scores are 1–5 against the seven judging criteria in the brief, which carry equal weight because
the brief gives none. Feasibility is listed separately because it decides whether "works end to
end" is achievable at all. The scores are the engineering team's judgement, not measurements.

| Criterion | A. SMS money copilot + scam shield | B. NSE backtester + news impact | C. Tax regime helper |
|---|---|---|---|
| Real-world impact | 5 — every UPI user gets bank SMS; most never total them | 3 — useful to a small group of active traders | 4 — every salaried person, once a year |
| Relevance to theme | 5 — two of the organisers' six directions | 5 | 5 |
| Works end to end | 5 — needs only pasted text; no external data feed | 3 — depends on a market-data source and news feed | 4 |
| Use of AI | 5 — ML classifiers, LLM extraction, tool-calling Q&A with citations | 3 — the backtest itself is arithmetic; AI is a commentary layer | 2 — a calculator with an explainer |
| Creativity | 4 — treats one inbox as both a ledger and a threat feed | 3 | 2 |
| Originality | 3 — SMS budgeting exists; the grounded-answer and scam combination is less common | 2 — the most common finance hackathon entry | 2 |
| Quality of demo | 5 — paste messages, watch a budget and scam warnings appear | 4 — charts demo well | 3 |
| **Total (of 35)** | **32** | **23** | **22** |
| Feasibility in 10 days | High | Medium — data sourcing is the risk | High, but wrong tax figures would mislead users |

### Selected: A — Summa

Reasons, in order of weight:

1. **It needs no external data feed**, so the demo cannot fail because a third-party API is down.
2. **The AI does real work in three places** (categorising, scam scoring, answering questions),
   which matters with a judging panel made up mostly of AI engineers.
3. **It runs without an API key.** Parsing, categorising, budgeting and scam scoring are local.
   A judge who clones the repo sees a working product with no account anywhere.
4. Approach C carries a correctness risk the others do not: tax slabs change every budget, and
   confidently wrong tax advice is worse than none.

## 2. Product summary

**Summa reads the bank and UPI SMS already sitting in your inbox and turns them into a ledger, a
monthly budget, scam warnings and answers you can check.**

Summa (Latin: "the sum total") targets students and early-career earners in India who pay by UPI
dozens of times a week and have no idea where the month went.

### Differentiators

- **One inbox, two jobs.** The same messages produce the budget and expose the scams.
- **The language model never does arithmetic.** It calls typed tools; code computes every number.
  Each answer lists the transactions it is based on.
- **Local first.** No message leaves the machine unless the user asks a question or turns on LLM
  parsing, and account numbers, phone numbers and UPI IDs are masked before anything is sent.
- **Every scam verdict is explained** with the specific signals that fired.

## 3. Users and journeys

| Persona | Need |
|---|---|
| Student on a monthly allowance | "Where did ₹8,000 go?" and "Can I afford this?" |
| First-job earner | A budget that builds itself, and subscriptions they forgot about |
| Anyone with a phone | "Is this message from my bank or a scam?" |

Primary journey: sign up or try the demo → import SMS (paste, upload or sample inbox) → see the
dashboard → review flagged scams → accept or edit the suggested budget → ask questions.

## 4. Functional requirements

Priority: P0 = required for submission, P1 = included if P0 is stable.

| ID | Requirement | Priority |
|---|---|---|
| F1 | Sign up, log in, log out with email and password. Each user sees only their own data. | P0 |
| F2 | One-click demo account loaded with a synthetic inbox | P0 |
| F3 | Import SMS by pasting text, uploading a `.txt`/`.csv`/`.json` file, or generating a sample inbox | P0 |
| F4 | Classify each message: transaction, scam suspect, OTP, promotion, other | P0 |
| F5 | Extract from transaction SMS: amount, direction, counterparty, channel, account tail, balance, date, reference | P0 |
| F6 | Skip duplicates on re-import | P0 |
| F7 | Categorise transactions; a user correction is remembered and applied to that merchant from then on | P0 |
| F8 | Dashboard: income, spend, savings rate, category split, daily trend, top merchants | P0 |
| F9 | Detect recurring payments and subscriptions | P0 |
| F10 | Flag unusually large transactions | P0 |
| F11 | Suggest a monthly budget from history; user can edit; show progress and month-end projection | P0 |
| F12 | Scam shield: risk score and reasons for inbox messages, plus a checker for any pasted message | P0 |
| F13 | Ask Summa: natural-language questions answered from the user's ledger, with cited transactions | P0 |
| F14 | Monthly insights: computed facts, rewritten as a short narrative when an LLM is configured | P0 |
| F15 | LLM fallback parser for transaction SMS the rule engine cannot read | P1 |
| F16 | Edit or delete a transaction; export CSV; delete all my data | P1 |

## 5. Non-functional requirements

| ID | Requirement |
|---|---|
| N1 | Runs from a clean clone with documented commands; no paid service required for F1–F12 |
| N2 | No secrets in the repo; configuration through environment variables |
| N3 | Passwords hashed with a memory-hard function; sessions in HTTP-only cookies |
| N4 | Sensitive identifiers masked before any text is sent to an LLM |
| N5 | Responsive from 360 px phones to desktop |
| N6 | Loading, empty and error states on every screen |
| N7 | Automated tests for the parser, classifiers, analytics, auth and API |
| N8 | Only synthetic data in the repository |

## 6. Out of scope

- Reading SMS directly from a phone (needs a native Android app and SMS permission).
- Bank account linking or the Account Aggregator framework.
- Investment, tax or credit advice.
- Real payments of any kind.

## 7. Success measures for the submission

- A new user reaches a populated dashboard in under a minute using the sample inbox.
- The rule parser extracts amount and direction correctly on every format in the test corpus.
- No answer from Ask Summa contains a figure that was not returned by a tool.
- The demo runs start to finish without a network connection, apart from Ask Summa.
