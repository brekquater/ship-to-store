# Apple App Store readiness

Load when `ios` is among the scan's platforms. Rules below were read from Apple's pages on **2026-11-03** unless marked *not re-verified*. If the user's tools allow web access, re-check the linked page before relying on a rule. Otherwise say "as of 2026-11-03".

Sources:
- App Review Guidelines: https://developer.apple.com/app-store/review/guidelines/ (checked 2026-11-03)
- App privacy details: https://developer.apple.com/app-store/app-privacy-details/ (checked 2026-11-03)
- Third-party SDK requirements: https://developer.apple.com/support/third-party-SDK-requirements/ (checked 2026-11-03)
- Required reason APIs: https://developer.apple.com/documentation/bundleresources/describing-use-of-required-reason-api (*categories not re-verified; the page did not render*)
- User privacy and data use (ATT): https://developer.apple.com/app-store/user-privacy-and-data-use/ (*not re-verified*)

## App Privacy details (the "nutrition label")

- Disclose all data **you or third-party partners (SDKs)** collect. "Collect" means transmitting data off the device so it can be accessed longer than needed to service the request in real time. On-device-only processing is not collected.
- Per data type, answer: purposes (Third-Party Advertising, Developer's Advertising or Marketing, Analytics, Product Personalization, App Functionality, Other), whether it is **linked to the user**, and whether it is **used for tracking**.
- Data types are grouped: Contact Info, Health & Fitness, Financial Info, Location, Sensitive Info, Contacts, User Content, Browsing History, Search History, Identifiers, Purchases, Usage Data, Diagnostics, Surroundings, Body, Other Data. The scan's `data_leads[].apple` gives the closest label. Confirm each one.
- Optional disclosure applies only when **all** of Apple's criteria are met (not tracking, not advertising, infrequent, optional, user-initiated with clear disclosure each time). Do not claim it casually.
- Apple-provided frameworks (e.g. MapKit, CloudKit) need not be disclosed for Apple's own collection.

## Purpose strings

Every protected resource the app accesses needs its `NS…UsageDescription` key in Info.plist (or Expo `ios.infoPlist` / config plugin). A missing key for an API the app calls crashes the app when it accesses the resource. Guideline 5.1.1(ii) requires that purpose strings "clearly and completely describe your use of the data". Flag empty, placeholder, or generic strings. Guideline 5.1.1(iv): do not force consent to unnecessary access; offer alternatives (e.g. manual address entry).

## Tracking and ATT

Guideline 5.1.2(i): you must get permission via App Tracking Transparency to track. Tracking means linking app data with third-party data for targeted ads or ad measurement, or sharing it with a data broker.
- ATT is required only if the app **tracks**. Having an ads or attribution SDK is strong evidence but not proof. Ask whether ad personalisation or measurement is enabled.
- If tracking: `NSUserTrackingUsageDescription` and a request (`requestTrackingAuthorization`) before tracking, and the SDKs configured to respect denial.
- An app may not require users to enable tracking, notifications or location to use it (5.1.2(i)).
- If tracking, declare tracking domains (`NSPrivacyTrackingDomains`) and `NSPrivacyTracking` in the privacy manifest.

## Privacy manifest

- `PrivacyInfo.xcprivacy` declares collected data types, tracking, and reasons for **required-reason API** use. Categories: UserDefaults, file timestamp, system boot time, disk space, active keyboards.
- The scanner checks native Swift/ObjC only. Cross-platform apps rely on their dependencies' manifests plus the app's own.
- Apple lists commonly used SDKs that must include a privacy manifest and a signature when shipped as binaries. The list includes Firebase modules, FBSDK, Flutter, Capacitor, Cordova, OneSignal and many Flutter plugins (see `sdk_catalog.json` `apple_privacy_manifest_sdks`). Recommend versions that include them. Do not claim a version does without checking its release notes.

## Transport security

ATS exceptions (`NSAllowsArbitraryLoads`, insecure exception domains) need justification at review and weaken transit encryption. Recommend HTTPS everywhere.

## Login services

Guideline 4.8: apps using a third-party or social login service for the primary account must also offer an equivalent login option with Apple's listed privacy features. Sign in with Apple qualifies. Exceptions exist (e.g. own account system only, enterprise or education logins, client apps for a specific third-party service). Flag for review. Do not assert a violation.

## Account deletion

Guideline 5.1.1(v): "If your app supports account creation, you must also offer account deletion within the app." Deleting must remove the account and associated data, not just deactivate it, subject to legal retention. If the app uses Sign in with Apple, revoke tokens via the REST API (*not re-verified*).

## Privacy policy

Guideline 5.1.1(i): all apps must link a privacy policy in App Store Connect and "within the app in an easily accessible manner". The policy must say what is collected, how, all uses, that third parties provide equal protection, retention and deletion, and how to revoke consent or request deletion.

## Third-party AI

Guideline 5.1.2(i) (checked 2026-11-03): "You must clearly disclose where personal data will be shared with third parties, including with third-party AI, and obtain explicit permission before doing so." If user content or personal data goes to an AI provider, recommend a just-in-time disclosure naming the provider and an explicit opt-in before the first send.

## Payments

Guideline 3.1.1: unlocking features or digital content in the app must use in-app purchase. Physical goods and services consumed outside the app may use other payment methods. Regional exceptions exist (*not re-verified*). Flag external payment code for review only.

## Review access

Guideline 2.1: "include demo account info (and turn on your back-end service!) if your app includes a login". Provide a demo account in App Review Information, or a demo mode, and notes for hardware, region, or feature-flag gated features.

## Kids

Guideline 1.3 (Kids Category) and 5.1.4: apps for kids should not include third-party analytics or advertising (limited exceptions), need a parental gate for links out and purchases, and must comply with children's privacy laws.

## Health

5.1.2(vi) and 5.1.3: HealthKit, Clinical Health Records, ARKit face data and similar data may not be used for marketing, advertising or data mining. Do not store personal health information in iCloud.

## Release checklist (Apple)

- [ ] App Privacy answers match the data inventory, including SDKs.
- [ ] Purpose strings for every accessed resource, specific and accurate.
- [ ] ATT implemented if tracking; manifest tracking fields consistent.
- [ ] App and SDK privacy manifests present; required-reason APIs declared.
- [ ] In-app account deletion if accounts can be created.
- [ ] Privacy policy URL in App Store Connect and in the app.
- [ ] Demo account / review notes.
- [ ] Export compliance (`ITSAppUsesNonExemptEncryption`) answered.
- [ ] Associated domains serve `apple-app-site-association`.
- [ ] Metadata (description, screenshots) does not claim features or privacy practices the app does not have.
