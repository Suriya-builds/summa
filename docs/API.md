# API Reference

Base path: `/api`. All bodies are JSON unless noted. Interactive OpenAPI docs: `http://localhost:8000/docs`.

**Authentication.** Log in or sign up to receive an `HttpOnly`, `SameSite=Strict` cookie named `summa_session`. Every endpoint except auth, `/health` and `/meta` requires it and returns `401` without it.

**Errors.** Every error is `{"detail": "<one readable sentence>"}` with a matching status: `401` not logged in, `404` not found or not yours, `409` conflict, `413` too large, `415` unsupported file, `422` invalid input, `429` rate limited, `502/503` AI provider problem.

**Cross-site protection.** `POST`, `PUT`, `PATCH` and `DELETE` requests carrying an `Origin` header from another site are rejected with `403`.

Money is returned in rupees as numbers with two decimals. Dates are ISO 8601 in Indian Standard Time.

## Auth

| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/auth/signup` | `{name, email, password}` (password ≥ 8) | `201`, sets cookie. `409` if the email exists. 10/hour per IP |
| POST | `/auth/login` | `{email, password}` | Sets cookie. 20 per 5 min per IP, 8 per 5 min per email |
| POST | `/auth/demo` | none | Creates a demo account, imports the synthetic inbox, applies suggested budgets. Demo accounts older than 24 h are deleted |
| POST | `/auth/logout` | none | Revokes the session |
| GET | `/auth/me` | none | `{user}` or `{user: null}` |

## Messages and import

| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/messages/import` | `{text, use_ai?}` | Pasted text, ≤ 2 MB. Returns an import result |
| POST | `/messages/import-file` | multipart: `file`, `use_ai?` | `.txt`, `.csv`, `.json`, `.xml` (SMS Backup & Restore). UTF-8 only |
| POST | `/messages/sample` | none | Imports a fresh synthetic inbox |
| GET | `/messages?kind=&page=&page_size=` | none | `kind`: transaction, scam, otp, promo, other |

Import result:

```json
{ "received": 3, "imported": 3, "duplicates": 0, "transactions": 1, "scams": 1, "otps": 1,
  "promos": 0, "others": 0, "llm_parsed": 0, "llm_error": null, "unparsed_money_messages": 0,
  "first_date": "2026-11-03", "last_date": "2026-11-04", "skipped_over_limit": 0 }
```

`use_ai` sends messages the rule parser could not read to Claude after masking. An AI-returned amount is accepted only if that number appears in the original message.

## Transactions

| Method | Path | Notes |
|---|---|---|
| GET | `/transactions?month=&category=&direction=&q=&min_amount=&max_amount=&sort=&page=&page_size=` | `sort`: date_desc, date_asc, amount_desc, amount_asc. Returns `items`, `total`, `total_debit`, `total_credit` |
| POST | `/transactions` | Manual entry `{date, amount, direction, counterparty, category?, note?}` |
| PATCH | `/transactions/{id}` | `{category?, note?, counterparty?, apply_to_merchant?}`. With `apply_to_merchant` (default true) the category is saved as a rule for that merchant and applied to past and future payments. Returns `also_updated` |
| DELETE | `/transactions/{id}` | |
| GET | `/transactions/export.csv?month=` | CSV download. Cells starting with `= + - @` are prefixed to prevent spreadsheet formula injection |

## Analytics

| Method | Path | Notes |
|---|---|---|
| GET | `/analytics/months` | Months with data, newest first, and the default |
| GET | `/analytics/summary?month=YYYY-MM` | Income, spend, invested, saved, savings rate, category split with change vs the same days of last month, daily series, top merchants, channels, largest expense |
| GET | `/analytics/trend` | Last six months of income, spend and investments |
| GET | `/analytics/recurring` | Payments repeating every 25–35 days at a steady amount; `kind` is subscription, bill or commitment |
| GET | `/analytics/anomalies?month=` | Payments far above that merchant's or category's normal |
| GET | `/analytics/insights?month=` | Computed facts, most actionable first, each with its numbers |
| POST | `/analytics/insights/narrative` | `{month?}`. Claude rewrites the facts as a paragraph; returns `figure_check`. Needs a key |

Definitions: **spend** is every debit except investments; **saved** is income minus spend.

## Budgets

| Method | Path | Notes |
|---|---|---|
| GET | `/budgets?month=` | Per-category limit, spent, remaining, projection and status (`ok`, `warning`, `over`, `unbudgeted`), plus daily allowance |
| PUT | `/budgets` | `{limits: {category: rupees}}`. `0` removes a budget |
| GET | `/budgets/suggestions` | Suggested limits from up to three complete months, with one-off purchases left out |

## Scam Shield

| Method | Path | Notes |
|---|---|---|
| GET | `/scam/alerts?include_dismissed=` | Flagged messages with score, level and reasons |
| POST | `/scam/check` | `{text, sender?, explain?}`. Scores any message without saving it. `explain` adds a Claude explanation |
| POST | `/scam/alerts/{id}/dismiss` | "This is genuine". If it is a real bank alert, its transaction is recorded |
| POST | `/scam/alerts/{id}/restore` | Flag again |

Verdict: `{score 0–1, level: safe|suspicious|dangerous, reasons: [{code, weight, text}], ml_probability, advice, links}`. Thresholds: suspicious ≥ 0.40, dangerous ≥ 0.70.

## Assistant

| Method | Path | Notes |
|---|---|---|
| GET | `/assistant/status` | Whether the LLM is configured, and suggested questions |
| POST | `/assistant/ask` | `{question}`. Returns `{content, citations, tools, figure_check}`. 20 per 5 min per user. `503` without a key |
| GET / DELETE | `/assistant/history` | Last 60 messages / clear |

Tools available to the model: `get_month_summary`, `search_transactions`, `spending_breakdown`, `get_budget_status`, `get_recurring_payments`, `get_unusual_transactions`, `get_scam_alerts`, `calculate`.

`figure_check`: `{checked, verified, unverified: ["₹5,000"]}`. Each money figure or percentage in the answer is matched against the numbers the tools returned.

## Account

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | `{status: "ok"}` |
| GET | `/meta` | Categories, LLM status, and held-out metrics for the two local models |
| GET | `/account/overview` | Counts and date range |
| DELETE | `/account/data` | Deletes all messages, transactions, budgets, rules and chat. Keeps the login |
| DELETE | `/account` | Deletes the account and everything in it |
