# Optional: developer-run runtime checks

Load only when the developer asks how to confirm runtime behaviour. Ship-to-Store never runs the app itself. These are steps the **developer** performs on a test build with synthetic data, in an environment they control.

## Journeys to test

| Journey | Consent state | Expected |
|---|---|---|
| Fresh install, first launch | none | No optional SDK traffic (analytics, ads, attribution, replay) before the required choice |
| Decline optional processing | declined | Optional SDKs stay disabled; core features work |
| Accept, then withdraw | accepted → withdrawn | Optional traffic stops after withdrawal |
| Permission denied | denied | No fallback collection; alternative offered (e.g. manual entry) |
| AI feature | as designed | Disclosure and permission shown before the first request to the AI provider |
| Account deletion | account exists | Account and associated data deleted; sessions revoked |

## How

Use the developer's own proxy or platform tools (e.g. Xcode network instruments, Android Studio Network Inspector, an intercepting proxy on a test device). Record per request: hostname, journey, consent state, data categories (not values), and whether it was HTTPS.

## Interpretation

- An observed request is confirmed only for that build, journey and configuration.
- No request observed does not prove that none occurs elsewhere.
- Server-side and SDK-backend processing is not visible from the device.
- Redact tokens, cookies and personal data from any notes shared with Claude.

Feed results back as `user_confirmed` or `runtime_verified` evidence in `data-inventory.json`.
