# Presentation Outline (7 slides)

The brief does not require slides. Use this if a live pitch or a slide in the video helps.

1. **The problem.** UPI handles billions of payments a month, and each one sends an SMS that nobody totals. The same inbox carries fake KYC, parcel-fee and "enter PIN to receive" scams. Two problems, one data source.

2. **Summa.** Paste or upload your SMS. Get a ledger, a budget, scam warnings and answers. One inbox, two jobs.

3. **How it works.** Diagram from ARCHITECTURE.md: splitter → scam detector → parser → categoriser → database → analytics → assistant. Scam messages never reach the ledger.

4. **Where the AI is, and why it is trustworthy.**
   - Local models: scam text classifier, merchant category classifier (held-out scores, synthetic data, stated as such).
   - Claude with typed, read-only tools. It never does arithmetic. Every figure is checked against tool output and the cited transactions are shown.
   - Identifiers masked before any AI call. Works without a key.

5. **Demo.** (Video or live: dashboard → Scam Shield → category correction → Ask Summa with evidence.)

6. **Impact and what's next.** For students and first-job earners who pay by UPI daily. Next: Android companion app reading SMS on-device, Account Aggregator data, Indian languages, a scam model trained on reported real messages.

7. **Honest limits and credits.** Synthetic training data, parser coverage, needs a key for the assistant. Built with FastAPI, React, scikit-learn and the Claude API, all credited in the README.
