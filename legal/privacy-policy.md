<!-- DRAFT FOR LAWYER REVIEW, not legal advice. Every statement is traced to the code or README in legal/traceability.md. Bump the version and date on every change. The Brekquater website copies this file (brekquater-front: npm run sync-legal). -->

# Ship-to-Store Privacy Policy

Version 1.0 · Last updated 5 November 2026

## Summary

Ship-to-Store is a free, open-source skill for Claude Code, published by BREKQUATER. It runs on your own computer. BREKQUATER does not run a server for it, and does not receive your code, your scan results, or any information about you or how you use it.

## Who we are

BREKQUATER, #169, INP Road, Baithkol, Karwar, Uttara Kannada District, Karnataka 581302, India. Contact: brekquater@gmail.com.

## What Ship-to-Store does with your files

- It reads files in the app folder you point it at, and skips dependency, build and other generated folders.
- Its scripts (scan.py and verify_report.py) use only your local Python and make no network calls.
- It keeps a scan cache in your computer's temporary folder (<temp>/ship-to-store/). Nothing is added to your repository by a scan.
- It writes changes into your repository only to fix what it finds, and leaves them uncommitted for you to review. It writes report documents only when you ask for them.
- Secret values found by the scanner are never printed or stored. Only the rule name and file location are recorded.

## Claude Code and Anthropic

Ship-to-Store runs inside Claude Code, which you use under your own agreement with Anthropic. While the skill is working, Claude reads the scanner summary and the lines of your files it needs to check, and that content is processed by Anthropic's service as part of your Claude Code session. That processing is governed by Anthropic's terms and privacy policy (https://www.anthropic.com/legal/privacy), not by BREKQUATER, and BREKQUATER does not receive it.

Claude may also look up public pages from Apple, Google, legislatures and regulators to re-check a rule. The skill instructs Claude never to send your code, secrets or scan results anywhere.

## Downloading and updates

You download Ship-to-Store from GitHub, which processes your visit and download under its own privacy statement (https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement).

The repository is public. If you star or fork it, or open an issue or pull request, your GitHub username and what you write are visible to us and to everyone. GitHub also shows repository owners aggregate traffic statistics, such as visit and clone counts and referring sites.

## What we do not collect

Ship-to-Store has no account, no sign-up, no telemetry, no analytics, no crash reporting and no advertising.

## If you contact us

If you email brekquater@gmail.com, we receive your email address and whatever you write, and use it only to reply and to keep a record of the request. Our email is provided by Google (Gmail), which may process it outside your country. We keep these emails until your request is resolved and then for 6 months.

## Legal basis (EEA and UK)

BREKQUATER does not receive any data from your use of Ship-to-Store. For emails you send us, we rely on our legitimate interest in answering you (Article 6(1)(f) GDPR).

## Your choices and rights

- Remove Ship-to-Store at any time: claude plugin uninstall ship-to-store@brekquater, or delete the copied skill folder.
- Delete the scan cache by deleting the ship-to-store folder in your computer's temporary folder.

Because we hold no data from your use of the tool, there is nothing for us to access or delete on your behalf. For emails you have sent us, you can ask us to access, correct or delete them at brekquater@gmail.com. For data processed by Anthropic or GitHub, use their own privacy processes.

In the EEA or UK you may also complain to your data protection authority. In India you may contact us using the details below and, if unresolved, approach the Data Protection Board of India.

## Children

Ship-to-Store is a tool for software developers. It is not directed at children.

## Changes to this policy

If we change this policy, we will update the version and date above and note the change in the changelog of the release that includes it.

## Contact

BREKQUATER, #169, INP Road, Baithkol, Karwar, Uttara Kannada District, Karnataka 581302, India. Email: brekquater@gmail.com.
