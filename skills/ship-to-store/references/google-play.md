# Google Play readiness

Load when `android` is among the scan's platforms. Rules were read from Google's pages on **2026-11-03** unless marked *not re-verified*. Re-check if web access is available; otherwise say "as of 2026-11-03".

Sources:
- Data safety section: https://support.google.com/googleplay/android-developer/answer/10787469 (checked 2026-11-03)
- Account deletion: https://support.google.com/googleplay/android-developer/answer/13327111 (checked 2026-11-03)
- Permissions and APIs that access sensitive information: https://support.google.com/googleplay/android-developer/answer/9888170 (checked 2026-11-03)
- Target API level: https://developer.android.com/google/play/requirements/target-sdk (checked 2026-11-03 via search summary)
- Advertising ID: https://support.google.com/googleplay/android-developer/answer/6048248 (*not re-verified*)
- User Data policy (prominent disclosure, privacy policy): https://support.google.com/googleplay/android-developer/answer/10144311 (*not re-verified*)

## Data safety

- Required for every app published on Play (closed, open and production tracks). Apps that collect nothing still complete it and link a privacy policy.
- **Collection** means transmitting data off the device, including by SDKs and by webviews the app controls. Exempt: on-device-only processing, end-to-end encrypted data the developer cannot read, and ephemeral processing.
- **Sharing** means transferring to a third party. Exempt: service providers acting on your behalf, legal obligations, user-initiated transfers, consented disclosures, and fully anonymised data.
- Categories: Location, Personal info, Financial info, Health and fitness, Messages, Photos and videos, Audio, Files and docs, Calendar, Contacts, App activity, Web browsing, App info and performance, Device or other IDs. The scan's `data_leads[].play` gives the closest label.
- Purposes: App functionality, Analytics, Developer communications, Advertising or marketing, Fraud prevention/security/compliance, Personalization, Account management.
- Per type: collected and/or shared, required or optional, purposes.
- Security practices: data encrypted in transit (any `cleartext` flag undermines a "yes"), and whether users can request deletion.

## Account deletion

If users can create an account in the app, the app needs:
1. An in-app path to delete the account and associated data.
2. A **web link** where users can request deletion without reinstalling the app, entered in the Data safety form.
Retained data (security, fraud, legal) must be disclosed. Partial data deletion without account deletion may also be offered.

## Sensitive permissions

Restricted or declaration-gated (the scan flags these with `play_policy`):
- **Background location**: only for user-beneficial features; requires a declaration, prominent disclosure and review.
- **SMS / Call Log**: only for default handlers or approved exceptions; requires a declaration.
- **All files access** (`MANAGE_EXTERNAL_STORAGE`): requires a declaration.
- **`QUERY_ALL_PACKAGES`**: requires a declaration; prefer targeted `<queries>`.
- **Photo and video** (`READ_MEDIA_IMAGES/VIDEO`): requires a declaration unless the system photo picker suffices. Recommend the Photo Picker.
- **Exact alarms** (`USE_EXACT_ALARM`): alarm, timer or calendar core function only. **Full-screen intent**: declaration on Android 14+.
- **Foreground service types**: declare each type and justification in Play Console (*declaration form not re-verified*).
- **Accessibility API, `REQUEST_INSTALL_PACKAGES`, `VpnService`, Health Connect**: restricted; require declarations.
- **Prominent disclosure**: where required, show in-app disclosure (what, why, how used) and get affirmative consent **before** the runtime prompt. The OS permission dialog alone does not count.

## Target API level

As of 2026-11-03: new apps and app updates must target **Android 16 (API 36)** from 2026-08-31. Wear OS, TV, Automotive and XR differ. Existing apps below the visibility floor are hidden from users on newer devices. The scanner compares against `sdk_catalog.json` `meta.play_target_sdk`. Update that value when Google announces the next requirement.

## Advertising ID

Apps targeting Android 13+ that use the advertising ID need `com.google.android.gms.permission.AD_ID` (ads SDKs often merge it automatically) and must answer the Advertising ID declaration in Play Console. If the app does not use it, remove it with `tools:node="remove"` and answer accordingly (*not re-verified*).

## Families and children

Apps targeting children must follow the Families policy: only self-certified ads SDKs, no transmitting identifiers from children, plus COPPA and other laws (*not re-verified*).

## App access for review

If parts of the app are behind a login, provide credentials or instructions under App content → App access (*not re-verified*).

## Release checklist (Google Play)

- [ ] Data safety form matches the data inventory, including SDK collection and sharing.
- [ ] Privacy policy URL in Play Console and accessible in the app.
- [ ] In-app account deletion and web deletion link (if accounts exist).
- [ ] Declarations for restricted permissions and foreground services; prominent disclosures implemented.
- [ ] Advertising ID declaration answered; AD_ID permission matches.
- [ ] targetSdk meets the current requirement.
- [ ] App Links hosts serve `/.well-known/assetlinks.json`.
- [ ] App access instructions for reviewers.
- [ ] Store listing does not contradict the app's actual behaviour.
