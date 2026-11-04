# Legal documents: evidence

Where each statement in [privacy-policy.md](privacy-policy.md) and [terms.md](terms.md) comes from (evidence types as in `skills/ship-to-store/references/evidence-and-findings.md`). Checked against `master` at v1.0.1 on 2026-11-05. Update this table with the documents.

| Statement | Evidence | Evidence type | Status |
|---|---|---|---|
| Publisher name, address, contact email | Same publisher details as the Morrow (v1.1) and Aarti Sangraha (v1.0.1) legal documents; `LICENSE` copyright BREKQUATER; `.claude-plugin/plugin.json` author | observed | confirmed by the owner's other published documents |
| Free, open source, MIT | `LICENSE`; `plugin.json` `license`; repository is public | observed | high |
| Runs locally; scripts make no network calls | `scripts/scan.py`, `scripts/verify_report.py` import no network module (only `urllib.parse`), no `subprocess`; README "What it runs and sends" | observed | high |
| Reads the app folder, skips generated folders | README "What it runs and sends", "Limitations" | observed | high |
| Scan cache in `<temp>/ship-to-store/`, nothing added to the repo | `scan.py` `tempfile.gettempdir()` cache path; CHANGELOG 1.0.0 | observed | high |
| Fixes left uncommitted; documents only on request | `SKILL.md` safety rule 5 and "Documents are made only on request" | observed | high |
| Secret values never printed or stored | README "Security and privacy"; `SKILL.md` rule 4; `verify_report.py` secret check | observed | high |
| Content Claude reads is processed by Anthropic within the user's Claude Code session | How Claude Code works; Anthropic privacy policy URL | static_inference | medium: describes the platform, not this repository |
| Claude may look up public pages; never sends code, secrets or scan results | `SKILL.md` rule 3; README "Network" | observed (instruction to the model) | medium: an instruction, not a technical control |
| Downloaded from GitHub; public interactions visible; aggregate traffic visible to owners | README install steps; repository is public; GitHub repository Insights | observed | high |
| No account, telemetry, analytics, crash reporting or ads | No such code or dependency; stdlib only | observed | high |
| Email handling (Gmail, 6 months) | Same practice stated in the Morrow privacy policy v1.1 | user_confirmed (owner's published Morrow policy) | to re-confirm for this product |
| Uninstall command | `claude plugin uninstall` (Claude Code CLI); README install options | observed | high |
| Not directed at children | Developer tool; README audience | static_inference | high |
| Not legal advice; no guarantee of approval or compliance; static analysis limits | README "What it is not", "Limitations"; `SKILL.md` | observed | high |
| Governing law India | Same choice as the Morrow and Aarti Sangraha terms | user_confirmed (owner's other terms) | to confirm with counsel |

Open questions for the owner:

1. Confirm the email handling and 6-month retention apply to Ship-to-Store support emails too.
2. Confirm the governing-law clause (Morrow says "courts of India", Aarti Sangraha says "courts at Karwar").
3. Have both documents reviewed by a qualified lawyer before relying on them.
