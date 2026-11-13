# Test Report

Last run: 13 Nov 2026, in the test environment (Linux, Python 3.13, Node 22, Chromium via Playwright).
Every result below was produced by a command that was actually run. Nothing is estimated.

## Summary

| Suite | Command | Result |
|---|---|---|
| Backend unit + API tests | `cd backend && .venv/bin/python -m pytest -q` | **69 passed, 0 failed** on Python 3.11 and on Python 3.13 |
| Frontend type check + production build | `cd frontend && npm run build` | **Passed** |
| Browser journey, desktop 1440×900 and Pixel 7 | `node e2e/journey.js` against the production build | **Passed**, 0 console errors or warnings, 0 server 5xx, no horizontal overflow on any page |
| Python dependency audit | `pip-audit -r backend/requirements.txt` | **No known vulnerabilities** |
| npm dependency audit (runtime) | `npm audit --omit=dev` | **0 vulnerabilities** (after upgrading React Router, see below) |
| Secret scan | `git grep` for key patterns | **None found** |
| Docker image | `docker build` | **Not run**: no Docker daemon in the test environment |
| Ask Summa against the live Claude API | | **Not run**: no API key was available. The tool loop is tested with a stubbed model |

## What the backend tests cover

| File | Tests | Covers |
|---|---|---|
| `test_parser.py` | 24 | 13 bank formats (HDFC, SBI, ICICI, Axis, Kotak, Canara, NEFT, ATM, credit card, refund) parse to the right amount, direction and payee. 8 look-alikes are rejected: OTP, "will be debited" scam, promo cashback, collect request, card statement, bill-paid notice, declined card, personal chat. Balance not mistaken for amount; date and time extraction; future dates ignored |
| `test_splitter.py` | 6 | Plain text with sender prefix, pipe format, CSV, JSON, SMS Backup & Restore XML (received only), XML entity rejection, CSV without a body column |
| `test_scam.py` | 14 | 5 scam types flagged dangerous; 5 genuine bank, OTP and booking messages scored safe; negated "never share your OTP" is not a signal; official bank domain not flagged; the text model alone cannot reach "dangerous"; metrics are reported |
| `test_assistant.py` | 9 | Safe arithmetic evaluator accepts arithmetic and rejects code, names and huge exponents; figure check passes real figures and flags an invented one; full tool loop with a stubbed model: the model's attempt to pass `user_id: 999` is ignored, citations are the user's own Netflix payments, figure check passes; 503 without a key; invalid tool arguments raise |
| `test_api.py` | 16 | Signup, login, logout, duplicate email, wrong password; readable validation errors; 401 on protected routes; import counts and re-import de-duplication; scam "will be debited" message not counted as spending; **user A cannot read, edit or delete user B's transactions**; dashboard totals add up (income − spend = saved; category spend sums to total); category correction updates other payments and future imports; budget save and invalid category; scam check and "this is genuine"; CSV formula injection escaped; cross-site POST blocked; binary upload rejected; delete-all-data; identifier redaction |

## Model evaluation

Both local models are trained at start-up on synthetic data written for this project and evaluated on a held-out set built from different templates or name tokens.

| Model | Held-out size | Result |
|---|---|---|
| Scam text classifier | 360 messages (12 scam and 12 genuine templates never seen in training) | Precision 92.2%, recall 98.3%, F1 95.2% |
| Merchant category classifier | 686 names built from tokens absent from training | Accuracy 93.2% |

**These figures do not measure real-world accuracy.** The data is synthetic. They show that the models generalise past their exact training strings, nothing more.

Combined detector (rules + model) on the same held-out scam set, measured during development: 163 of 180 scams dangerous, 7 suspicious, 10 missed (all one parcel template, since fixed by a new rule); 180 of 180 genuine messages safe.

## Browser journey (e2e/journey.js)

On both desktop and phone:
landing page → "Try the demo" → dashboard renders insights → Transactions → Budget → Scam Shield → Ask → Import → Settings, with a screenshot of each.

Desktop only, additionally: open a Zomato payment and change its category (saved message shown); paste a "enter UPI PIN to receive" message in the scam checker (correct reason shown); paste the example into Import (result card shown); log out (returns to the landing page).

## Defects found and fixed during testing

| # | Found by | Defect | Fix |
|---|---|---|---|
| 1 | Unit test | A reference number followed by a comma was not masked before AI calls | Redaction lookahead now allows trailing punctuation |
| 2 | Manual run of the parser | `Rs:150.00` (Canara) not recognised; "reference number is …" not captured | Amount and reference patterns widened; covered by tests |
| 3 | Manual run of the pipeline | A UPI ID starting with a phone number (`9845012345@ybl`) became "Unknown" | UPI IDs are accepted as payees before other filters |
| 4 | Review of demo output | Rent was projected at 2.3× its value (a once-a-month payment extrapolated daily) | Recurring payments counted once in projections |
| 5 | Review of demo output | Ordinary ₹500 food orders flagged as "unusual" | Anomaly rule now uses per-merchant history, an outer-fence test and a ₹1,000 floor |
| 6 | Review of demo output | A one-off ₹18,499 purchase inflated the suggested Shopping budget | One-off purchases are excluded from suggestions and listed |
| 7 | Browser test | Logged-out landing page logged a 401 error in the console | `/auth/me` returns `{user: null}` |
| 8 | npm audit | React Router 6.28 had high-severity open-redirect advisories | Upgraded to 7.18.5; journey re-run and passed |
| 10 | Self-review on Python 3.11 | The backend did not start on Python 3.11 (f-string syntax legal only from 3.12) | Rewritten; suite run on 3.11 |
| 9 | Screenshot review | A stationery shop was labelled a "subscription" | Education payments are no longer called subscriptions |

## How to reproduce

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/python -m pytest -q
cd .. && ./run.sh            # in one terminal
node e2e/journey.js          # in another; needs Playwright (npm i -g playwright && npx playwright install chromium)
```
