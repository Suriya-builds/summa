# Summa: your SMS inbox, turned into a money copilot

**Arthaton 2026 · Theme: AI for finance · Directions: Smart budgeting + Scam and fraud detector**

Every UPI payment, card swipe and ATM withdrawal in India produces a bank SMS. Most people never total them, and the same inbox also carries fake KYC alerts, UPI "collect" scams and parcel-fee phishing.

**Summa reads those messages and turns them into a ledger, a monthly budget, scam warnings and answers you can check.**

| What it does | How |
|---|---|
| **Reads bank and UPI SMS** from HDFC, SBI, ICICI, Axis, Kotak, Canara and others | Rule-based parser, tested on 13 transaction formats and 8 look-alike non-transactions; optional AI fallback for unusual ones |
| **Categorises every payment**, including merchants no list knows ("Sri Balaji Medicals") | Known-merchant dictionary, then a character n-gram classifier; your corrections are learned per merchant |
| **Builds a budget** from your history and projects the month end | Recurring payments counted once; everyday spending extended at its daily pace |
| **Flags scams** with the reason, and keeps them out of your spending | Explainable signal rules plus a text classifier. The classifier alone can never mark a message dangerous |
| **Answers questions** like "How much did I spend on food this month vs last?" | Claude calls typed, read-only tools over your ledger. Each figure in the answer is checked against tool output, and the transactions used are shown |
| **Finds subscriptions and unusual spends** | Interval and amount statistics |

The core features (import, categorisation, budgets, scam detection) **run without any API key**. The language model is used only for Ask Summa, AI summaries, AI scam explanations and opt-in AI parsing.

---

## Quick start

Requirements: Python 3.11+, Node 20+.

```bash
git clone https://github.com/Suriya-builds/summa.git
cd summa
./run.sh            # installs dependencies, builds the frontend, starts on http://localhost:8000
```

Open http://localhost:8000 and click **Try the demo**. It creates a throwaway account and runs about 220 synthetic SMS through the real pipeline.

To enable the AI assistant, put an Anthropic API key in `.env` (created from `.env.example` on first run) and restart:

```
ANTHROPIC_API_KEY=your-key-here
```

### Manual setup (two terminals, with hot reload)

```bash
# backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload            # http://127.0.0.1:8000, API docs at /docs

# frontend
cd frontend
npm ci
npm run dev                                         # http://localhost:5173, proxies /api to :8000
```

### Docker

```bash
docker build -t summa .
docker run -p 8000:8000 -v summa-data:/data --env-file .env summa
```

---

## Using your own messages

- **Android:** back up SMS with the "SMS Backup & Restore" app and upload the `.xml` file on the Import page. Only received messages are read.
- **Any phone:** copy bank messages and paste them, one per line. A sender prefix such as `VM-HDFCBK:` improves scam detection.
- **CSV / JSON:** any file with a `body` (or `text`/`message`) column, plus optional `sender` and `date`.

Re-importing is safe: duplicates are skipped by message fingerprint and by UPI reference.

---

## Tests

```bash
cd backend && .venv/bin/python -m pytest -q          # 69 unit and API tests
./run.sh &  node e2e/journey.js                       # browser journey on desktop and phone sizes
```

Results are in [docs/TEST_REPORT.md](docs/TEST_REPORT.md).

---

## Documentation

| Document | Contents |
|---|---|
| [PROJECT_ANALYSIS.md](docs/PROJECT_ANALYSIS.md) | The hackathon brief: requirements, rules, judging criteria, gaps |
| [PRODUCT_REQUIREMENTS.md](docs/PRODUCT_REQUIREMENTS.md) | Three approaches compared, the chosen product, requirements |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, import pipeline, where the AI is, security model |
| [API.md](docs/API.md) | Every endpoint. Live OpenAPI docs at `/docs` |
| [DATABASE.md](docs/DATABASE.md) | Schema |
| [TECH_STACK.md](docs/TECH_STACK.md) | Technology choices and why |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Running in production |
| [TEST_REPORT.md](docs/TEST_REPORT.md) | What was tested and the results |
| [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) | What it does not do, honestly |
| [DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) | A 4.5-minute demo video script |
| [PRESENTATION.md](docs/PRESENTATION.md) | Slide outline |
| [SUBMISSION_CHECKLIST.md](docs/SUBMISSION_CHECKLIST.md) | Everything needed to submit |
| [DEVELOPMENT_LOG.md](docs/DEVELOPMENT_LOG.md) | Build history |

---

## Privacy and safety

- Only synthetic data is in this repository. No real bank details, PAN numbers or keys.
- Messages are stored on the server you run. "Delete all my data" in Settings removes them.
- Before anything is sent to the language model, phone numbers, long account and reference numbers, PAN, Aadhaar, email addresses and one-time codes are masked. Merchant and payee names (including UPI handles such as `name@okaxis`) are kept so answers can name them.
- SMS text reaches the model only as tool output, never as instructions, and every tool is read-only and scoped to the signed-in user.
- Summa explains your own spending. It is not a licensed financial adviser and never moves money.

---

## Credits

The rules require crediting open-source libraries and AI APIs.

**AI API**
- [Anthropic Claude](https://www.anthropic.com/) (default model `claude-opus-5-5`) through the official `anthropic` Python SDK: Ask Summa, insight summaries, scam explanations, AI SMS parsing.

**Backend:** FastAPI, Uvicorn, SQLAlchemy, Pydantic, python-multipart, scikit-learn (with NumPy and SciPy), pytest, HTTPX.

**Frontend:** React, React DOM, React Router, Recharts, lucide-react icons, Vite, TypeScript, Tailwind CSS, PostCSS, Autoprefixer.

**Testing:** Playwright and Chromium.

All SMS samples, merchant names, people and scam messages in this repository were written for this project and are fictional.

## License

MIT
