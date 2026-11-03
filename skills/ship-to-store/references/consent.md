# Consent and user-choice recommendations

Load at workflow step 9 when the inventory contains analytics, ads, attribution, session replay, marketing messages, sensitive data, precise location, AI sharing, or children. Recommend interfaces only when findings support them. **Never add a generic "I accept the Privacy Policy" checkbox by default.** Acknowledging a notice is not consent and should not be presented as consent.

## Distinguish the mechanisms

| Mechanism | What it is | Typical use | Not a substitute for |
|---|---|---|---|
| Privacy notice | Information given at or before collection | Always: policy link at sign-up and in settings | Consent |
| Terms acceptance | Contract with the user | Account creation, paid features | Consent to optional processing |
| Consent to specific processing | Specific, informed, freely given, unbundled, withdrawable agreement to one purpose | Where consent is the legal basis (e.g. GDPR optional analytics, DPDP default basis) | Notice or terms |
| Marketing consent | Opt-in (or opt-out where law allows) to promotional email/SMS/push | Newsletters, promotional push | Transactional messages |
| Tracking consent | Apple ATT prompt; EU/UK device-access consent; US opt-out of sale/sharing | Ads personalisation, attribution, cross-app tracking | Each other: ATT does not satisfy EU consent and vice versa |
| Cookie consent | Consent for non-essential cookies/storage | Web apps, controlled webviews | App SDK consent (handled separately) |
| OS permission prompt | Platform authorisation for a resource | Camera, location, contacts | Legal consent; Play prominent disclosure where required |
| Parental consent | Verifiable consent from a parent | Child users | Child's own consent |

## Decision procedure (per processing activity)

For each data item or SDK purpose found:
1. **Necessity.** Is it strictly necessary for a feature the user requested (e.g. location for "stores near me")? If yes: notice plus the OS permission is usually enough. Consent is usually not the right basis, but the permission must be requested in context.
2. **Optional purposes** (analytics, ads, attribution, replay, AI features, marketing): these must be optional. Declining must not block unrelated core features (Apple 5.1.2(i) forbids requiring tracking, notifications or location to use the app).
3. **Jurisdiction and platform overlay**, using statuses from `jurisdictions.md`:
   - EU/UK `confirmed`/`potential` + device storage/access by a non-essential SDK → **opt-in before SDK initialisation** (ePrivacy Art. 5(3)).
   - iOS + tracking → **ATT** before tracking (Apple 5.1.2(i)).
   - California `confirmed` + selling/sharing → **opt-out link and preference-signal handling** (not opt-in).
   - India (DPDP, once in force) → notice + consent unless a legitimate use applies. Under 18 → parental consent; no targeted ads to children.
   - Personal data to third-party AI → **explicit permission** before the first send (Apple 5.1.2(i)).
   - Sensitive data (health, biometrics, sexual orientation, precise location in some US states) → explicit consent or legal review.
   - Play restricted permissions (background location etc.) → **prominent disclosure + affirmative consent** before the OS prompt.
4. If unresolved, choose `further legal review` rather than guessing.

## Recommendation content

In chat, give each recommendation as one or two lines: activity → mechanism, when, and what happens if the user declines, with its basis. Use the full field list below only when the developer asks for a consent plan file (`consent-recommendations.md`).

- **Activity:** what happens (e.g. "Firebase Analytics events").
- **Data involved:** categories from the inventory.
- **Purpose:** why it is processed (`[TO CONFIRM]` if not evident).
- **Recipient/vendor:** who receives it.
- **Mechanism:** none beyond notice | notice + OS permission | opt-in consent | opt-out | ATT | prominent disclosure | parental consent | further legal review.
- **When:** e.g. "before SDK initialisation on first launch", "just before first AI request".
- **Optional?** yes/no, and why.
- **If the user declines:** concrete behaviour, e.g. SDK not initialised, non-personalised ads, feature hidden, manual address entry.
- **Basis:** jurisdiction status + platform rule (with source), stated as "potentially required", never as a legal conclusion.
- **Evidence:** file:line or SDK id. **Confidence:** high/medium/low.

## Implementation notes (only if the developer asks for code)

- Gate SDK initialisation on stored consent state. Many SDKs support default-off flags (e.g. Firebase Analytics collection flags; Google UMP for EEA/UK ads consent). Confirm exact flags in vendor docs before recommending them.
- Store a consent record: purposes, choice, timestamp, notice version. Provide withdrawal in settings that is as easy as giving consent, and propagate withdrawal to SDKs.
- Avoid dark patterns: no pre-ticked boxes, accept and reject equally prominent, no repeated nagging, no bundling with terms.
- Consent, ATT and prominent-disclosure flows change user-facing behaviour. Ask before building them (SKILL.md step 5). Flipping an existing SDK to default-off until a choice exists is part of the same change.

## User rights and deletion

Map rights only for regimes marked `confirmed`/`potential`: access, correction, deletion, portability, objection/opt-out, consent withdrawal, appeal/grievance. Account deletion must also meet Apple 5.1.1(v) and Play's in-app + web-link rules. Do not promise deletion from backups or vendors unless the process supports it. Disclose legally retained data.
