# Tech Stack

Chosen for build speed, a one-command run for judges, and as few moving parts as possible.

| Layer | Choice | Why | Rejected alternative |
|---|---|---|---|
| Backend | Python 3.11+ with FastAPI | Typed request/response models, automatic OpenAPI docs, same language as the ML code | Node/Express — would split ML into a second service |
| Database | SQLite through SQLAlchemy 2 | Zero setup for judges; `DATABASE_URL` switches to Postgres for hosting | Postgres only — adds a setup step to every clone |
| ML | scikit-learn (TF-IDF + logistic regression) | Small, fast, explainable, trains in seconds on CPU | Fine-tuned transformer — too heavy to justify for short SMS text |
| LLM | Claude through the official `anthropic` SDK | Reliable tool calling; allowed by the brief | Hard dependency on any LLM — the core must run with no key |
| Frontend | React 18 + React Router 7 + TypeScript + Vite | Fast builds, typed API client | Next.js — server rendering adds nothing here |
| Styling | Tailwind CSS | Consistent responsive UI quickly | Component library — more weight than needed |
| Charts | Recharts | Declarative, responsive | D3 by hand — slower to build |
| Auth | scrypt (Python standard library) + server-side sessions in an HTTP-only cookie | No extra dependency; sessions can be revoked | JWT in localStorage — readable by any injected script |
| Tests | pytest + FastAPI TestClient; Playwright for browser journeys | Covers units, API and real UI | — |
| Packaging | One Docker image: the API also serves the built frontend | One process to deploy | Separate frontend hosting — two deployments, CORS |

## Dependencies kept out on purpose

- No ORM migration tool: the schema is created at start-up. Acceptable for a hackathon; listed in
  known limitations.
- No task queue: imports are parsed in the request. A 2,000-message import takes well under a second.
- No vector database: the ledger is structured, so questions are answered with typed tools and SQL,
  not embeddings.
- No LangChain or agent framework: the tool loop is about a hundred lines against the SDK.

## Credits required by the brief

Open-source libraries and AI APIs must be credited in the README. The list is maintained there.
