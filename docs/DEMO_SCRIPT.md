# Demo Video Script (target 4 min 30 s, limit 5 min)

**Before recording**
- Start a fresh server: `./run.sh`. If you want to show Ask Summa, set `ANTHROPIC_API_KEY` in `.env` first and ask each question once beforehand to confirm it works.
- Browser at 1440×900, zoom 100%, bookmarks bar hidden. Close other tabs and notifications.
- Have the "check a message" text ready to paste (below).
- If no API key is available, skip scene 5 and spend the time on scenes 3 and 4. Do not fake an answer.

| # | Time | Screen | Say |
|---|---|---|---|
| 1 | 0:00–0:25 | Landing page | "Every UPI payment in India sends you an SMS. Most of us never add them up, and the same inbox is full of fake KYC and 'enter your PIN to receive money' scams. Summa reads those messages and turns them into a budget, scam warnings and answers you can check." |
| 2 | 0:25–1:15 | Click **Try the demo** → Dashboard | "This loads about 220 synthetic messages through the real parser. No prepared results. Here's November so far: money in, spent, kept. Spending is compared with the *same 13 days* of last month, not the whole month. Where it went, top merchants, and recurring payments Summa found on its own: rent, SIP, Netflix, Spotify, the electricity bill." Scroll to **What stands out**: "These are computed facts, for example a category on pace to go over budget, with its projection." (The sample inbox is randomised, so the exact items differ each run.) |
| 3 | 1:15–2:10 | Click the red banner → **Scam Shield** | "Nine messages were flagged, and none were counted as spending, even this one that looks like a debit alert. Each one says *why*: a look-alike domain, a threat to block the account, a personal mobile number posing as a bank." Paste into **Check a message**: `You received Rs 4,999 from PRIYA S. Enter your UPI PIN to receive the money. bit.ly/Rcv4999` → Check. "A PIN is only ever needed to *send* money. Summa says exactly that." |
| 4 | 2:10–2:55 | **Transactions** → search "tea" → open a tea stall payment | "Categories come from known merchants first, then a small model that reads names like 'Sri Ganesh Tea Stall'. This one is marked AI. If it's wrong, I change it once" → change category → Save → "and every past and future payment to that merchant follows." Then **Budget**: "The budget was suggested from my last two months. A one-off ₹18,499 laptop purchase was left out so it doesn't inflate Shopping. The grey bar is where each category is heading by month end." |
| 5 | 2:55–3:55 | **Ask Summa** | Click "How much did I spend on food this month compared with last month?" Wait. "The model doesn't see my database and doesn't do arithmetic. It calls typed tools; code computes every number." Click **Show evidence**: "These are the tools it called and the transactions behind the answer. And this green badge: every figure in the answer was checked against what the tools returned." Ask: "What are my subscriptions and what do they cost a year?" |
| 6 | 3:55–4:20 | **Import** page | "With your own phone: export SMS with SMS Backup & Restore and upload the file, or paste messages. Parsing and scam detection run on the server you control, and identifiers are masked before anything goes to the AI." |
| 7 | 4:20–4:30 | Dashboard | "Summa: one inbox, two jobs. Your budget, and your scam shield. Thank you." |

**After recording:** watch it once end to end, check the length is under 5:00, upload as unlisted to YouTube or as "anyone with the link" on Google Drive, and open the link in a private window to confirm it plays.
