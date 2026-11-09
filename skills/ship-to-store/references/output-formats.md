# Output documents (only on request)

The default output is the chat report in SKILL.md. Write files **only when the developer asks**, and **only the ones they ask for**. "Write it up" with nothing more specific means `audit-report.md` alone. Ask where to put them; default to `<app root>/ship-to-store-report/` and offer to gitignore it. Each Markdown file starts with:

```
> Ship-to-Store · generated <YYYY-MM-DD> · scanner <version> · status: <COMPLETE | INCOMPLETE — needs business-owner input | NEEDS LEGAL REVIEW>
> Static analysis of repository contents. It cannot observe runtime behaviour and does not guarantee store approval or legal compliance.
```

| File | When asked for | Owner review |
|---|---|---|
| `audit-report.md` | "full report", "write it up" | — |
| `remediation-checklist.md` | "checklist" | Developer |
| `data-inventory.json` | "data inventory", or as the evidence behind other files | Developer |
| `sdk-inventory.md` | "SDK list" | Developer |
| `app-store-disclosures.md` | "App Privacy answers" (iOS only) | Business owner |
| `google-play-data-safety.md` | "Data safety answers" (Android only) | Business owner |
| `consent-recommendations.md` | "consent plan" | Business owner + legal |
| `google-play-policy-matrix.md` | "policy matrix": one row per area in `google-play.md`, with policy, source URL, status, severity, file:line, evidence, fix, whether fixed, and test evidence | Developer |
| `privacy-policy-draft.md` | "privacy policy" when none exists (see `privacy-policy.md`) | Business owner + legal |

## audit-report.md

1. **Release readiness:** status from `evidence-and-findings.md`, blockers count, three-line summary.
2. **App profile:** frameworks, platforms, identifiers, scanner coverage (files scanned, skipped, parse errors, limits hit).
3. **Findings table:** ID · Severity · Category · Title · File:line · Evidence type · Confidence · Remediation (short). Ordered by severity. Full fields go in `data-inventory.json`.
4. **Data and third parties:** short summary with links to `sdk-inventory.md` and `data-inventory.json`.
5. **Jurisdictions:** the table from `jurisdictions.md`.
6. **Platform disclosures:** links to the Apple and Play files plus mismatches found.
7. **Unresolved questions:** numbered and concise. Each says which document it blocks.
8. **Method and limits:** static scan, sources and check dates, what was not verified.

## data-inventory.json

```json
{
  "schema": "ship-to-store/data-inventory/v1",
  "generated_at": "YYYY-MM-DD",
  "app": {"name": "…", "platforms": ["ios", "android"], "frameworks": ["expo"]},
  "scan_fingerprint": "<scan.json fingerprint>",
  "data_items": [{
    "id": "D1", "category": "precise_location", "description": "Location for nearby stores",
    "sources": ["src/App.tsx:20"], "purpose": "App functionality", "recipients": ["first party", "Google (Firebase)"],
    "destination": "api.example.com", "optional": "yes|no|unknown", "linked_to_user": "yes|no|unknown",
    "used_for_tracking": "yes|no|unknown", "retention": "[TO CONFIRM: retention period]",
    "evidence_type": "observed|static_inference|vendor_documentation|user_confirmed|unknown",
    "confidence": "high|medium|low", "verification": "unverified|developer_confirmed|runtime_verified"
  }],
  "findings": [{
    "id": "F1", "category": "account_deletion", "title": "…", "description": "…", "severity": "critical|high|medium|low|info",
    "file": "path or null", "line": 12, "evidence": "short, redacted", "evidence_type": "…", "confidence": "…",
    "impact": "…", "remediation": "…", "verification_status": "unverified|developer_confirmed|fixed_pending_rescan|resolved"
  }],
  "unresolved_questions": ["…"]
}
```
Use the scanner's category keys (`data_leads[].category`). Use `other` with a description if none fits.

## sdk-inventory.md

| SDK / vendor | Category | Direct / transitive / dev-only | Possible data (vendor docs) | Confirmed in code? | Destinations seen | Tracking capable | Docs (checked) |
|---|---|---|---|---|---|---|---|

Then: unclassified endpoint hosts (first-party or unknown) with locations, and "possible international transfers" with placeholders.

## app-store-disclosures.md

Table per Apple data type: Collected? · Purposes · Linked to user? · Used for tracking? · Source (SDK/code) · Confidence. Then: ATT decision, privacy manifest status, purpose-string review, account deletion, privacy policy URL, review notes and demo account, items to confirm.

## google-play-data-safety.md

Table per Play data type: Collected? · Shared? (with whom) · Required/optional · Purposes · Ephemeral? · Source · Confidence. Then: encrypted in transit (cite any cleartext flags), deletion request mechanism + web URL, sensitive-permission declarations, Advertising ID answer, target API status, items to confirm.

## remediation-checklist.md

Grouped: **Blockers** (critical/high) → **Before submission** (medium) → **Hygiene** (low). Each item is a checkbox with the finding ID, file:line, the concrete fix, and how to verify it (usually "re-run `/ship-to-store`; check <ID> is gone").
