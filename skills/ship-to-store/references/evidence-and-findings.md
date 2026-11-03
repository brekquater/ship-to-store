# Evidence, findings and status

Load this before writing any finding or document.

## What the evidence proves

| Evidence | Proves | Does NOT prove |
|---|---|---|
| SDK in a manifest/lockfile | The package is a dependency | That it ships, is initialised, or that every feature (ads, analytics, replay) is enabled |
| Dev-only dependency | Present at build/test time | That it ships in the release binary |
| Permission / purpose string declared | The app may request it | That the app actually accesses the resource, or when |
| Sensitive API call in source | A code path can access the resource | That the path is reachable, or that data leaves the device |
| URL literal | The string exists | That a request is made, what data it carries, or that it runs in production |
| Vendor documentation | What the vendor says the SDK can collect | What this app's configuration collects |
| Developer statement | What the developer says | Runtime behaviour (record as `user_confirmed`) |

Matches in test, example, mock or fixture paths are excluded from checks. Mention them only if relevant.

## Evidence types (use exactly these)

- `observed`: directly seen in repository content (a declaration, a config value, a dependency entry).
- `static_inference`: concluded from code paths (an API call implies the app may collect X).
- `vendor_documentation`: from the vendor's published docs (cite the URL and date).
- `user_confirmed`: stated by the developer in this session.
- `unknown`: not determinable from the repository. Becomes a `[TO CONFIRM: ...]` placeholder and an unresolved question.

Confidence: `high` (direct and unambiguous), `medium` (likely, but one assumption), `low` (weak signal or keyword).

## Finding format

Every significant finding has these fields (also the `findings[]` schema in `data-inventory.json`):

`id` (F1, F2, …) · `category` · `title` · `description` · `severity` · `file` · `line` (or null) · `evidence` (short, redacted, no secret values) · `evidence_type` · `confidence` · `impact` · `remediation` · `verification_status` (`unverified` | `developer_confirmed` | `fixed_pending_rescan` | `resolved`)

Severity:
- `critical`: live secret or service-role key in shipped code; personal data sent somewhere undisclosed with clear evidence; a store blocker that guarantees rejection (e.g. a crash from a missing purpose string on a used API).
- `high`: likely store rejection (no account deletion, tracking without ATT, missing privacy policy); sensitive data (health, location, children) with no disclosure or consent path.
- `medium`: disclosure inaccuracies, weak purpose strings, cleartext endpoints, tokens in plain storage, PII in logs.
- `low`: hygiene and documentation gaps.
- `info`: observations to confirm; no risk established.

Never assign severity from a package name alone. Downgrade when evidence is only `vendor_documentation` or the dependency is dev-only.

## Placeholders

Use exactly `[TO CONFIRM: what is needed]` for unknown facts: legal entity, contact, address, DPO, retention periods, legal bases, purposes not evident in code, vendor contracts, data locations, age of users, target markets. Never invent them. `verify_report.py` counts placeholders. Any document that still has them is marked **INCOMPLETE — needs business-owner input**.

## Release-readiness status (use one)

- `NOT READY: BLOCKERS FOUND`: at least one critical or high finding open.
- `READY FOR REVIEW: ITEMS TO CONFIRM`: no blockers found by static checks, but placeholders or unverified items remain.
- `TECHNICAL CHECKS PASSED: LEGAL REVIEW RECOMMENDED`: no open findings, no placeholders.

Never say "compliant", "approved", "guaranteed" or "safe to publish". Each report states that store approval and legal compliance cannot be guaranteed by a static scan.
