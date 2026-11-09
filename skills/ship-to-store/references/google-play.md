# Google Play readiness

Load when `android` is among the scan's platforms. Rules were read from Google's pages on the dates below. Re-check if web access is available; otherwise say "as of <that date>". Official Google pages are the only authority here; never use blogs or tutorials. Keep rules in force apart from announced future ones.

Sources (Developer Program Policy effective 2026-10-29, checked 2026-11-09):
- Policy Center: https://support.google.com/googleplay/android-developer/answer/18265346 (2026-11-09)
- Target API level: https://developer.android.com/google/play/requirements/target-sdk (2026-11-09)
- User Data (privacy policy, prominent disclosure): https://support.google.com/googleplay/android-developer/answer/10144311 (2026-11-09)
- Advertising ID: https://support.google.com/googleplay/android-developer/answer/6048248 (2026-11-09)
- Foreground services: https://support.google.com/googleplay/android-developer/answer/13392821 (2026-11-09)
- App content page: https://support.google.com/googleplay/android-developer/answer/9859455 (2026-11-09)
- Ads: https://support.google.com/googleplay/android-developer/answer/9857753 (2026-11-09)
- Payments: https://support.google.com/googleplay/android-developer/answer/9858738 (2026-11-09)
- User-generated content: https://support.google.com/googleplay/android-developer/answer/9876937 (2026-11-09)
- Families: https://support.google.com/googleplay/android-developer/answer/9893335 (2026-11-09)
- Device and network abuse: https://support.google.com/googleplay/android-developer/answer/9888379 (2026-11-09)
- Broken and minimum functionality: https://support.google.com/googleplay/android-developer/answer/9898783 (2026-11-09)
- Deceptive behavior: https://support.google.com/googleplay/android-developer/answer/9888077 (2026-11-09)
- Restricted content index: https://support.google.com/googleplay/android-developer/topic/9877466 (2026-11-09)
- Metadata policy: https://support.google.com/googleplay/android-developer/answer/9898842 (2026-11-09)
- Store listing limits: https://support.google.com/googleplay/android-developer/answer/9859152 (2026-11-09)
- Testing requirements: https://support.google.com/googleplay/android-developer/answer/14151465 (2026-11-09)
- Pre-launch reports: https://support.google.com/googleplay/android-developer/answer/9842757 (2026-11-09)
- Android vitals: https://support.google.com/googleplay/android-developer/answer/9844486 (2026-11-09)
- App optimization (R8): https://developer.android.com/topic/performance/app-optimization/enable-app-optimization (2026-11-09)
- Data safety: https://support.google.com/googleplay/android-developer/answer/10787469 (2026-11-03)
- Account deletion: https://support.google.com/googleplay/android-developer/answer/13327111 (2026-11-03)
- Permissions and sensitive APIs: https://support.google.com/googleplay/android-developer/answer/9888170 (2026-11-03)

## Policy coverage

Give each area below one status from your evidence. In chat, show only one count line; list the problems in the normal report sections. Give the full table only when asked for a "policy matrix".

- `PASS`: verified with concrete evidence. **Never PASS because nothing was found.** No match means `NOT TESTED`, or `NOT APPLICABLE` with the reason.
- `FAIL`: confirmed violation or defect.
- `WARNING`: looks problematic and needs attention.
- `NEEDS YOU`: needs a product, legal, business or Play Console answer.
- `NOT APPLICABLE`: does not apply, with the reason.
- `NOT TESTED`: evidence or testing was unavailable.

| # | Area | Evidence to use |
|---|---|---|
| 1 | Functionality and quality | Placeholder text and dead links from code. Crashes and flows need real devices and the pre-launch report: `NOT TESTED` unless the developer confirms |
| 2 | Privacy and data handling | `data_leads`, logs, storage, TLS, disclosure before collection |
| 3 | Permissions | Source manifests plus the merged release manifest. Trace each sensitive permission to a feature and check denial is handled |
| 4 | SDKs | `sdks`, including what the merged manifest adds. "Popular" is not evidence of compliance |
| 5 | Privacy policy and Data safety | Policy text against the findings; public URL; link inside the app |
| 6 | Accounts and deletion | `ACCOUNT_DELETION_NOT_FOUND`; in-app path and web link |
| 7 | Ads | `PLAY_AD_PLACEMENT_REVIEW`: read each call site |
| 8 | Billing and subscriptions | `payments_iap`, `PLAY_PAYMENTS_REVIEW` |
| 9 | User-generated content | `PLAY_UGC_SAFEGUARDS_NOT_FOUND`, or what the app's features show |
| 10 | Restricted content, IP, impersonation | `PLAY_RESTRICTED_CATEGORY_REVIEW`, app purpose, name, artwork and text sources |
| 11 | Technical and security | Target API, exported components, TLS, dynamic code, WebView, release config, secrets |
| 12 | Store listing | `PLAY_STORE_LISTING` for fastlane files. Also read any listing document (`store/`, `listing*`). Otherwise `NOT TESTED` |
| 13 | Review access and declarations | Login needs, App content sections |
| 14 | Children and Families | `CHILDREN_SIGNALS`, `ADS_NOT_CHILD_DIRECTED`, target audience |

Do not rebuild the app to fill a gap. If `coverage.merged_release_manifest` is null, permissions added by SDKs are `NOT TESTED`: ask the developer to run a release build once, then rescan. If its `stale` is true, the build is older than the config, so treat it as a lead.

## Data safety

- Required for every app published on Play (closed, open and production tracks). Apps that collect nothing still complete it and link a privacy policy.
- **Collection** means transmitting data off the device, including by SDKs and by webviews the app controls. Exempt: on-device-only processing, end-to-end encrypted data the developer cannot read, and ephemeral processing.
- **Sharing** means transferring to a third party. Exempt: service providers acting on your behalf, legal obligations, user-initiated transfers, consented disclosures, and fully anonymised data.
- Categories: Location, Personal info, Financial info, Health and fitness, Messages, Photos and videos, Audio, Files and docs, Calendar, Contacts, App activity, Web browsing, App info and performance, Device or other IDs. The scan's `data_leads[].play` gives the closest label.
- Purposes: App functionality, Analytics, Developer communications, Advertising or marketing, Fraud prevention/security/compliance, Personalization, Account management.
- Per type: collected and/or shared, required or optional, purposes.
- Security practices: data encrypted in transit (any `cleartext` flag undermines a "yes"), and whether users can request deletion.

## Privacy policy

Needed even by apps that access no personal data. It must be on an active, public, non-geofenced URL, not a PDF, and be linked in Play Console and inside the app. It must name the app or the store listing's entity and be labelled as a privacy policy. It must cover developer contact, data types collected and shared, recipients, secure handling, and retention and deletion. Personal data must not be sold.

## Account deletion

If users can create an account in the app, the app needs:
1. An in-app path to delete the account and associated data.
2. A **web link** where users can request deletion without reinstalling the app, entered in the Data safety form.
Freezing or deactivating an account does not count. Retained data (security, fraud, legal) must be disclosed. Partial data deletion without account deletion may also be offered.

## Sensitive permissions

Restricted or declaration-gated (the scan flags these with `play_policy`):
- **Background location**: only for user-beneficial features; requires a declaration, prominent disclosure and review.
- **SMS / Call Log**: only for default handlers or approved exceptions; requires a declaration.
- **All files access** (`MANAGE_EXTERNAL_STORAGE`): requires a declaration.
- **`QUERY_ALL_PACKAGES`**: requires a declaration; prefer targeted `<queries>`.
- **Photo and video** (`READ_MEDIA_IMAGES/VIDEO`): requires a declaration unless the system photo picker suffices. Recommend the Photo Picker.
- **Exact alarms** (`USE_EXACT_ALARM`): alarm, timer or calendar core function only. **Full-screen intent**: declaration on Android 14+.
- **Foreground service types** (apps targeting Android 14+): declare every type on the App content page, with a functionality description, user impact and a demo video link.
- **Accessibility API, `REQUEST_INSTALL_PACKAGES`, `VpnService`, Health Connect**: restricted; require declarations.
- **Prominent disclosure**: required when data use may fall outside user expectations, such as background collection. Show it in normal use, immediately before the consent or runtime prompt, saying what data, how it is used and whether it is shared. Consent needs an affirmative action, and collection cannot start before it. The OS dialog or a privacy policy alone does not count.

## Target API level

As of 2026-11-09: new apps and updates must target **Android 16 (API 36)** since 2026-08-31 (Wear OS and Automotive 35; TV and XR 34). The extension window ran to 2026-11-01. Existing apps must target API 35 or higher to stay available to new users on newer Android versions. Permanently private apps are exempt. The scanner compares against `sdk_catalog.json` `meta.play_target_sdk`. Update that value when Google announces the next requirement.

## Advertising ID

Apps that update their target to Android 13 or above and use the advertising ID need `com.google.android.gms.permission.AD_ID` (ads SDKs often merge it automatically). If the app does not use it, remove it with `tools:node="remove"`. For advertising, use it in place of other device identifiers. The App content page checked on 2026-11-09 lists no separate Advertising ID declaration: cover it in Data safety and the Ads declaration, and answer any further question the Console shows.

## Ads

Read each interstitial call site. Not allowed: ads that imitate app UI; blocking use until someone clicks an ad or shares data; unexpected full-screen ads such as at the start of a level or before a splash screen; repeated interstitials that interrupt a task; false dismiss buttons; ads placed where people normally tap or that interrupt exit; lockscreen ads unless that is the app's sole purpose. Full-screen interstitials must be closeable after 15 seconds; opt-in and rewarded ads are exempt. Ads must match the content rating. Declare "contains ads" on the App content page.

## Payments and subscriptions

In-app items, subscriptions, features, content and cloud services must use Play Billing unless an exception applies. Exempt: payments primarily for physical goods or services, bill remittances, peer-to-peer payments, auctions, tax-exempt donations, and gambling. Apps may not steer users to other payment methods except under these exceptions or enrolled regional programs (alternative billing, external offers). Disclose terms and pricing clearly. In-app prices must match the Play billing UI. Listings must say when features cost extra. Disclose loot-box odds near the purchase. For subscription details, read the current Subscriptions article (*not re-verified*).

## User-generated content

Apps with UGC need: terms accepted before creating or uploading; defined and prohibited objectionable content; robust, ongoing moderation; an in-app way to report content and users (for verified or registered users, or public UGC); an in-app way to block users (for direct messaging, tagging, mentions, or public UGC); enforcement. Incidental sexual content must be filtered by default and children barred with an age screen. Answer the content rating questionnaire accurately.

## Restricted content

If the app's purpose touches one of these, open that article and check what it needs; do not rely on memory:
[Child Endangerment](https://support.google.com/googleplay/android-developer/answer/9878809) · [Inappropriate Content](https://support.google.com/googleplay/android-developer/answer/9878810) · [Financial Services](https://support.google.com/googleplay/android-developer/answer/9876821) · [Real-Money Gambling](https://support.google.com/googleplay/android-developer/answer/9877032) · [Illegal Activities](https://support.google.com/googleplay/android-developer/answer/9878877) · [Health](https://support.google.com/googleplay/android-developer/answer/16679511) · [Blockchain](https://support.google.com/googleplay/android-developer/answer/13607354) · [AI-Generated Content](https://support.google.com/googleplay/android-developer/answer/13985936) · [Age-Restricted Content](https://support.google.com/googleplay/android-developer/answer/16302250). Listings and metadata must also match what the app does, with no hidden or undocumented features. Check names, artwork and text sources for IP and impersonation risk.

## Quality and code delivery

Apps must not crash, freeze or fail to load, and need real utility: static text-only or PDF-only apps and apps with very little content are disallowed. Apps may update only through Google Play and may not download executable code (dex, JAR, .so) from elsewhere. Code interpreted in a VM, such as JavaScript in a WebView, is excepted, but must not enable policy violations; apply this to over-the-air JS updates. Do not load untrusted web content in a WebView with a JavaScript interface.

## Release configuration

A release signed with the debug key or marked debuggable cannot ship. In a repo-owned `android/`, tell the developer to set up release signing; do not create keystores or touch credentials. In a gitignored generated `android/` (`coverage.generated_native_dirs`), the template's debug signing is normal if EAS or CI applies real signing, so ask them to confirm.

R8 is not a Play policy requirement, but Google says to always enable optimization for release builds: code shrinking (`isMinifyEnabled`) and resource shrinking (`isShrinkResources`), or `optimization { enable = true }` on AGP 9.3+. On Expo, set `enableMinifyInReleaseBuilds` and `enableShrinkResourcesInReleaseBuilds` in `expo-build-properties`. Ask before turning it on, because it can break code that uses reflection and needs keep rules; then test a release build on a device. Upload the deobfuscation file so crash reports stay readable.

## Testing before production

Personal developer accounts created after 2023-11-13 must run a closed test with at least 12 testers opted in continuously for at least 14 days, then choose **Apply for production** on the Dashboard. Plan this time before any launch date; ask whether the account is personal or an organization.

Uploading a bundle triggers a pre-launch report: a crawler checks stability, compatibility, performance and accessibility on test-lab devices, subject to lab capacity. Purchases cannot be tested there. Add a dedicated test account in its settings if the app needs a login. It complements real-device testing and does not replace it.

After launch, watch Android vitals. Play's bad-behavior thresholds are a 1.09% user-perceived crash rate and 0.47% ANR rate overall, or 8% on a single device model. Do not add an analytics or crash SDK just to be ready for release: each one adds Data safety, privacy policy and consent work.

## Store listing

Limits: title 30 characters, short description 80, full description 4,000. No emoji or ALL CAPS in the title unless part of the brand. Across the listing: no performance, ranking, price or program claims ("#1", "App of the year", "Best of Play", "Popular", "New", "Editor's choice", "10% off", "free for limited time"), no repetitive or unrelated keywords, no anonymous testimonials, and no other brands or celebrity names without permission. Screenshots must show the real app. Descriptions must be accurate and clear, and excessive length or repetition can itself be a violation. Keyword research is not part of this skill.

## Families and children

The Families policy applies when a target audience includes children. Apps showing ads to children or users of unknown age may use only Google Play Families Self-Certified Ads SDKs, with no interest-based ads or remarketing. Solely child-directed apps must not transmit the advertising ID or hardware identifiers, request AD_ID when targeting API 33+, or request location. Mixed-audience apps need a neutral age screen. Keep Target audience, Data safety and the content rating accurate.

## Sign-in details for review

If any part of the app needs login, membership, location or other access, give reviewers everything needed under App content → Sign-in details, with any OTP or multi-factor steps under "Any other instructions". Credentials must keep working and must not depend on an OTP the reviewer can't receive or a region they can't reach.

## Release checklist (Google Play)

- [ ] Data safety form matches the data inventory, including SDK collection and sharing.
- [ ] Privacy policy URL in Play Console and accessible in the app.
- [ ] In-app account deletion and web deletion link (if accounts exist).
- [ ] Declarations for restricted permissions and foreground services; prominent disclosures implemented.
- [ ] App content: Ads, Sign-in details, Target audience and content, Content ratings.
- [ ] targetSdk meets the current requirement; release is not debug-signed; R8 considered.
- [ ] Closed test done if the account requires it; pre-launch report reviewed; tested on real devices.
- [ ] App Links hosts serve `/.well-known/assetlinks.json`.
- [ ] Store listing does not contradict the app's actual behaviour.
