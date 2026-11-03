# Privacy policy drafting

Load only when the developer asks for a privacy policy (`privacy-policy-draft.md`). Draft only from the confirmed findings and user-confirmed facts, never from marketing copy or assumptions. If a policy already exists in the app, compare it with the findings and give the gaps in chat instead.

## When

- No privacy policy found in the repository or provided → offer a draft.
- An existing policy is found (text in repo or a URL the user supplies) → produce a **gap comparison** (claims vs inventory) instead of a new draft, unless asked.

## Rules

- Header: `DRAFT — requires business-owner confirmation and legal review. Not legal advice. Does not guarantee compliance.`
- Plain language. Structure: who we are; what we collect (by category, matching the store disclosures); how we use it (purposes); who we share it with (vendors from the SDK inventory, by name or category); international transfers (only if confirmed); retention; your choices and rights (only for regimes `confirmed`/`potential`); children; security (no absolute claims); changes; contact.
- Every unknown becomes `[TO CONFIRM: …]`: legal entity, address, contact email, DPO/representative, retention periods, legal bases, vendor locations, effective date.
- Do not claim encryption, certifications, "we never sell/share", "no AI training", specific retention, or deletion from backups without evidence.
- Do not write "we never share data" if any SDK or processor receives data.
- Describe SDK collection in conditional terms when only `vendor_documentation` supports it, and add a question to confirm the configuration.
- Keep the privacy policy separate from terms of service and from consent prompts.
- The policy must match `app-store-disclosures.md` and `google-play-data-safety.md`. Note any mismatch.

## Traceability (append to the draft)

| Policy statement | Evidence (file:line / SDK / user-confirmed) | Evidence type | Status |
|---|---|---|---|

Remove or qualify any statement that cannot be traced. List open questions for the owner at the end.
