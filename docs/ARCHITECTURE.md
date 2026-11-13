# Architecture

## 1. System overview

One Python process serves the JSON API and the built React app. SQLite holds all state. The only
outbound call is to the LLM provider, and only for features the user triggers.

```mermaid
flowchart LR
    subgraph Browser
        UI[React SPA]
    end
    subgraph Server["FastAPI process"]
        API[REST API /api/*]
        subgraph Pipeline["Import pipeline (local)"]
            SPLIT[Message splitter<br/>text / csv / json / xml]
            SCAM[Scam detector<br/>signals + ML]
            PARSE[Transaction parser<br/>rule engine]
            CAT[Categoriser<br/>user rules → keywords → ML]
        end
        AN[Analytics, budgets,<br/>recurring, anomalies]
        ASK[Assistant<br/>tool loop + figure check]
        RED[Redactor]
    end
    DB[(SQLite)]
    LLM[[Claude API<br/>optional]]

    UI -- cookie session --> API
    API --> SPLIT --> SCAM --> PARSE --> CAT --> DB
    API --> AN --> DB
    API --> ASK
    ASK -- typed tools --> AN
    ASK --> RED --> LLM
    PARSE -. unreadable SMS, opt-in .-> RED
```

## 2. Import pipeline

```mermaid
sequenceDiagram
    participant U as User
    participant A as API
    participant S as Scam detector
    participant P as Parser
    participant C as Categoriser
    participant D as DB
    U->>A: POST /api/messages/import (text or file)
    A->>A: split into messages, fingerprint, drop duplicates
    loop each new message
        A->>S: score(sender, body)
        S-->>A: score, level, reasons
        alt level is dangerous
            A->>D: store as scam (never parsed as a transaction)
        else
            A->>P: parse(body, received_at)
            alt transaction found
                P-->>A: amount, direction, counterparty, date...
                A->>C: categorise(counterparty, direction)
                A->>D: store message + transaction
            else
                A->>D: store as otp / promo / other
            end
        end
    end
    A-->>U: counts per kind, new transactions, flagged scams
```

A message scored as dangerous is never turned into a transaction. Scam texts often imitate debit
alerts ("Rs 4,999 will be debited, click to cancel"), and counting them would corrupt the ledger.

## 3. Where the AI is

| Component | Technique | Runs | Purpose |
|---|---|---|---|
| Scam detector | Explainable signal rules combined with a TF-IDF + logistic regression text model | Local | Risk score with reasons |
| Categoriser | User rules, then a keyword dictionary, then a character n-gram classifier over merchant names | Local | Handles merchants no dictionary lists, e.g. "SRI BALAJI MEDICALS" |
| Recurring and anomaly detection | Interval and amount statistics | Local | Subscriptions, unusual spends |
| Ask Summa | Claude with tool calling over typed analytics functions | LLM | Natural-language answers with citations |
| Figure check | Every number in an answer is matched against tool output | Local | Flags figures the model did not get from data |
| Insight narrative | Claude rewrites computed facts | LLM | Readable monthly summary |
| Fallback parser | Claude structured output | LLM, opt-in | SMS formats the rule engine cannot read |

### Ask Summa in detail

```mermaid
sequenceDiagram
    participant U as User
    participant A as Assistant service
    participant L as Claude
    participant T as Tools (analytics on the user's DB rows)
    U->>A: "How much did I spend on food last month?"
    A->>L: question + tool definitions
    L-->>A: tool_use spend_by_category(from, to)
    A->>T: run for this user only
    T-->>A: totals + transaction ids
    A->>L: tool_result (identifiers masked)
    L-->>A: answer text
    A->>A: check each figure in the answer against tool output
    A-->>U: answer, cited transactions, tools used, figure check
```

- Tools take a `user_id` from the session, never from the model, so a prompt cannot reach another
  user's data.
- The loop is capped at six tool rounds.
- The model is told to call `calculate` for any arithmetic. The figure check then verifies the
  result instead of trusting the instruction.

## 4. Backend layout

```
backend/app/
  main.py            app factory, static files, error handlers
  config.py          settings from environment variables
  db.py              engine, session, schema creation
  models.py          SQLAlchemy models
  schemas.py         request and response models
  security.py        password hashing, session tokens, rate limiter
  deps.py            current-user dependency
  routers/           auth, messages, transactions, analytics, budgets, scam, assistant, account
  services/
    splitter.py      raw text / csv / json / xml → messages
    sms_parser.py    transaction extraction
    categorizer.py   category assignment
    scam_detector.py risk scoring
    analytics.py     summaries, recurring, anomalies, insights
    budgets.py       suggestions, progress, projection
    assistant.py     tool definitions, tool loop, figure check
    llm.py           provider wrapper
    redact.py        identifier masking
    sample_data.py   synthetic inbox generator
```

## 5. Frontend layout

```
frontend/src/
  api/         typed client, one function per endpoint
  pages/       Landing, Dashboard, Transactions, Budget, Shield, Ask, Import, Settings
  components/  layout, charts, tables, states (loading / empty / error)
```

Session state lives in an HTTP-only cookie. The SPA holds no token.

## 6. Authentication and authorisation

- Passwords: scrypt with a per-user random salt.
- Sessions: 32 random bytes sent as an `HttpOnly`, `SameSite=Strict` cookie. Only the SHA-256 of the
  token is stored, so a database leak does not expose live sessions.
- Every query filters by the session's `user_id`.
- Sign-up, log-in and assistant endpoints are rate limited.

## 7. Security requirements

| Risk | Control |
|---|---|
| Cross-user data access | `user_id` filter on every query; tests assert isolation |
| Session theft through script injection | HTTP-only cookie; React escapes all rendered SMS text |
| Cross-site request forgery | `SameSite=Strict` cookie; API accepts JSON, not form posts |
| Prompt injection through SMS text | SMS content reaches the model only as tool-result data; tools are read-only and scoped to the user |
| Leaking identifiers to the LLM | Account numbers, card numbers, phone numbers, UPI IDs, PAN and Aadhaar patterns are masked |
| Malicious upload | Size cap, UTF-8 text only, XML with DTD or entities rejected |
| Secrets in the repo | `.env` is git-ignored; `.env.example` holds names only |
| Credential stuffing | Rate limit per IP on auth endpoints |

## 8. Deployment

A multi-stage Dockerfile builds the frontend, then copies it into a slim Python image. The
container listens on `$PORT`. SQLite lives on a mounted volume; set `DATABASE_URL` to use Postgres.
See `DEPLOYMENT.md`.
