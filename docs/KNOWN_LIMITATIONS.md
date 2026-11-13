# Known Limitations

Stated plainly so judges and users know what to expect.

## Data and accuracy

- **The models are trained on synthetic data.** The scam and merchant classifiers have never seen real SMS. Their held-out scores show generalisation within synthetic data, not real-world accuracy. The scam verdict is driven mainly by explainable rules for that reason.
- **The parser covers common formats, not all of them.** It is tested on 13 formats from major banks. Regional banks, wallets and new formats may not parse. Those messages are counted as "mentioned money but not recognised", and the opt-in AI parser can read them when a key is configured.
- **Scam detection can be wrong in both directions.** A new scam wording with no link, number or known tactic may score safe. A genuine message from an unregistered number that mentions KYC may be flagged. Users can mark any flag as genuine.
- **Transfers between your own accounts** count as spending in one account and income in the other.
- **Categories are a best guess** for merchants not in the dictionary. Each AI-assigned category is labelled "AI" in the list and can be corrected; corrections apply to that merchant from then on.
- **Dates without a year or time** fall back to the time the SMS was received. Pasted text without timestamps uses the date in the message, or today.

## AI assistant

- **Needs an Anthropic API key**, which costs money per question. Without one, Ask Summa and AI summaries are disabled and everything else works.
- **Not tested against the live API in the test environment** (no key was available). The tool loop, tool scoping and figure check are tested with a stubbed model.
- **The figure check flags, it does not prevent.** A figure the model did not get from a tool is shown to the user as unverified; the answer is not blocked.
- **Not financial advice.** The assistant is instructed not to recommend investments, loans, insurance or tax positions.

## Product scope

- No direct reading of SMS from a phone; messages are pasted or uploaded. A native Android app would be needed.
- No bank linking or Account Aggregator integration.
- English only.
- No multi-currency support; amounts are rupees.

## Engineering

- **No database migrations.** The schema is created at start-up. A schema change on an existing database needs a manual migration.
- **Single instance.** Rate limits live in process memory and SQLite has one writer. Scaling out needs Postgres and a shared rate-limit store.
- **No email verification or password reset.**
- **The Docker image was not built or run** in the test environment (no Docker daemon). The non-Docker run path was tested.
- **No hosted deployment** was made or verified.
- **Demo accounts** are cleaned up only when another demo account is created, after 24 hours.
