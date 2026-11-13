# Project Analysis — Arthaton 2026

Source: `Arthaton_2026_Event_Brief.pdf` (3 pages, read in full on 12 Nov 2026).
The brief says it was compiled from arthaton.com. That website could not be reached from the
test environment (network policy), so nothing here has been cross-checked against the live site.

## 1. Problem statement

> Build an AI application that helps people or businesses make better money decisions, such as
> managing a monthly budget, understanding investments or analysing the markets.

- **Theme:** AI for finance.
- **Category:** open-ended applied AI / fintech product build. Teams choose their own direction.
- **Audience for the product:** "people or businesses" in India (the brief's examples are UPI,
  bank SMS, NSE, SIPs, GST, old vs new tax regime).

### Directions suggested by the organisers (optional)

| Direction | Organisers' example |
|---|---|
| Smart budgeting | Turn UPI and bank SMS alerts into a monthly budget and spending insights |
| Investing and portfolio guide | Explain SIPs, index funds and FDs, and flag risk across a portfolio |
| Trading and market insights | Backtest strategies on historical NSE data or track how news moves a stock |
| Tax helper | Explain old vs new regime and deductions in plain words |
| Scam and fraud detector | Flag fake UPI collect requests, phishing messages and suspicious transactions |
| Small business finance | Automate GST invoices, cash-flow forecasts and loan or EMI planning |

## 2. Mandatory requirements

| # | Requirement | Source | Who does it |
|---|---|---|---|
| M1 | Register the team (team details + college verification) **by 15 Nov 2026** | p.1, p.2 | **Product owner** |
| M2 | The product is an AI application for finance | p.1 | Engineering |
| M3 | All source code in a **public GitHub repository** | p.2 | Engineering (repo is already public) |
| M4 | README explains what it does and how to run it | p.2 | Engineering |
| M5 | Open-source libraries and AI APIs are **credited in the README** | p.2 | Engineering |
| M6 | **Demo video of the working app, under 5 minutes** | p.2 | **Product owner** (script provided) |
| M7 | Submit repo link + video link through the emailed link **before 22 Nov 2026, 11:59 PM IST** | p.2 | **Product owner** |
| M8 | Project is the team's own work | p.2 | Both |
| M9 | No real bank details, passwords, PAN numbers or broker API keys in the repository | p.2 | Engineering |
| M10 | Trading projects: historical data or paper trading only | p.2 | Not applicable to the chosen product |

"Submissions missing a GitHub repository or a demo video will not be judged."

## 3. Technical constraints and restrictions

- No restriction on language, framework, hosting or AI provider.
- AI APIs (ChatGPT, Claude, Gemini and others) and open-source libraries are allowed, with credit.
- Data: "sample, synthetic or public market data is fine and preferred."
- Secrets and personal financial identifiers must never be committed.
- A hosted deployment is **not** required. The brief asks for a repo and a video.

## 4. Deadlines and milestones

| Date | Event |
|---|---|
| 15 Nov 2026 | Registration closes. One registration per team, filled by the team lead. |
| After 15 Nov | Submission link emailed to registered team leads |
| 22 Nov 2026, 11:59 PM IST | Submission deadline. Late entries are not accepted. |
| By 30 Nov 2026 | Results and certificates emailed |

As of 12 Nov 2026: 3 days to registration, 10 days to submission.

## 5. Judging criteria

Seven criteria are listed. **No weightage is given**, so they are treated as equal.

1. Real-world impact
2. Relevance to the theme
3. Works end to end
4. Use of AI
5. Creativity
6. Originality
7. Quality of the demo

### Who judges

| Judge | Role | Company |
|---|---|---|
| Pawan Nagwani | Senior Engineer, Search AI | Google |
| Kumar Pallav | Member of Technical Staff | Perplexity |
| Richa Agrawal | Senior Principal Engineer | Cadence |
| Pravesh Agrawal | Research Scientist | Mistral AI |
| Viola Chen | Senior Research Associate | Bernstein |
| Manoj Sarda | Co-founder | Elimentary |

Reading of the panel (an inference, not stated in the brief): four of six work on AI systems,
two of them on search and answer engines. A thin chat wrapper is unlikely to score on "Use of AI".
Answers that are grounded in data and show their evidence should land well. One judge is a
finance researcher, so numbers have to be right.

## 6. Prizes

₹10,000 / ₹5,000 / ₹3,000, paid once per team. Every participant with a valid submission gets a
certificate. Selected apps are featured on the Arthaton website.

## 7. Eligibility and participation rules

- Currently enrolled college students in India. Team members can be from different colleges.
- Every member verified by official college email or a photo of a valid college ID.
- Solo or up to 3 members. One registration per team.
- The registration form needs a Google sign-in. Each account can register once.

## 8. Resources and datasets

None are provided. The brief only says sample, synthetic or public data is preferred.

## 9. Links

- Website: https://arthaton.com/
- Registration form: https://forms.gle/vV6HC4824Gw6aCB16
- Contact: hello@arthaton.com (replies within two working days)
- Industry partners: Elimentary and Bondio

## 10. Missing or ambiguous information

| # | Gap | Impact | How it is handled |
|---|---|---|---|
| A1 | No weightage for the judging criteria | Cannot optimise for one criterion | Treat all seven equally |
| A2 | "Valid submission is decided by the judges" — no definition | Unknown minimum bar | Meet every stated requirement; make the app run from a clean clone |
| A3 | "The team's own work" is not defined further | Minor | Libraries and the AI API are credited in the README as the rules require |
| A4 | No rule on whether a live hosted URL is expected | Could affect "works end to end" | Ship a one-command local run and a Docker image; hosting is optional |
| A5 | Demo video format, hosting and audio language are not specified | Minor | Unlisted YouTube or Drive link, English narration, under 5 minutes |
| A6 | No statement on whether judges will run the code themselves | Setup must not depend on a paid key | Core features run with no API key; the LLM features switch on when a key is present |
| A7 | Whether a project may combine two suggested directions | None expected ("teams are free to pick their own") | Combining is treated as allowed |
| A8 | Whether the repository must stay unchanged after the deadline | Minor | Tag the submitted commit |

## 11. Actions only the product owner can take

1. **Register by 15 Nov 2026** using the form above (Google sign-in + college verification).
   Without this the project cannot be submitted, whatever state the code is in.
2. Confirm eligibility for every team member (currently enrolled, verifiable).
3. Record the demo video (a script is in `docs/DEMO_SCRIPT.md`).
4. Submit both links before 22 Nov, 11:59 PM IST.
