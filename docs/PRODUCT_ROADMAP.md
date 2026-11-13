# Product Roadmap

Dates are fixed by the brief: registration closes 15 Nov 2026, submission closes 22 Nov 2026 at
11:59 PM IST.

## Milestones

| # | Milestone | Target | Owner | Exit condition |
|---|---|---|---|---|
| 1 | Analysis, strategy, architecture | 12 Nov | Engineering | Documents in `docs/` |
| 2 | Backend core: auth, import, parser, categoriser, analytics, budgets, scam shield | 12 Nov | Engineering | API tests pass |
| 3 | Frontend: all screens wired to the API | 12–13 Nov | Engineering | Browser journeys pass |
| 4 | Ask Summa and LLM parsing | 13 Nov | Engineering | Tool loop tested; live test once a key is supplied |
| 5 | QA, security review, fixes | 13 Nov | Engineering | Test report complete, no critical findings open |
| 6 | **Team registration** | **by 15 Nov** | **Product owner** | Confirmation from the organisers |
| 7 | Product owner review and change requests | 13–18 Nov | Product owner | Sign-off |
| 8 | Optional hosted deployment | 18–19 Nov | Both | Public URL verified |
| 9 | Demo video recorded (under 5 minutes) | 19–20 Nov | Product owner | Link works in a private window |
| 10 | Submit repo link + video link | 21 Nov (one day of margin) | Product owner | Submission acknowledged |

## Build order and why

1. **Parser first.** Everything downstream depends on correct amounts and directions.
2. **Analytics and budgets next**, because they need only parsed transactions.
3. **Scam shield** in parallel: it reads the same messages and touches nothing else.
4. **LLM features last.** They are additive, and the product must stand without them.

## After the hackathon

- Android companion app that reads SMS on the device with permission.
- Account Aggregator integration as a second data source.
- Scam model trained on real reported messages, with user feedback.
- Shared budgets for flatmates and families.
- Hindi, Tamil and other Indian languages for the interface and the assistant.
