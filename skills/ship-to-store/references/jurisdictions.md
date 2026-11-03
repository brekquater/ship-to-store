# Jurisdiction applicability

Load at workflow step 8. The goal is a reasoned, dated assessment, not a list claiming every country has identical rules. Ship-to-Store covers the regimes below. Anything else is `not_assessed` unless the user asks. Never claim worldwide coverage.

## Method

1. **Collect facts.** Repository first, then ask the user once, in one compact list, only for what the repository cannot show:
   - Where the developer or company is established (country/state).
   - Target markets: store availability, languages, currencies, marketing. Repository hints: `*.lproj`, `values-xx/`, i18n locale files, currency codes, region-specific consent tooling.
   - Whether the app is directed at children, or has users under 13/16/18.
   - Data categories (from the data inventory), especially sensitive data and precise location.
   - Whether data is sold or shared for cross-context advertising (ads/attribution SDKs are a lead, not proof).
   - For US state laws: annual revenue and volume of residents' data processed. Many developers will not know or will want to keep these private; record `unknown`.
2. **Apply each regime's trigger test** below to those facts.
3. **Assign a status:**
   - `confirmed`: the trigger is met by user-confirmed facts (e.g. established in the EU, or confirms targeting UK users).
   - `potential`: repository or store evidence suggests the trigger may be met, but facts are unconfirmed. Worldwide store availability alone gives `potential`, not `confirmed`.
   - `not_assessed`: facts missing, or regime outside this skill's coverage.
   - `not_applicable`: the trigger is clearly not met. **Always state the reason** (e.g. "not established in India; app not offered in India per developer").
4. **Record currentness.** Each row carries the source URL and the date checked. If web access is unavailable in this session, use the dates below and write "not re-verified in this session".
5. **Escalate** to qualified counsel: children's data, health/biometric/financial data, cross-border transfer mechanisms, threshold questions, conflicting obligations, and any "are we compliant?" question.

In chat, give only regimes that are `confirmed` or `potential`, one line each with their status. Use this table only in a requested `audit-report.md`:

| Regime | Trigger test | Facts / evidence | Status | Main obligations if it applies | Source (checked) |
|---|---|---|---|---|---|

## Regimes

### EU GDPR, Regulation (EU) 2016/679
- **Trigger (Art. 3):** established in the EU, or (not established) offering goods/services to people in the EU, or monitoring their behaviour in the EU. Analytics and ads profiling count as monitoring.
- **Main obligations:** lawful basis per purpose (Art. 6; Art. 9 for special categories); transparency (Arts. 13–14); data subject rights; processor contracts (Art. 28); international transfer safeguards (Ch. V); security; breach notification; DPIA for high-risk processing; EU representative if not established (Art. 27).
- **Source:** https://eur-lex.europa.eu/eli/reg/2016/679/oj (stable text, *not re-fetched 2026-11-03*).

### EU ePrivacy, Directive 2002/58/EC Art. 5(3), via national law
- **Trigger:** storing or accessing information on a user's device in the EU, e.g. SDKs reading or writing identifiers.
- **Obligation:** consent before access, unless strictly necessary for the service the user explicitly requested. National implementations differ.
- **Source:** https://eur-lex.europa.eu/eli/dir/2002/58/oj (*not re-fetched*).

### UK GDPR, Data Protection Act 2018, and PECR
- **Trigger:** like GDPR, for the UK. PECR covers device storage/access and electronic marketing.
- **Note:** the Data (Use and Access) Act 2025 amends UK data protection and PECR (including some cookie exemptions), with phased commencement. Verify the current position at https://ico.org.uk/ before relying on any exemption (*not re-verified*).

### California CCPA as amended by CPRA
- **Trigger:** a for-profit business doing business in California that meets one of these: annual gross revenue above **$26,625,000** (CPI-adjusted from 2025-01-01; checked 2026-11-03 at https://cppa.ca.gov/regulations/cpi_adjustment.html; next adjustment expected 2027-01-01); buys, sells or shares personal information of 100,000+ consumers or households; or earns 50%+ of revenue from selling or sharing personal information.
- **Main obligations:** notice at collection; rights to know, delete and correct; opt-out of sale/**sharing** (cross-context behavioural advertising), including a "Do Not Sell or Share" mechanism and honouring opt-out preference signals; limit use of sensitive personal information (includes precise geolocation); contracts with service providers.
- **Many indie apps fall below every threshold.** That is `not_applicable` only with confirmed revenue and volume facts; otherwise `not_assessed`.

### Other US state comprehensive privacy laws
- Roughly twenty states have comprehensive laws with differing thresholds (often based on the number of state residents whose data is processed) and differing children's and sensitive-data rules. Mark `not_assessed` unless the user confirms significant US reach. Then check each state's statute or attorney-general guidance. Do not generalise from California.

### US COPPA (16 CFR Part 312)
- **Trigger:** an online service directed to children under 13, or with actual knowledge that it collects personal information from a child under 13.
- **Main obligations:** notice, verifiable parental consent before collection, separate consent for third-party disclosure (2025 amendments), data minimisation and retention limits, security. Amended rule effective 2025-06-23; compliance date 2026-04-22 (checked 2026-11-03 via legal summaries; primary: https://www.ftc.gov/legal-library/browse/rules/childrens-online-privacy-protection-rule-coppa).

### India DPDP Act 2023 and DPDP Rules 2025
- **Trigger:** processing digital personal data in India, or outside India in connection with offering goods/services to people in India.
- **Commencement is phased** (checked 2026-11-03 via search summaries of the gazette notification; verify at https://www.meity.gov.in/). The Rules were notified in November 2025. Some provisions (Data Protection Board) started 2025-11-14. The consent-manager rule starts 2026-11-14. Most obligations on data fiduciaries (notice, consent, security, breach reporting, children, rights) are reported to start 18 months after notification (around May 2027). Do not describe these as currently in force before their date. Present them as "upcoming obligations to prepare for".
- **Main obligations once in force:** notice and consent (or a listed legitimate use), verifiable parental consent for users under 18, no tracking, behavioural monitoring or targeted advertising directed at children, reasonable security safeguards, breach notification, rights (access, correction, erasure, grievance redressal, nomination).

### Brazil LGPD (Lei 13.709/2018)
- **Trigger (Art. 3):** processing in Brazil, offering goods/services to people in Brazil, or data collected in Brazil. Source: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm (*not re-verified*).

### Not covered in depth (mark `not_assessed` unless the user targets them)
Canada (PIPEDA, Quebec Law 25; https://www.priv.gc.ca/), Australia (Privacy Act; https://www.oaic.gov.au/), Japan (APPI; https://www.ppc.go.jp/en/), South Korea (PIPA; https://www.pipc.go.kr/eng/), Singapore (PDPA; https://www.pdpc.gov.sg/), Switzerland (FADP; https://www.edoeb.admin.ch/), China (PIPL), South Africa (POPIA; https://inforegulator.org.za/). Point the user to the regulator. Do not summarise rules not researched in this session.

## Children

Child-directed signals (the `CHILDREN_SIGNALS` check, Kids/Family store categories, age gates) change everything. COPPA, GDPR Art. 8 (age of digital consent 13–16 by member state), DPDP (under 18), Apple 1.3/5.1.4, and Play Families policy may all apply. Third-party analytics and ads SDKs become high-risk. Always escalate to legal review and never generate a children's policy from templates alone.

## International transfers

If vendors (`sdks`, `endpoints`) process data outside the user's region, note "potential international transfer" per vendor with `[TO CONFIRM: vendor data location and transfer mechanism]`. Do not name a mechanism (SCCs, adequacy, DPF) unless the vendor's documentation or the user confirms it.
