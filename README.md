# Ship-to-Store

Make your vibe-coded app ready for the App Store and Google Play.

Ship-to-Store is a **Claude Code Skill** that works on your app repository **locally**. An offline scanner finds what stands between your app and the stores (SDKs, permissions, purpose strings, privacy manifest, target API, account deletion, consent, secrets…). Claude then **fixes what it safely can** and tells you, in a short numbered list in chat, what is left for you: store-console steps, App Privacy and Data safety answers, and questions only you can answer. It creates no report files unless you ask for them.

**What it is not:** a SaaS product, a hosted scanner, a legal opinion, or a guarantee of store approval or legal compliance. It never uploads your code, never runs your app, and never installs your dependencies.

## Requirements

- [Claude Code](https://code.claude.com/). Built for Claude Code, where it can read and fix your local repo. In claude.ai chat it has no local repo to work on.
- Python 3.9 or newer (`python3`; on Windows, `python`). Standard library only; nothing to `pip install`.

## Install

### Option A: plugin (recommended, gets updates)

In your shell:

```bash
claude plugin marketplace add brekquater/ship-to-store
```

```bash
claude plugin install ship-to-store@brekquater
```

Or inside a Claude Code session (v2.1.275+): `/plugin install ship-to-store --marketplace brekquater/ship-to-store`.

Run it with `/ship-to-store:ship-to-store`, because plugin commands carry the plugin name as a prefix. Update with `claude plugin update ship-to-store@brekquater`.

### Option B: copy the skill folder

This gives you the short `/ship-to-store` command, but no automatic updates. The skill is the folder `skills/ship-to-store/`. Copy that folder, not the whole repository, into one of Claude Code's skill locations.

**Project-level** (only this app; commit it so collaborators get it). Run from your app's root:

```bash
git clone --depth 1 https://github.com/brekquater/ship-to-store.git /tmp/ship-to-store
mkdir -p .claude/skills
cp -R /tmp/ship-to-store/skills/ship-to-store .claude/skills/ship-to-store
```

**User-level** (all your projects):

```bash
git clone --depth 1 https://github.com/brekquater/ship-to-store.git /tmp/ship-to-store
mkdir -p ~/.claude/skills
cp -R /tmp/ship-to-store/skills/ship-to-store ~/.claude/skills/ship-to-store
```

Windows (PowerShell), user-level:

```powershell
git clone --depth 1 https://github.com/brekquater/ship-to-store.git "$env:TEMP\ship-to-store"
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse "$env:TEMP\ship-to-store\skills\ship-to-store" "$HOME\.claude\skills\ship-to-store"
```

For project-level on Windows, use `.claude\skills` in your app's root instead of `$HOME\.claude\skills`.

To update, delete the installed `ship-to-store` folder and repeat the copy. Restart Claude Code, or start a new session, so it picks up the skill.

## Use

In Claude Code, from your app's root:

```text
/ship-to-store
```

With the plugin install, type `/ship-to-store:ship-to-store` instead. The arguments are the same.

Variants:

```text
/ship-to-store check-only         # report only, change nothing
/ship-to-store apps/mobile        # a sub-folder (monorepos)
```

Claude also picks up the skill automatically for requests like *"is my app ready for the App Store?"*, *"fill in the Play Data safety form"*, or *"what does my app need for privacy before launch?"*.

What happens:
1. The scanner runs once and prints a compact summary of a few KB. Its cache lives in your OS temp folder, so **nothing is added to your repo**.
2. Claude confirms the important leads by reading only the cited lines.
3. **Claude fixes what it safely can:** purpose strings, unused permissions, personal data in logs, privacy manifests, target API, insecure URLs, and making an in-app privacy policy publishable.
4. Before bigger changes, Claude asks you once, in one short list: new dependencies, new screens (account deletion, consent, Sign in with Apple), removing features, and facts only you know.
5. Claude re-scans to confirm the fixes, runs your project's own typecheck, lint and tests if it has them, and leaves the changes uncommitted for you to review.
6. You get one short report in chat: **what was fixed**, **what you need to do** (numbered, in submission order), **questions**, and **store-form answers**.

Want files? Ask for them: *"write the Data safety answers"*, *"draft a privacy policy"*, or *"write it up"*. Each generated file is checked by `verify_report.py`, which fails on any secret-like value and flags guarantee-like wording.

### Example (synthetic sample app)

An illustrative chat report for the bundled React Native fixture (`tests/fixtures/react-native`):

```text
fixture-rn — NOT READY: BLOCKERS FOUND

Fixed (4)
1. NSPhotoLibraryUsageDescription added; NSCameraUsageDescription written — ios/FixtureApp/Info.plist
2. Email removed from console.log — src/App.tsx:15
3. targetSdkVersion 34 → 36 — android/build.gradle:4 (test before release)
4. Location sent in the POST body instead of the URL — src/App.tsx:22

You need to do (5)
Blockers
1. Add account deletion: you have sign-up but no way to delete. I can build it; say yes.
2. Publish a privacy policy URL; none exists. I can draft one; say yes.
Play Console
3. Data safety: email, user ID, precise location, photos, app interactions (answers below).
4. Photo and video permissions declaration, or let me switch to the system photo picker.
App Store
5. Add Sign in with Apple next to Google Sign-In (guideline 4.8), or document the exception.

Need your answer
1. What is sent to Mixpanel (src/App.tsx:33)?   2. Can upload.fixture-backend.io serve HTTPS?
...
```

The scanner on its own:

```bash
python3 skills/ship-to-store/scripts/scan.py --root tests/fixtures/react-native
```

Abridged summary output:

```json
{"app":{"frameworks":["react-native"],"platforms":["android","ios"]},
 "sdks":["firebase-analytics [analytics]","firebase-auth [auth]","google-signin [auth,social_login]","sentry [crash_reporting,performance]", "..."],
 "endpoints":["api.mixpanel.com (Mixpanel) x1","api.fixture-backend.io x1","upload.fixture-backend.io x1 [cleartext]"],
 "checks":[
  {"id":"IOS_PURPOSE_STRING_MISSING","status":"attention","summary":"photos used but no NSPhotoLibraryUsageDescription ...","evidence":["src/App.tsx:8","sdk:image-picker"]},
  {"id":"ACCOUNT_DELETION_NOT_FOUND","status":"attention","evidence":["src/App.tsx:14","src/App.tsx:27","firebase-auth"]},
  {"id":"PLAY_TARGET_SDK_LOW","status":"attention","summary":"targetSdk 34 is below the Play requirement recorded on 2026-11-03 (API 36 ...)"},
  {"id":"TOKENS_IN_PLAIN_STORAGE","status":"attention","evidence":["src/App.tsx:16"]}, "..."]}
```

## Documents (only when you ask)

| Ask for | You get |
|---|---|
| "write it up" / "full report" | `audit-report.md`: status, findings, jurisdictions, open questions |
| "Data safety answers" | `google-play-data-safety.md` |
| "App Privacy answers" | `app-store-disclosures.md` |
| "privacy policy" | `privacy-policy-draft.md`, marked DRAFT, with `[TO CONFIRM: …]` for unknown facts |
| "consent plan", "SDK list", "checklist", "data inventory" | the matching file |

Files go to `ship-to-store-report/` (or wherever you say). Claude offers to gitignore that folder.

Documents that still contain `[TO CONFIRM: …]` are marked **INCOMPLETE** and need the business owner. Anything marked for legal review needs a qualified lawyer.

## Supported projects

| Project type | What the scanner reads |
|---|---|
| React Native | `package.json`, lockfiles (npm/yarn/pnpm), Android and iOS native folders |
| Expo | `app.json` (`ios.infoPlist`, `android.permissions`, plugins, build properties); `app.config.js/ts` detected but not evaluated |
| Flutter | `pubspec.yaml`, `pubspec.lock`, platform folders |
| Native Android (Kotlin/Java) | `AndroidManifest.xml`, Gradle Groovy/KTS, `libs.versions.toml`, network security config |
| Native iOS (Swift/Objective-C) | `Info.plist`, `.entitlements`, `PrivacyInfo.xcprivacy`, Podfile/Podfile.lock, `Package.swift`/`Package.resolved`, Cartfile, `project.pbxproj` |
| Ionic / Capacitor / Cordova | `package.json`, `capacitor.config.*`, `ionic.config.json`, `config.xml` |
| .NET MAUI | `.csproj` (PackageReference, UseMaui), platform manifests |
| Web apps | `package.json` frameworks, source, endpoints (store checks don't apply) |

The SDK catalog (`scripts/sdk_catalog.json`) covers 76 common analytics, ads, attribution, crash, session-replay, auth, payments, push, maps, storage, media, consent and AI SDKs. It also includes Apple's list of SDKs that require privacy manifests (checked 2026-11-03).

## Run the scanner directly

```bash
python3 skills/ship-to-store/scripts/scan.py --root path/to/app              # summary; detail cached in the OS temp folder
python3 skills/ship-to-store/scripts/scan.py --root path/to/app --reuse      # cached summary if nothing changed
python3 skills/ship-to-store/scripts/scan.py --root path/to/app --show sdks --grep firebase
python3 skills/ship-to-store/scripts/verify_report.py --dir path/to/docs      # check documents you asked Claude to write
```

## Limitations

- **Static analysis only.** An installed SDK does not prove a feature is enabled. A declared permission does not prove the resource is accessed. A URL string does not prove data is sent. Runtime-configured endpoints, server-side processing, remote config and data flows inside SDKs are invisible.
- Pattern-based detection has false positives and false negatives. The report lists coverage gaps: skipped large, minified, binary or symlinked files, parse errors, and caps reached.
- Generated and vendor folders (`node_modules`, `Pods`, `build`, …) are skipped. SDKs are identified from manifests and lockfiles instead.
- Platform rules and laws change. References record the date each rule was checked (currently 2026-11-03). Claude re-checks official pages when web access is available and otherwise says the rule was not re-verified.
- Jurisdiction coverage is limited to GDPR, UK GDPR/PECR, ePrivacy, CCPA/CPRA, COPPA, India DPDP and LGPD triggers. Everything else is reported as *not assessed*.
- No guarantee of App Store / Google Play approval or legal compliance.

## What it runs and sends

| | |
|---|---|
| **Runs** | `scripts/scan.py` and `scripts/verify_report.py` with your local Python (standard library only). After making fixes, Claude may run your project's existing typecheck, lint and test scripts, and tells you first. Nothing is installed, built or executed from your app. |
| **Reads** | Files in the app folder you point it at, skipping `node_modules`, build output and other vendor or generated folders. |
| **Writes** | Only the fixes it makes in your repo (left uncommitted), plus its scan cache under your OS temp folder (`<temp>/ship-to-store/`). It writes documents only if you ask. |
| **Network** | The scripts make no network calls. Claude may look up public Apple, Google, legislation and regulator pages to re-check a rule, and never sends your code, secrets or scan results anywhere. |

## Security and privacy

- Everything runs locally. Scripts make no network calls and use only the Python standard library.
- Repository content is treated as untrusted data. Instructions found in code, comments or docs are never followed.
- Secret **values are never printed or stored**. Only rule names and locations are recorded, and generated documents are checked for leaks.
- The scanner does not follow symlinks or junctions out of the repository and handles malformed, binary, non-UTF-8 and oversized files without crashing.
- Claude edits your code only for fixes, never commits, and asks before adding dependencies, changing user-facing behaviour or removing anything. It never installs packages or builds your app. It runs your existing typecheck, lint and test scripts only to verify its own fixes, and tells you first.
- Documents you ask for describe your app's data practices and may be sensitive. Treat them accordingly.

## Tests

```bash
python -m unittest discover -s tests -v
```

Synthetic fixtures for React Native, Expo, Flutter, native Android, native iOS, Capacitor/Ionic, .NET MAUI and a web app live in `tests/fixtures/`. Edge cases (malformed files, binaries, large and minified files, symlinks, secrets, injection text) are generated at test time. CI runs on Linux, Windows and macOS.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) (adding SDKs, updating rules with official sources) and [CHANGELOG.md](CHANGELOG.md).

## License

MIT, as chosen by the repository owner. See [LICENSE](LICENSE).
