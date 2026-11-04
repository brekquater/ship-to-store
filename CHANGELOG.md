# Changelog

Add entries under **Unreleased** in each PR. The release workflow moves them under the new version number.

## Unreleased

## 1.0.1 (2026-11-04)

### Added
- Release automation (`.github/workflows/release.yml`): pick patch, minor or major under Actions → release → Run workflow; or merge a PR that bumps the version in `.claude-plugin/plugin.json`. Either way the release is tagged and published with notes from this file.

## 1.0.0 (2026-11-03)

Rewrite of the earlier `privacy-audit` draft as **Ship-to-Store**.

### Added
- Claude Code plugin packaging: `.claude-plugin/plugin.json` and a marketplace (`brekquater`) in the same repo. Install with `claude plugin marketplace add brekquater/ship-to-store` then `claude plugin install ship-to-store@brekquater`.
- `scripts/scan.py`: offline, stdlib-only scanner. Covers framework detection (React Native, Expo, Flutter, native Android/iOS, Capacitor/Ionic, Cordova, .NET MAUI, web), dependency parsing (npm/yarn/pnpm, pub, CocoaPods, SwiftPM, Gradle + version catalogs, NuGet, pip), SDK identification via `sdk_catalog.json`, Android manifest / Info.plist / entitlements / privacy-manifest / Expo config parsing, sensitive-API and data-collection rules, endpoint extraction with redaction, secret detection (values never stored), store-readiness checks, data-category leads mapped to Apple and Play labels, compact summary output, `--reuse` cache and `--show` drill-down.
- `scripts/verify_report.py`: blocks secret-like values in generated documents, validates `data-inventory.json`, flags guarantee-like wording, counts open placeholders.
- References for Apple App Store, Google Play, jurisdictions (with check dates), consent mechanisms, output formats, evidence rules, security, and optional runtime checks.
- Synthetic fixtures for 8 app types and a `unittest` suite. GitHub Actions on Linux, Windows and macOS.

### Changed: fix first, report in chat
- The skill now fixes what it safely can (purpose strings, unused permissions, PII in logs, privacy manifests, target API, insecure URLs, publishable privacy policy). It asks once before bigger changes, then gives one short numbered to-do list in chat. Report files are made only on request, so the earlier default of 8 files is gone.
- The scan cache moved from `<app>/ship-to-store-report/` to the OS temp folder, so a run adds nothing to the app repo.
- `quick` is replaced by `check-only` (report without changing anything).
- The scanner resolves the React Native / Expo default targetSdk from the installed `react-native` version catalog.

### Fixed after the first real-app test (an Expo + AdMob app)
- Explicit child-directed opt-outs (`tagForChildDirectedTreatment: false`) were reported as child signals. They are now a separate `ADS_NOT_CHILD_DIRECTED` info check.
- Google UMP via react-native-google-mobile-ads (`AdsConsent`, `canRequestAds`) was not recognised as consent tooling.
- Debug source-set manifests (`src/debug*/`) raised release-level cleartext and permission findings.
- Build-script repositories and Android drawable/layout XML comments were listed as app endpoints.
- `--reuse` could serve a `scan.json` written by an older scanner. The fingerprint now covers the scanner itself, and unreadable caches trigger a rescan.
- Added: gitignored `android/`/`ios/` flagged as generated, Expo `platforms` honoured, and the framework version shown when targetSdk is unknown.

### Fixed (relative to the earlier draft)
- Scanner crash on Windows consoles (non-UTF-8 stdout).
- Secrets leaking through unredacted URL matches and unquoted or env-style keys.
- Info.plist, entitlements, privacy manifests, Objective-C and .NET files were never read.
- Output volume: about 72 KB for a repo with no app code. It now prints a summary of a few KB.
- Symlinks followed outside the repository root.
