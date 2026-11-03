#!/usr/bin/env python3
"""Ship-to-Store repository scanner: local, offline, read-only, stdlib only.

Walks an app repository, parses manifests and platform configs, and emits
LEADS for a store-readiness and privacy review. A lead is not a finding:
a matched API, an installed SDK, a declared permission or a URL literal does
not prove that data is collected or transmitted at runtime.

Never prints or stores secret values. Never executes target code or uses the
network. Writes nothing into the scanned repo: scan.json goes to a per-app
folder under the OS temp dir (override with --out-dir).

  scan.py --root PATH              full scan -> <temp>/ship-to-store/<app>-<hash>/scan.json, prints compact summary
  scan.py --root PATH --reuse      prints the cached summary when no scanned file changed
  scan.py --root PATH --show NAME  prints one section of scan.json (see SECTIONS), with --grep/--limit
"""
import argparse
import base64
import fnmatch
import hashlib
import json
import math
import os
import plistlib
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

VERSION = "1.0.0"
HERE = Path(__file__).resolve().parent
REPORT_DIR = "ship-to-store-report"
SECTIONS = ("app", "dependencies", "sdks", "permissions", "platform_config", "signals",
            "endpoints", "secrets", "env_files", "data_leads", "checks", "coverage")

MAX_FILE_BYTES = 2_000_000
MAX_LOCK_BYTES = 40_000_000
MAX_FILES = 25_000
MAX_HITS_PER_RULE = 200
MINIFIED_LINE = 1_000

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "bower_components", "vendor", "dist", "build", "out",
    ".next", ".nuxt", ".expo", ".expo-shared", ".dart_tool", ".pub-cache", ".gradle", ".idea",
    ".vscode", ".cxx", ".externalNativeBuild", "Pods", "Carthage", "DerivedData", "xcuserdata",
    ".build", ".swiftpm", "coverage", ".nyc_output", ".venv", "venv", "__pycache__", ".mypy_cache",
    ".pytest_cache", "target", "bin", "obj", ".terraform", ".cache", ".parcel-cache", ".turbo",
    ".svelte-kit", ".angular", "web-build", "generated", "Generated", ".fvm", "ephemeral",
    ".symlinks", ".plugin_symlinks", REPORT_DIR, ".claude",
}
SKIP_FILE_RE = re.compile(r"\.(min\.(js|css)|map|bundle\.js|chunk\.js|g\.dart|freezed\.dart|pb\.dart|generated\.\w+)$", re.I)
SOURCE_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".html", ".dart",
               ".swift", ".m", ".mm", ".h", ".kt", ".java", ".cs", ".xaml", ".razor", ".py", ".rb",
               ".go", ".php"}
CONFIG_EXTS = {".json", ".yaml", ".yml", ".xml", ".plist", ".entitlements", ".xcprivacy",
               ".properties", ".xcconfig", ".gradle", ".kts", ".toml", ".csproj", ".pbxproj"}
LOCKFILES = {"package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
             "pubspec.lock", "Podfile.lock", "Package.resolved"}
NAMED = {"Podfile", "Cartfile", "Gemfile", "requirements.txt", "go.mod"}
NO_URL_SCAN = {"package.json", "project.pbxproj", "AndroidManifest.xml", "Podfile", "Cartfile",
               "gradle-wrapper.properties", "gradle.properties"} | LOCKFILES
# build scripts list package repositories and Android drawable/layout XML carries template comments: neither is an app endpoint
NO_URL_SCAN_RE = re.compile(r"\.(gradle|kts)$|/res/(drawable|layout|anim|animator|color|mipmap|font|menu)[^/]*/")
DEBUG_VARIANT_RE = re.compile(r"(^|/)src/[^/]*debug[^/]*/", re.I)
DEBUG_SUFFIX = " [debug build only]"
TEST_PARTS = {"test", "tests", "__tests__", "spec", "specs", "__mocks__", "mocks", "fixtures",
              "e2e", "androidtest", "uitests", "example", "examples", "storybook", "stories",
              ".storybook", "integration_test", "test_driver"}
TEST_FILE_RE = re.compile(r"(\.(test|spec)\.\w+$|Tests?\.(swift|kt|java|m|cs)$|_test\.(dart|go|py)$)")
COMMENT_PREFIXES = ("//", "/*", "*", "<!--")
HASH_COMMENT_EXTS = {".py", ".rb", ".yaml", ".yml", ".toml", ".properties", ".sh"}

# --- data categories, with the closest Apple / Google Play label (always verify) -----------
DATA_CATEGORIES = {
    "precise_location": ("Precise location", "Location > Precise Location", "Location > Precise location"),
    "approximate_location": ("Approximate location", "Location > Coarse Location", "Location > Approximate location"),
    "email": ("Email address", "Contact Info > Email Address", "Personal info > Email address"),
    "phone": ("Phone number", "Contact Info > Phone Number", "Personal info > Phone number"),
    "name": ("Name", "Contact Info > Name", "Personal info > Name"),
    "physical_address": ("Physical address", "Contact Info > Physical Address", "Personal info > Address"),
    "other_personal": ("Other personal info (e.g. date of birth)", "Contact Info > Other User Contact Info (verify)", "Personal info > Other info"),
    "sensitive_info": ("Sensitive info (e.g. health, beliefs, orientation, government ID)", "Sensitive Info > Sensitive Info", "Personal info > sensitive types / Other info (verify)"),
    "user_id": ("User ID", "Identifiers > User ID", "Personal info > User IDs"),
    "device_id": ("Device ID", "Identifiers > Device ID", "Device or other IDs"),
    "advertising_id": ("Advertising ID", "Identifiers > Device ID (tracking if linked with third-party data)", "Device or other IDs"),
    "photos_videos": ("Photos or videos", "User Content > Photos or Videos", "Photos and videos"),
    "audio": ("Audio recordings", "User Content > Audio Data", "Audio files > Voice or sound recordings"),
    "contacts": ("Contacts", "Contacts > Contacts", "Contacts"),
    "calendar": ("Calendar events", "User Content > Other User Content (verify)", "Calendar > Calendar events"),
    "health_fitness": ("Health and fitness", "Health & Fitness", "Health and fitness"),
    "messages": ("Messages (SMS, email, in-app)", "User Content > Emails or Text Messages", "Messages"),
    "files_docs": ("Files and documents", "User Content > Other User Content", "Files and docs"),
    "installed_apps": ("Installed apps", "Usage Data > Other Usage Data (verify)", "App activity > Installed apps"),
    "app_interactions": ("App interactions / analytics events", "Usage Data > Product Interaction", "App activity > App interactions"),
    "crash_diagnostics": ("Crash logs", "Diagnostics > Crash Data", "App info and performance > Crash logs"),
    "performance_diagnostics": ("Performance diagnostics", "Diagnostics > Performance Data", "App info and performance > Diagnostics"),
    "payment_info": ("Payment info", "Financial Info > Payment Info", "Financial info > User payment info"),
    "purchase_history": ("Purchase history", "Purchases > Purchase History", "Financial info > Purchase history"),
    "user_content": ("Other user-generated content", "User Content > Other User Content", "App activity > Other user-generated content"),
    "advertising_data": ("Advertising data", "Usage Data > Advertising Data", "App activity > Other actions (verify)"),
}

# Android permission (without "android.permission.") -> (data category, Play policy note)
ANDROID_PERMS = {
    "ACCESS_FINE_LOCATION": ("precise_location", None),
    "ACCESS_COARSE_LOCATION": ("approximate_location", None),
    "ACCESS_BACKGROUND_LOCATION": ("precise_location", "Background location is restricted: Play Console declaration, prominent disclosure and review required"),
    "CAMERA": ("photos_videos", None),
    "RECORD_AUDIO": ("audio", None),
    "READ_CONTACTS": ("contacts", None),
    "WRITE_CONTACTS": ("contacts", None),
    "READ_CALENDAR": ("calendar", None),
    "WRITE_CALENDAR": ("calendar", None),
    "READ_MEDIA_IMAGES": ("photos_videos", "Photo and video permissions policy: declaration required unless the system photo picker is insufficient"),
    "READ_MEDIA_VIDEO": ("photos_videos", "Photo and video permissions policy: declaration required unless the system photo picker is insufficient"),
    "READ_MEDIA_VISUAL_USER_SELECTED": ("photos_videos", None),
    "READ_MEDIA_AUDIO": ("audio", None),
    "READ_EXTERNAL_STORAGE": ("files_docs", None),
    "WRITE_EXTERNAL_STORAGE": ("files_docs", None),
    "MANAGE_EXTERNAL_STORAGE": ("files_docs", "All files access is restricted: Play Console declaration required"),
    "READ_SMS": ("messages", "SMS/Call Log permissions are restricted to default handlers: declaration required"),
    "RECEIVE_SMS": ("messages", "SMS/Call Log permissions are restricted to default handlers: declaration required"),
    "SEND_SMS": ("messages", "SMS/Call Log permissions are restricted to default handlers: declaration required"),
    "RECEIVE_MMS": ("messages", "SMS/Call Log permissions are restricted to default handlers: declaration required"),
    "READ_CALL_LOG": ("messages", "SMS/Call Log permissions are restricted to default handlers: declaration required"),
    "WRITE_CALL_LOG": ("messages", "SMS/Call Log permissions are restricted to default handlers: declaration required"),
    "PROCESS_OUTGOING_CALLS": ("messages", "SMS/Call Log permissions are restricted to default handlers: declaration required"),
    "READ_PHONE_STATE": ("device_id", None),
    "READ_PHONE_NUMBERS": ("phone", None),
    "BODY_SENSORS": ("health_fitness", None),
    "BODY_SENSORS_BACKGROUND": ("health_fitness", None),
    "ACTIVITY_RECOGNITION": ("health_fitness", None),
    "QUERY_ALL_PACKAGES": ("installed_apps", "QUERY_ALL_PACKAGES is restricted: declaration required"),
    "REQUEST_INSTALL_PACKAGES": (None, "REQUEST_INSTALL_PACKAGES is restricted: declaration required"),
    "USE_EXACT_ALARM": (None, "USE_EXACT_ALARM is restricted to alarm/timer/calendar core functionality"),
    "SCHEDULE_EXACT_ALARM": (None, "Review the exact alarm policy"),
    "USE_FULL_SCREEN_INTENT": (None, "Full-screen intent: declaration required on Android 14+ unless calling/alarm app"),
    "BIND_ACCESSIBILITY_SERVICE": (None, "Accessibility API use is restricted: declaration and review"),
    "BIND_VPN_SERVICE": (None, "VpnService is restricted to VPN core functionality"),
    "AD_ID": ("advertising_id", "Declare Advertising ID use in Play Console (App content)"),
}
ANDROID_PREFIX_PERMS = {
    "FOREGROUND_SERVICE_": (None, "Foreground service types require a Play Console declaration"),
    "health.": ("health_fitness", "Health Connect permissions require a Play Console declaration"),
}
IOS_KEYS = {
    "NSCameraUsageDescription": "photos_videos",
    "NSMicrophoneUsageDescription": "audio",
    "NSPhotoLibraryUsageDescription": "photos_videos",
    "NSPhotoLibraryAddUsageDescription": None,
    "NSLocationWhenInUseUsageDescription": "precise_location",
    "NSLocationAlwaysAndWhenInUseUsageDescription": "precise_location",
    "NSLocationAlwaysUsageDescription": "precise_location",
    "NSContactsUsageDescription": "contacts",
    "NSCalendarsUsageDescription": "calendar",
    "NSCalendarsFullAccessUsageDescription": "calendar",
    "NSCalendarsWriteOnlyAccessUsageDescription": None,
    "NSHealthShareUsageDescription": "health_fitness",
    "NSHealthUpdateUsageDescription": "health_fitness",
    "NSMotionUsageDescription": "health_fitness",
    "NSSpeechRecognitionUsageDescription": "audio",
    "NSUserTrackingUsageDescription": "advertising_id",
}
# capability -> iOS purpose-string keys that satisfy it (any one)
CAP_IOS_KEYS = {
    "camera": ["NSCameraUsageDescription"],
    "microphone": ["NSMicrophoneUsageDescription"],
    "photos": ["NSPhotoLibraryUsageDescription", "NSPhotoLibraryAddUsageDescription"],
    "location": ["NSLocationWhenInUseUsageDescription", "NSLocationAlwaysAndWhenInUseUsageDescription"],
    "background_location": ["NSLocationAlwaysAndWhenInUseUsageDescription"],
    "contacts": ["NSContactsUsageDescription"],
    "calendar": ["NSCalendarsUsageDescription", "NSCalendarsFullAccessUsageDescription", "NSCalendarsWriteOnlyAccessUsageDescription"],
    "health": ["NSHealthShareUsageDescription", "NSHealthUpdateUsageDescription"],
    "motion": ["NSMotionUsageDescription"],
    "bluetooth": ["NSBluetoothAlwaysUsageDescription"],
    "speech": ["NSSpeechRecognitionUsageDescription"],
    "biometrics": ["NSFaceIDUsageDescription"],
    "tracking": ["NSUserTrackingUsageDescription"],
}

# --- source-code rules: (id, kind, capability, data category, confidence, regex, ext filter) ---
SWIFT_OBJC = {".swift", ".m", ".mm", ".h"}
R = lambda p, flags=0: re.compile(p, flags)  # noqa: E731
RULES = [
    ("location", "sensitive_api", "location", "precise_location", "medium",
     R(r"\bCLLocationManager\b|requestWhenInUseAuthorization|startUpdatingLocation|FusedLocationProviderClient|requestLocationUpdates|getLastKnownLocation|navigator\.geolocation|Geolocation\.(getCurrentPosition|watchPosition|GetLocationAsync|GetLastKnownLocationAsync)|getCurrentPositionAsync|watchPositionAsync|requestForegroundPermissionsAsync|Geolocator\.(getCurrentPosition|getPositionStream|requestPermission)|getLastKnownPosition"), None),
    ("background_location", "sensitive_api", "background_location", "precise_location", "medium",
     R(r"requestAlwaysAuthorization|allowsBackgroundLocationUpdates|startMonitoringSignificantLocationChanges|requestBackgroundPermissionsAsync|startLocationUpdatesAsync|ACCESS_BACKGROUND_LOCATION"), None),
    ("camera", "sensitive_api", "camera", "photos_videos", "medium",
     R(r"\bAVCaptureDevice\b|\bAVCaptureSession\b|sourceType\s*=\s*\.camera|androidx\.camera|cameraManager\.openCamera|\blaunchCamera\b|launchCameraAsync|requestCameraPermissionsAsync|ImageSource\.camera|getUserMedia|MediaPicker\.(Default\.)?Capture(Photo|Video)Async|useCameraDevice|CameraController\("), None),
    ("microphone", "sensitive_api", "microphone", "audio", "medium",
     R(r"\bAVAudioRecorder\b|requestRecordPermission|\bMediaRecorder\b|\bAudioRecord\b|Audio\.Recording|requestRecordingPermissionsAsync|AudioRecorder\("), None),
    ("speech", "sensitive_api", "speech", "audio", "medium",
     R(r"\bSFSpeechRecognizer\b|\bSpeechRecognizer\.createSpeechRecognizer|@react-native-voice|speech_to_text"), None),
    ("photos", "sensitive_api", "photos", "photos_videos", "medium",
     R(r"\bPHPhotoLibrary\b|\bPHPickerViewController\b|MediaStore\.(Images|Video)|PickVisualMedia|launchImageLibrary(Async)?\b|ImageSource\.gallery|\bpickMultiImage\b|\.pickImage\(|MediaPicker\.(Default\.)?Pick(Photo|Video)Async|CameraRoll\."), None),
    ("contacts", "sensitive_api", "contacts", "contacts", "medium",
     R(r"\bCNContactStore\b|ContactsContract|Contacts\.(getAll|requestPermission|getContactsAsync)|getContactsAsync|FlutterContacts|ContactsService\.getContacts|Contacts\.Default"), None),
    ("calendar", "sensitive_api", "calendar", "calendar", "medium",
     R(r"\bEKEventStore\b|CalendarContract|Calendar\.(getEventsAsync|requestCalendarPermissionsAsync)|DeviceCalendarPlugin"), None),
    ("health", "sensitive_api", "health", "health_fitness", "medium",
     R(r"\bHKHealthStore\b|HealthConnectClient|androidx\.health\.connect|AppleHealthKit|Health\(\)\.(requestAuthorization|getHealthDataFromTypes)"), None),
    ("motion", "sensitive_api", "motion", "health_fitness", "low",
     R(r"\bCMMotionActivityManager\b|\bCMPedometer\b|Pedometer\.(stepCountStream|watchStepCount)|TYPE_STEP_COUNTER"), None),
    ("bluetooth", "sensitive_api", "bluetooth", None, "low",
     R(r"\bCBCentralManager\b|BluetoothLeScanner|BluetoothAdapter\.getDefaultAdapter|new BleManager|FlutterBluePlus"), None),
    ("biometrics", "sensitive_api", "biometrics", None, "low",
     R(r"\bLAContext\b|BiometricPrompt|LocalAuthentication\.authenticateAsync|authenticateAsync\(|local_auth"), None),
    ("advertising_id", "sensitive_api", "tracking", "advertising_id", "high",
     R(r"\bASIdentifierManager\b|advertisingIdentifier|AdvertisingIdClient|getAdvertisingId(Info|Async)?\b"), None),
    ("att_request", "signal", "tracking", None, "high",
     R(r"requestTrackingAuthorization|\bATTrackingManager\b|requestTrackingPermissionsAsync|AppTrackingTransparency\.requestTrackingAuthorization|getTrackingStatus\("), None),
    ("device_id", "sensitive_api", None, "device_id", "medium",
     R(r"identifierForVendor|Settings\.Secure\.ANDROID_ID|getAndroidId\b|getUniqueId\(|\bgetImei\(|getSerial\(|Build\.SERIAL|getDeviceId\("), None),
    ("telephony", "sensitive_api", None, "phone", "low",
     R(r"getLine1Number|TelephonyManager|SubscriptionManager\.getActiveSubscriptionInfoList"), None),
    ("sms_calllog", "sensitive_api", None, "messages", "medium",
     R(r"\bSmsManager\b|Telephony\.Sms|CallLog\.Calls"), None),
    ("clipboard_read", "sensitive_api", None, "user_content", "low",
     R(r"UIPasteboard\.general\.(string|strings|image|url)\b|getPrimaryClip|Clipboard\.(getString|getStringAsync|getData|GetTextAsync)\("), None),
    ("installed_apps", "sensitive_api", None, "installed_apps", "low",
     R(r"getInstalledPackages|getInstalledApplications|queryIntentActivities"), None),
    ("webview_bridge", "risk", None, None, "low",
     R(r"addJavascriptInterface|setJavaScriptEnabled\(true\)|setAllowUniversalAccessFromFileURLs\(true\)"), None),
    ("input_email", "data_collection", None, "email", "medium",
     R(r"""textContentType\s*=\s*\{?\s*["'](emailAddress|username)|keyboardType\s*=\s*\{?\s*["']email-address|autoComplete\s*=\s*\{?\s*["']email|TextInputType\.emailAddress|inputType\s*=\s*["']textEmailAddress|UITextContentType\.emailAddress|\.textContentType\(\.emailAddress\)|type\s*=\s*["']email["']|Keyboard\.Email"""), None),
    ("input_phone", "data_collection", None, "phone", "medium",
     R(r"""keyboardType\s*=\s*\{?\s*["']phone-pad|textContentType\s*=\s*\{?\s*["']telephoneNumber|autoComplete\s*=\s*\{?\s*["']tel|TextInputType\.phone|inputType\s*=\s*["']phone|UITextContentType\.telephoneNumber|type\s*=\s*["']tel["']|Keyboard\.Telephone"""), None),
    ("input_name_address", "data_collection", None, "name", "low",
     R(r"""textContentType\s*=\s*\{?\s*["'](name|givenName|familyName|fullStreetAddress|postalCode)["']|autoComplete\s*=\s*\{?\s*["'](name|given-name|family-name|street-address|postal-code)["']|TextInputType\.(name|streetAddress)|inputType\s*=\s*["']text(PersonName|PostalAddress)"""), None),
    ("input_dob", "data_collection", None, "other_personal", "low",
     R(r"\b(dateOfBirth|date_of_birth|birthDate|birthdate|birth_date|birthday)\b"), None),
    ("sensitive_fields", "data_collection", None, "sensitive_info", "low",
     R(r"\b(ethnicity|religion|sexualOrientation|sexual_orientation|politicalViews|ssn|socialSecurityNumber|passportNumber|aadhaar|nationalId|national_id|medicalCondition|diagnosis)\b", re.I), None),
    ("auth_signup", "signal", None, "email", "medium",
     R(r"createUserWithEmailAndPassword|auth\.signUp\(|\.signUp\(\{|signUpWithEmail|Auth\.signUp|registerUser\(|createAccount\("), None),
    ("phone_auth", "signal", None, "phone", "medium",
     R(r"signInWithPhoneNumber|verifyPhoneNumber|PhoneAuthProvider|signInWithOtp\(\s*\{\s*phone"), None),
    ("social_login", "signal", None, "user_id", "medium",
     R(r"GoogleSignin\.|\bGIDSignIn\b|signInWithGoogle|GoogleSignIn\(|LoginManager\.(logIn|getInstance)|FacebookAuth\.|signInWithFacebook|TwitterAuthProvider|GithubAuthProvider|signInWithPopup\(|signInWithOAuth\("), None),
    ("apple_login", "signal", None, None, "high",
     R(r"ASAuthorizationAppleIDProvider|AppleAuthentication\.|appleAuth\.|SignInWithApple|signInWithApple|AppleAuthProvider|OAuthProvider\(['\"]apple\.com|provider:\s*['\"]apple['\"]"), None),
    ("account_deletion", "signal", None, None, "medium",
     R(r"deleteAccount|delete_account|deleteUser\(|deleteMyAccount|currentUser\??!?\.delete\(|user\.delete\(\)|auth\.admin\.deleteUser|accountDeletion|account[/_-]delet|closeAccount", re.I), None),
    ("analytics_event", "data_collection", None, "app_interactions", "medium",
     R(r"\.logEvent\s*\(|\.setUserProperty\s*\(|\.setUserProperties\s*\(|mixpanel\.track\(|amplitude\.track\(|posthog\.capture\(|\bAnalytics\.track\(|\.trackEvent\s*\(|logCustomEvent\("), None),
    ("analytics_identify", "data_collection", None, "user_id", "medium",
     R(r"\.setUserId\s*\(|\.identify\s*\(|Sentry\.setUser\(|setUserIdentifier\(|crashlytics\(\)\.setUserId|setUserID\(|Bugsnag\.setUser"), None),
    ("payments_iap", "signal", None, "purchase_history", "medium",
     R(r"\bSKPaymentQueue\b|Product\.products\(|BillingClient|RNIap|requestPurchase\(|InAppPurchase\.instance|Purchases\.(configure|purchasePackage|shared)"), None),
    ("payments_external", "signal", None, "payment_info", "medium",
     R(r"presentPaymentSheet|initPaymentSheet|StripeProvider|confirmPayment\(|PaymentSheet\(|new Razorpay|RazorpayCheckout|Razorpay\(\)|BraintreeClient|PayPalCheckout|checkout\.sessions\.create"), None),
    ("push_notifications", "signal", None, "device_id", "low",
     R(r"registerForRemoteNotifications|messaging\(\)\.getToken|FirebaseMessaging\.(instance|getInstance)|getExpoPushTokenAsync|getDevicePushTokenAsync|OneSignal\.(initialize|setAppId|login)"), None),
    ("network_client", "signal", None, None, "low",
     R(r"\bfetch\(|\baxios[.(]|XMLHttpRequest|\bURLSession\b|\bAF\.request|Retrofit\.Builder|OkHttpClient|new HttpClient\(|\bhttp\.(get|post)\(|\bDio\(|HttpURLConnection"), None),
    ("pii_logging", "risk", None, None, "medium",
     R(r"(console\.(log|info|debug|warn)|\bprint|debugPrint|\bNSLog|\bLog\.[dviwe]|Timber\.[dviwe]|\blogger\.\w+|os_log)\s*\(.*(email|password|passwd|token|phone|ssn|card_?number|creditcard|latitude|longitude)", re.I), None),
    ("insecure_storage", "risk", None, None, "medium",
     R(r"(AsyncStorage\.setItem|localStorage\.setItem|SharedPreferences|\.put(String|Int)\(|UserDefaults\.standard\.set|NSUserDefaults|prefs\.setString|Preferences\.Set|GetStorage\(\)\.write|MMKV)\s*.*(token|password|passwd|secret|jwt|session)", re.I), None),
    ("children", "signal", None, None, "low",
     R(r"\b(COPPA|tagForChildDirectedTreatment|tag_for_child_directed_treatment|TagForChildDirectedTreatment|tagForUnderAgeOfConsent|isChildDirected|parentalConsent|parental_gate|ageGate|age_gate|kidsMode|designedForFamilies)\b"), None),
    # explicit opt-out of child-directed ad treatment; a "children" hit on the same line is dropped
    ("children_opt_out", "signal", None, None, "medium",
     R(r"(tagForChildDirectedTreatment|tag_for_child_directed_treatment|tagForUnderAgeOfConsent|isChildDirected)\s*[:=(]\s*(false|TagForChildDirectedTreatment\.no|0)\b", re.I), None),
    ("privacy_policy_link", "signal", None, None, "medium",
     R(r"privacy[-_ ]?policy|privacyPolicy|/privacy\b", re.I), None),
    ("consent_tooling", "signal", None, None, "medium",
     R(r"ConsentInformation|UserMessagingPlatform|requestConsentInfoUpdate|ConsentForm|AdsConsent\.|gatherConsent|canRequestAds|PrivacyOptionsRequirementStatus|setConsent\(|setAnalyticsCollectionEnabled|setCrashlyticsCollectionEnabled|OneTrust|Didomi|Usercentrics|Cookiebot|gdprApplies|IABTCF_|optOut\(|opt_out|consentGiven|hasConsent"), None),
    ("ai_call", "data_collection", None, "user_content", "medium",
     R(r"new OpenAI\(|OpenAI\(api_key|chat\.completions\.create|new Anthropic\(|messages\.create\(|GenerativeModel\(|generateContent\(|getGenerativeModel"), None),
    # Apple required-reason API categories (native iOS code only)
    ("rr_user_defaults", "required_reason_api", None, None, "high", R(r"\bUserDefaults\b|\bNSUserDefaults\b"), SWIFT_OBJC),
    ("rr_file_timestamp", "required_reason_api", None, None, "medium",
     R(r"\.creationDate\b|\.modificationDate\b|contentModificationDate|creationDateKey|NSFileCreationDate|NSFileModificationDate|\bgetattrlist\(|\bfstat\(|\bstat\("), SWIFT_OBJC),
    ("rr_boot_time", "required_reason_api", None, None, "high", R(r"systemUptime|mach_absolute_time"), SWIFT_OBJC),
    ("rr_disk_space", "required_reason_api", None, None, "high",
     R(r"volumeAvailableCapacity|NSFileSystemFreeSize|systemFreeSize|\bstatfs\(|\bstatvfs\("), SWIFT_OBJC),
    ("rr_active_keyboards", "required_reason_api", None, None, "high", R(r"activeInputModes"), SWIFT_OBJC),
]
CHILD_OPT_OUT = next(r[5] for r in RULES if r[0] == "children_opt_out")
RR_TYPES = {
    "rr_user_defaults": "NSPrivacyAccessedAPICategoryUserDefaults",
    "rr_file_timestamp": "NSPrivacyAccessedAPICategoryFileTimestamp",
    "rr_boot_time": "NSPrivacyAccessedAPICategorySystemBootTime",
    "rr_disk_space": "NSPrivacyAccessedAPICategoryDiskSpace",
    "rr_active_keyboards": "NSPrivacyAccessedAPICategoryActiveKeyboards",
}

# --- secrets: values are matched but never stored or printed --------------------------------
SECRET_RULES = [
    ("private_key", "critical", R(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----")),
    ("aws_access_key_id", "critical", R(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("stripe_live_secret", "critical", R(r"\b(?:sk|rk)_live_[0-9A-Za-z]{10,}\b")),
    ("stripe_test_secret", "low", R(r"\b(?:sk|rk)_test_[0-9A-Za-z]{10,}\b")),
    ("anthropic_api_key", "critical", R(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("openai_api_key", "critical", R(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{32,}")),
    ("github_token", "high", R(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})")),
    ("slack_token", "high", R(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("google_api_key", "low", R(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("jwt", "medium", R(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
]
SECRET_NOTES = {
    "google_api_key": "Google/Firebase client API keys identify a project and ship in apps by design; confirm API restrictions are set.",
    "stripe_test_secret": "Test-mode key; still remove from source control.",
    "jwt": "Token embedded in source.",
    "supabase_anon_key": "Supabase anon key is public by design; safety depends on row-level security.",
    "supabase_service_role_key": "Service-role key bypasses row-level security; it must never ship in an app.",
    "generic_secret": "Credential-like value assigned to a secret-named variable.",
    "url_credentials": "Credentials embedded in a URL.",
    "url_query_secret": "Secret-like query parameter in a URL literal.",
}
SECRET_NAME = r"[A-Za-z0-9_.\-]*(?:api[_-]?key|apikey|secret|token|passw(?:or)?d|private[_-]?key|access[_-]?key|auth[_-]?key)[A-Za-z0-9_\-]*"
GENERIC_QUOTED = R(r"(?i)\b(" + SECRET_NAME + r")\b[\"']?\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']")
GENERIC_KV = R(r"(?i)^\s*(?:export\s+)?(" + SECRET_NAME + r")\s*[:=]\s*[\"']?([^\"'\s#]{8,})")
PLACEHOLDER_RE = R(r"(?i)your|xxx|example|placeholder|changeme|dummy|sample|redacted|replace|insert|todo|<|\$\{|\{\{|%\(|\$\(|process\.env|import\.meta|BuildConfig|@string/|getenv|environ")
URL_RE = R(r"""\b(?:https?|wss?)://[^\s'"`<>()\[\]{}\\,$|^]+""")
SENSITIVE_QUERY = {"key", "api_key", "apikey", "token", "access_token", "auth", "secret", "client_secret",
                   "password", "pass", "sig", "signature", "session", "code"}
IGNORE_HOSTS = {"schemas.android.com", "www.w3.org", "w3.org", "www.apple.com", "apple.com", "json-schema.org",
                "schemas.microsoft.com", "localhost", "127.0.0.1", "0.0.0.0", "10.0.2.2", "xmlpull.org",
                "ns.adobe.com", "purl.org", "xmlns.com", "schema.org", "www.example.com", "example.com",
                "example.org", "example.net", "reactnative.dev", "facebook.github.io", "developer.android.com",
                "developer.apple.com", "flutter.dev", "docs.flutter.dev", "dart.dev", "pub.dev",
                "docs.expo.dev", "www.apache.org", "opensource.org", "github.com", "npmjs.com", "www.npmjs.com"}
IGNORE_HOST_SUFFIX = (".example", ".example.com", ".test", ".invalid", ".local", ".localhost")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def line_of(text, needle, start=0):
    idx = text.find(needle, start)
    return text.count("\n", 0, idx) + 1 if idx >= 0 else None


def entropy(s):
    counts = {c: s.count(c) for c in set(s)}
    return -sum(n / len(s) * math.log2(n / len(s)) for n in counts.values())


def is_test_path(rel):
    parts = [p.lower() for p in Path(rel).parts]
    return any(p in TEST_PARTS for p in parts[:-1]) or bool(TEST_FILE_RE.search(parts[-1]))


def strip_android(name):
    return name[len("android.permission."):] if name.startswith("android.permission.") else name.rsplit(".", 1)[-1] if name.startswith("com.google.android.gms.permission.") else name


def android_perm_info(name):
    short = strip_android(name)
    if short in ANDROID_PERMS:
        return ANDROID_PERMS[short]
    for prefix, info in ANDROID_PREFIX_PERMS.items():
        if short.startswith(prefix) or name.startswith("android.permission." + prefix):
            return info
    return (None, None)


def redact_url(raw):
    """Return (safe_url, host, flags) with userinfo, query and long opaque path segments removed."""
    try:
        parts = urlsplit(raw.rstrip(".;:'\""))
        host = (parts.hostname or "").lower()
    except ValueError:
        return None, None, []
    flags = []
    if parts.username or parts.password:
        flags.append("credentials_in_url")
    if parts.query:
        names = {k.lower() for k, _ in parse_qsl(parts.query, keep_blank_values=True)}
        if names & SENSITIVE_QUERY:
            flags.append("secret_like_query")
    if parts.scheme in ("http", "ws"):
        flags.append("cleartext")
    segs = []
    for seg in parts.path.split("/"):
        opaque = len(seg) >= 20 and re.fullmatch(r"[A-Za-z0-9_\-=.%]+", seg) and re.search(r"\d", seg)
        segs.append("[REDACTED]" if opaque or "@" in seg else seg)
    path = "/".join(segs)[:80]
    port = ""
    try:
        port = ":%d" % parts.port if parts.port else ""
    except ValueError:
        pass
    return "%s://%s%s%s" % (parts.scheme, host, port, path), host, flags


def redact_line(line):
    """Redact secrets and URL query/userinfo from a line; used only when --snippets is requested."""
    for _rid, _sev, rx in SECRET_RULES:
        line = rx.sub("[REDACTED]", line)
    line = GENERIC_QUOTED.sub(lambda m: m.group(0).replace(m.group(2), "[REDACTED]"), line)
    line = URL_RE.sub(lambda m: redact_url(m.group(0))[0] or "[URL]", line)
    line = "".join(c if c.isprintable() else " " for c in line)
    return line.strip()[:160]


def jwt_role(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("role")
    except Exception:
        return None


class Scan:
    def __init__(self, root, catalog, snippets=False):
        self.root = root
        self.catalog = catalog
        self.snippets = snippets
        self.deps = []
        self.dep_keys = set()
        self.frameworks = {}
        self.web_frameworks = {}
        self.languages = {}
        self.identifiers = {}
        self.entry_points = []
        self.android_perms = []
        self.ios_keys = []
        self.expo = {}
        self.platform = {"ios_plists": [], "entitlements": [], "privacy_manifests": [], "android_manifests": [],
                         "ats": [], "background_modes": [], "url_schemes": [], "associated_domains": [],
                         "app_links": [], "deep_links": [], "exported_components": [], "cleartext": [],
                         "allow_backup": [], "foreground_services": [], "firebase_config": [], "export_compliance": [],
                         "android_meta_data": [], "target_sdk": [], "min_sdk": [], "maui": []}
        self.signals = {}
        self.signal_counts = {}
        self.endpoints = {}
        self.secrets = []
        self.env_files = []
        self.gitignore_lines = []
        self.coverage = {"files_seen": 0, "files_scanned": 0, "skipped_dirs": [], "skipped_large": [],
                         "skipped_binary": 0, "skipped_generated": 0, "symlinks_skipped": [], "minified_skipped": [],
                         "encoding_replaced": [], "parse_errors": [], "unreadable": [], "file_limit_hit": False,
                         "test_context_hits": 0, "truncated_rules": []}

    # ---- recorders -------------------------------------------------------------------------
    def framework(self, fid, rel, line=None):
        self.frameworks.setdefault(fid, "%s:%s" % (rel, line) if line else rel)

    def add_dep(self, eco, name, version, rel, line=None, direct=True, dev=False):
        name = name.strip()
        if not name:
            return
        key = (eco, name.lower(), rel)
        if key in self.dep_keys:
            return
        if not direct and not self.catalog_match(eco, name):
            return  # keep only catalog-relevant transitive deps; totals are still counted
        self.dep_keys.add(key)
        self.deps.append({"ecosystem": eco, "name": name, "version": (version or "")[:40] or None,
                          "path": rel, "line": line, "direct": direct, "dev": dev})

    def parse_error(self, rel, err):
        self.coverage["parse_errors"].append({"path": rel, "error": ("%s: %s" % (type(err).__name__, err))[:160]})

    def signal(self, rule_id, rel, line, match, text_line):
        test = is_test_path(rel)
        if test:
            self.coverage["test_context_hits"] += 1
        bucket = self.signals.setdefault(rule_id, [])
        self.signal_counts[rule_id] = self.signal_counts.get(rule_id, 0) + 1
        if len(bucket) >= MAX_HITS_PER_RULE:
            if rule_id not in self.coverage["truncated_rules"]:
                self.coverage["truncated_rules"].append(rule_id)
            return
        hit = {"path": rel, "line": line, "match": match[:80], "test_context": test}
        if self.snippets:
            hit["snippet"] = redact_line(text_line)
        bucket.append(hit)

    def secret(self, rule, severity, rel, line, length, note_key=None):
        if any(s["path"] == rel and s["line"] == line for s in self.secrets):
            return
        self.secrets.append({"rule": rule, "severity": severity, "path": rel, "line": line,
                             "value_length": length, "note": SECRET_NOTES.get(note_key or rule, ""),
                             "test_context": is_test_path(rel)})

    # ---- catalog -----------------------------------------------------------------------------
    def catalog_match(self, eco, name):
        lname = name.lower()
        base = lname.split("/")[0]
        hits = []
        for sdk in self.catalog.get("sdks", []):
            for pat in sdk.get("match", {}).get(eco, []):
                p = pat.lower()
                if eco == "spm":
                    ok = p in lname
                elif p.endswith("*"):
                    ok = lname.startswith(p[:-1])
                else:
                    ok = lname == p or (eco == "pod" and base == p)
                if ok:
                    hits.append(sdk)
                    break
        return hits

    def vendor_for_host(self, host):
        for sdk in self.catalog.get("sdks", []):
            for d in sdk.get("domains", []):
                if host == d or host.endswith("." + d):
                    return sdk
        return None


# ---- file walking ---------------------------------------------------------------------------
class F:
    __slots__ = ("path", "rel", "name", "ext", "kind", "size")

    def __init__(self, path, rel, name, ext, kind, size):
        self.path, self.rel, self.name, self.ext, self.kind, self.size = path, rel, name, ext, kind, size


def classify(name, ext):
    low = name.lower()
    if name in LOCKFILES:
        return "lock"
    if low == ".env" or low.startswith(".env.") or low.endswith(".env"):
        return "env"
    if name in NAMED or name == ".gitignore":
        return "manifest"
    if ext in SOURCE_EXTS:
        return "source"
    if ext in CONFIG_EXTS:
        return "config"
    return None


def walk(root, cov, max_files):
    isjunction = getattr(os.path, "isjunction", lambda p: False)
    root_real = os.path.join(os.path.realpath(root), "")
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        keep = []
        dir_real = os.path.realpath(dirpath)
        for d in sorted(dirnames):
            full = os.path.join(dirpath, d)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            # realpath mismatch also catches Windows junctions on Pythons without os.path.isjunction
            if os.path.islink(full) or isjunction(full) or os.path.realpath(full) != os.path.join(dir_real, d):
                cov["symlinks_skipped"].append(rel)
            elif d in SKIP_DIRS or d.endswith((".xcassets", ".framework", ".xcframework")):
                cov["skipped_dirs"].append(rel)
            else:
                keep.append(d)
        dirnames[:] = keep
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            ext = os.path.splitext(name)[1].lower()
            kind = classify(name, ext)
            if kind is None:
                continue
            cov["files_seen"] += 1
            if os.path.islink(full):
                cov["symlinks_skipped"].append(rel)
                continue
            if not os.path.join(os.path.realpath(full), "").startswith(root_real):
                cov["symlinks_skipped"].append(rel)
                continue
            if SKIP_FILE_RE.search(name):
                cov["skipped_generated"] += 1
                continue
            try:
                size = os.path.getsize(full)
            except OSError:
                cov["unreadable"].append(rel)
                continue
            limit = MAX_LOCK_BYTES if kind == "lock" else MAX_FILE_BYTES
            if size > limit:
                cov["skipped_large"].append({"path": rel, "bytes": size})
                continue
            if cov["files_scanned"] >= max_files:
                cov["file_limit_hit"] = True
                return
            cov["files_scanned"] += 1
            yield F(full, rel, name, ext, kind, size)


def decode(data, rel, cov):
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", "replace")
    if b"\x00" in data[:8192]:
        return None
    text = data.decode("utf-8-sig", "replace")
    if "\ufffd" in text:
        cov["encoding_replaced"].append(rel)
    return text


# ---- manifest / config handlers ---------------------------------------------------------------
MOBILE_NPM = {"react-native": "react-native", "expo": "expo", "@capacitor/core": "capacitor",
              "cordova-android": "cordova", "cordova-ios": "cordova", "@nativescript/core": "nativescript"}
WEB_NPM = {"next": "next.js", "react-dom": "react (web)", "vue": "vue", "nuxt": "nuxt", "@angular/core": "angular",
           "svelte": "svelte", "@sveltejs/kit": "sveltekit", "@remix-run/react": "remix", "astro": "astro"}


def h_package_json(s, f, data, text):
    pj = json.loads(text)
    if not isinstance(pj, dict):
        raise ValueError("package.json is not an object")
    names = set()
    for section, dev in (("dependencies", False), ("devDependencies", True),
                         ("optionalDependencies", False), ("peerDependencies", False)):
        deps = pj.get(section)
        if isinstance(deps, dict):
            for name, ver in deps.items():
                names.add(name)
                s.add_dep("npm", name, str(ver), f.rel, line_of(text, '"%s"' % name), True, dev)
    for n in names:
        if n in MOBILE_NPM:
            s.framework(MOBILE_NPM[n], f.rel, line_of(text, '"%s"' % n))
        if n in WEB_NPM:
            s.web_frameworks.setdefault(WEB_NPM[n], f.rel)
        if n.startswith("@ionic/"):
            s.framework("ionic", f.rel, line_of(text, '"%s"' % n))
    if isinstance(pj.get("main"), str) and ("expo" in names or "react-native" in names):
        s.entry_points.append("%s (package.json main)" % pj["main"])


def h_npm_lock(s, f, data, text):
    lj = json.loads(text)
    pk = lj.get("packages") or {}
    names = {k.rsplit("node_modules/", 1)[1] for k in pk if "node_modules/" in k}
    names |= set((lj.get("dependencies") or {}).keys())
    for n in names:
        s.add_dep("npm", n, None, f.rel, None, direct=False)


YARN_RE = R(r'^"?((?:@[^@/\s"]+/)?[^@/\s",]+)@')
PNPM_RE = R(r"""^\s{2}['"]?/?((?:@[^@/\s'"]+/)?[^@/\s'"]+)@""")


def h_yarn_lock(s, f, data, text):
    for line in text.splitlines():
        if line and not line[0].isspace() and not line.startswith("#"):
            m = YARN_RE.match(line)
            if m:
                s.add_dep("npm", m.group(1), None, f.rel, None, direct=False)


def h_pnpm_lock(s, f, data, text):
    for line in text.splitlines():
        m = PNPM_RE.match(line)
        if m:
            s.add_dep("npm", m.group(1), None, f.rel, None, direct=False)


def h_pubspec(s, f, data, text):
    section = None
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            section = line.split(":")[0].strip()
            continue
        if section in ("dependencies", "dev_dependencies"):
            m = re.match(r"^  ([A-Za-z0-9_]+)\s*:\s*(.*)$", line)
            if m:
                s.add_dep("pub", m.group(1), m.group(2).strip() or None, f.rel, i, True, section == "dev_dependencies")
                if m.group(1) == "flutter":
                    s.framework("flutter", f.rel, i)
    if "lib/main.dart" not in s.entry_points and (Path(f.path).parent / "lib" / "main.dart").exists():
        s.entry_points.append(str(Path(f.rel).parent / "lib" / "main.dart").replace("\\", "/").lstrip("./"))


def h_pubspec_lock(s, f, data, text):
    in_packages = False
    for line in text.splitlines():
        if not line.startswith(" "):
            in_packages = line.startswith("packages:")
            continue
        m = re.match(r"^  ([a-z0-9_]+):\s*$", line)
        if in_packages and m:
            s.add_dep("pub", m.group(1), None, f.rel, None, direct=False)


def h_podfile(s, f, data, text):
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"""^\s*pod\s+['"]([^'"]+)['"](?:\s*,\s*['"]([^'"]+)['"])?""", line)
        if m:
            s.add_dep("pod", m.group(1), m.group(2), f.rel, i)


def h_podfile_lock(s, f, data, text):
    in_pods = False
    for line in text.splitlines():
        if not line.startswith(" "):
            in_pods = line.startswith("PODS:")
            continue
        m = re.match(r'^  - "?([^\s"(]+)', line)
        if in_pods and m:
            s.add_dep("pod", m.group(1), None, f.rel, None, direct=False)


def h_package_swift(s, f, data, text):
    for m in re.finditer(r'\.package\s*\([^)]*?url:\s*"([^"]+)"', text):
        s.add_dep("spm", m.group(1), None, f.rel, text.count("\n", 0, m.start()) + 1)


def h_package_resolved(s, f, data, text):
    pj = json.loads(text)
    pins = pj.get("pins") or (pj.get("object") or {}).get("pins") or []
    for p in pins:
        url = p.get("location") or p.get("repositoryURL") or p.get("identity") or p.get("package") or ""
        ver = (p.get("state") or {}).get("version")
        s.add_dep("spm", url, ver, f.rel, None, direct=False)


def h_cartfile(s, f, data, text):
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r'^\s*(?:github|git|binary)\s+"([^"]+)"', line)
        if m:
            s.add_dep("spm", m.group(1), None, f.rel, i)


GRADLE_CONF = r"(?:implementation|api|compileOnly|runtimeOnly|kapt|ksp|annotationProcessor|\w+Implementation|\w+Api|classpath|coreLibraryDesugaring)"
GRADLE_DEP = R(r"""^\s*(""" + GRADLE_CONF + r""")\s*\(?\s*(?:platform\(\s*|enforcedPlatform\(\s*)?['"]([A-Za-z0-9_.\-]+):([A-Za-z0-9_.\-]+)(?::([^'"@]+))?""")


def gradle_values(s, f, text):
    for key, bucket in (("targetSdk", "target_sdk"), ("minSdk", "min_sdk")):
        for m in re.finditer(r"\b%s(?:Version)?\s*(?:=|:)?\s*\(?\s*([A-Za-z0-9_.]+)" % key, text):
            val = m.group(1)
            s.platform[bucket].append({"value": int(val) if val.isdigit() else val, "path": f.rel,
                                       "line": text.count("\n", 0, m.start()) + 1})
    m = re.search(r"""\bapplicationId\s*(?:=)?\s*['"]([^'"]+)['"]""", text)
    if m:
        s.identifiers.setdefault("android_application_id", m.group(1))


def h_gradle(s, f, data, text):
    for i, line in enumerate(text.splitlines(), 1):
        m = GRADLE_DEP.match(line)
        if m:
            conf = m.group(1)
            s.add_dep("maven", "%s:%s" % (m.group(2), m.group(3)), m.group(4), f.rel, i, True,
                      conf.lower().startswith(("test", "androidtest", "debug")))
    if re.search(r"com\.android\.application", text):
        s.framework("android-gradle-app", f.rel, line_of(text, "com.android.application"))
    if "com.google.gms.google-services" in text:
        s.platform["firebase_config"].append("%s:%s" % (f.rel, line_of(text, "com.google.gms.google-services")))
    gradle_values(s, f, text)


def h_properties(s, f, data, text):
    if f.name == "gradle.properties":
        gradle_values(s, f, text)


def h_versions_toml(s, f, data, text):
    section = None
    for i, line in enumerate(text.splitlines(), 1):
        st = line.strip()
        if st.startswith("["):
            section = st.strip("[]").strip()
            continue
        if section != "libraries" or "=" not in st or st.startswith("#"):
            continue
        m = re.search(r"""module\s*=\s*["']([^"':]+:[^"':]+)["']""", st) or \
            re.search(r"""=\s*["']([^"':]+:[^"':]+)(?::[^"']*)?["']""", st)
        if m:
            s.add_dep("maven", m.group(1), None, f.rel, i)
            continue
        g, n = re.search(r"""group\s*=\s*["']([^"']+)""", st), re.search(r"""\bname\s*=\s*["']([^"']+)""", st)
        if g and n:
            s.add_dep("maven", "%s:%s" % (g.group(1), n.group(1)), None, f.rel, i)


def h_csproj(s, f, data, text):
    for m in re.finditer(r"""<PackageReference\s+Include\s*=\s*["']([^"']+)["'](?:\s+Version\s*=\s*["']([^"']+))?""", text):
        s.add_dep("nuget", m.group(1), m.group(2), f.rel, text.count("\n", 0, m.start()) + 1)
    if re.search(r"<UseMaui>\s*true", text, re.I) or "Microsoft.Maui" in text:
        s.framework("dotnet-maui", f.rel, line_of(text, "Maui"))
    m = re.search(r"<ApplicationId>([^<]+)</ApplicationId>", text)
    if m:
        s.identifiers.setdefault("maui_application_id", m.group(1).strip())


def h_requirements(s, f, data, text):
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*([A-Za-z0-9_.\-]+)", line)
        if m and not line.lstrip().startswith(("#", "-")):
            s.add_dep("pypi", m.group(1), None, f.rel, i)


ANS = "{http://schemas.android.com/apk/res/android}"
TNS = "{http://schemas.android.com/tools}"


def h_android_manifest(s, f, data, text):
    s.platform["android_manifests"].append(f.rel)
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        s.parse_error(f.rel, e)
        for m in re.finditer(r"""<uses-permission[^>]*android:name\s*=\s*["']([^"']+)""", text):
            add_android_perm(s, f, text, m.group(1), removed=False, max_sdk=None, parsed=False)
        return
    pkg = root.get("package")
    if pkg:
        s.identifiers.setdefault("android_manifest_package", pkg)
    for el in root.iter():
        tag = el.tag
        if tag in ("uses-permission", "uses-permission-sdk-23"):
            name = el.get(ANS + "name") or ""
            add_android_perm(s, f, text, name, el.get(TNS + "node") == "remove", el.get(ANS + "maxSdkVersion"), True)
        elif tag == "application":
            ln = line_of(text, "<application")
            dbg = DEBUG_SUFFIX if DEBUG_VARIANT_RE.search(f.rel) else ""
            if (el.get(ANS + "usesCleartextTraffic") or "").lower() == "true":
                s.platform["cleartext"].append("%s:%s usesCleartextTraffic=true%s" % (f.rel, line_of(text, "usesCleartextTraffic"), dbg))
            if (el.get(ANS + "allowBackup") or "").lower() == "true":
                s.platform["allow_backup"].append("%s:%s" % (f.rel, line_of(text, "allowBackup")))
            if (el.get(ANS + "debuggable") or "").lower() == "true":
                s.platform["cleartext"].append("%s:%s debuggable=true%s" % (f.rel, ln, dbg))
        elif tag == "meta-data":
            name = el.get(ANS + "name") or ""
            s.platform["android_meta_data"].append({"name": name[:120], "path": f.rel, "line": line_of(text, name)})
        elif tag in ("activity", "activity-alias", "service", "receiver", "provider"):
            cname = el.get(ANS + "name") or "?"
            filters = el.findall("intent-filter")
            launcher = any(c.get(ANS + "name") == "android.intent.category.LAUNCHER" for flt in filters for c in flt.findall("category"))
            if launcher:
                s.entry_points.append("%s (%s launcher activity)" % (cname, f.rel))
            if (el.get(ANS + "exported") or "").lower() == "true" and not launcher and not el.get(ANS + "permission"):
                s.platform["exported_components"].append("%s %s (%s:%s)" % (tag, cname, f.rel, line_of(text, cname)))
            if tag == "service" and el.get(ANS + "foregroundServiceType"):
                s.platform["foreground_services"].append("%s=%s (%s)" % (cname, el.get(ANS + "foregroundServiceType"), f.rel))
            for flt in filters:
                verify = (flt.get(ANS + "autoVerify") or "").lower() == "true"
                for d in flt.findall("data"):
                    scheme, host = d.get(ANS + "scheme"), d.get(ANS + "host")
                    if not scheme and not host:
                        continue
                    entry = "%s://%s (%s:%s)" % (scheme or "*", host or "", f.rel, line_of(text, host or scheme))
                    s.platform["app_links" if verify and scheme in ("http", "https") else "deep_links"].append(entry)


def add_android_perm(s, f, text, name, removed, max_sdk, parsed):
    cat, policy = android_perm_info(name)
    line = line_of(text, '"%s"' % name) or line_of(text, name) or line_of(text, strip_android(name))
    s.android_perms.append({"name": name, "path": f.rel, "line": line, "debug_only": bool(DEBUG_VARIANT_RE.search(f.rel)),
                            "removed": removed, "max_sdk": max_sdk, "data_category": cat, "play_policy": policy,
                            "parsed": parsed})


def h_network_security(s, f, data, text):
    if re.search(r'cleartextTrafficPermitted\s*=\s*"true"', text):
        s.platform["cleartext"].append("%s:%s cleartextTrafficPermitted=true" % (f.rel, line_of(text, "cleartextTrafficPermitted")))


def load_plist(s, f, data):
    try:
        return plistlib.loads(data)
    except Exception as e:  # malformed plist or Xcode build-variable syntax
        s.parse_error(f.rel, e)
        return None


def purpose_status(value):
    if not isinstance(value, str) or not value.strip():
        return "empty"
    v = value.strip()
    if re.search(r"(?i)todo|lorem|tbd|fixme|description here|usage description", v) or len(v) < 12:
        return "weak"
    if v.startswith("$("):
        return "build_variable"
    return "ok"


def record_ios_keys(s, rel, text, plist, source):
    for key, val in plist.items():
        if not isinstance(key, str):
            continue
        if re.fullmatch(r"NS\w+UsageDescription|NFCReaderUsageDescription", key):
            s.ios_keys.append({"key": key, "path": rel, "line": line_of(text, key) if text else None,
                               "status": purpose_status(val), "data_category": IOS_KEYS.get(key), "source": source})
    if isinstance(plist.get("NSAppTransportSecurity"), dict):
        ats = plist["NSAppTransportSecurity"]
        if ats.get("NSAllowsArbitraryLoads") is True:
            s.platform["ats"].append("%s:%s NSAllowsArbitraryLoads=true" % (rel, line_of(text, "NSAllowsArbitraryLoads") if text else "?"))
        for dom, cfg in (ats.get("NSExceptionDomains") or {}).items():
            if isinstance(cfg, dict) and cfg.get("NSExceptionAllowsInsecureHTTPLoads"):
                s.platform["ats"].append("%s: insecure HTTP exception for %s" % (rel, dom))
    modes = plist.get("UIBackgroundModes")
    for mode in modes if isinstance(modes, list) else []:
        s.platform["background_modes"].append("%s (%s)" % (mode, rel))
    types = plist.get("CFBundleURLTypes")
    for t in types if isinstance(types, list) else []:
        for scheme in (t.get("CFBundleURLSchemes") or []) if isinstance(t, dict) else []:
            s.platform["url_schemes"].append("%s (%s)" % (scheme, rel))
    if "ITSAppUsesNonExemptEncryption" in plist:
        s.platform["export_compliance"].append("%s=%s (%s)" % ("ITSAppUsesNonExemptEncryption", plist["ITSAppUsesNonExemptEncryption"], rel))
    bid = plist.get("CFBundleIdentifier")
    if isinstance(bid, str) and not bid.startswith("$("):
        s.identifiers.setdefault("ios_bundle_id", bid)


def h_info_plist(s, f, data, text):
    s.platform["ios_plists"].append(f.rel)
    plist = load_plist(s, f, data)
    if isinstance(plist, dict):
        record_ios_keys(s, f.rel, text, plist, "Info.plist")
    elif text:
        for m in re.finditer(r"<key>(NS\w+UsageDescription)</key>", text):
            s.ios_keys.append({"key": m.group(1), "path": f.rel, "line": line_of(text, m.group(1)),
                               "status": "unparsed", "data_category": IOS_KEYS.get(m.group(1)), "source": "Info.plist"})


def h_entitlements(s, f, data, text):
    plist = load_plist(s, f, data)
    if not isinstance(plist, dict):
        return
    s.platform["entitlements"].append({"path": f.rel, "keys": sorted(k for k in plist if isinstance(k, str))[:30]})
    for dom in plist.get("com.apple.developer.associated-domains") or []:
        s.platform["associated_domains"].append("%s (%s)" % (dom, f.rel))


def h_privacy_manifest(s, f, data, text):
    plist = load_plist(s, f, data)
    if not isinstance(plist, dict):
        return
    s.platform["privacy_manifests"].append({
        "path": f.rel,
        "tracking": plist.get("NSPrivacyTracking"),
        "tracking_domains": (plist.get("NSPrivacyTrackingDomains") or [])[:20],
        "collected_types": [d.get("NSPrivacyCollectedDataType") for d in plist.get("NSPrivacyCollectedDataTypes") or [] if isinstance(d, dict)],
        "accessed_api_types": [d.get("NSPrivacyAccessedAPIType") for d in plist.get("NSPrivacyAccessedAPITypes") or [] if isinstance(d, dict)],
    })


def h_google_service(s, f, data, text):
    s.platform["firebase_config"].append(f.rel)


def h_app_json(s, f, data, text):
    cfg = json.loads(text)
    expo = cfg.get("expo") if isinstance(cfg, dict) else None
    if not isinstance(expo, dict):
        return
    s.framework("expo", f.rel, line_of(text, '"expo"'))
    ios, android = expo.get("ios") or {}, expo.get("android") or {}
    if ios.get("bundleIdentifier"):
        s.identifiers.setdefault("ios_bundle_id", ios["bundleIdentifier"])
    if android.get("package"):
        s.identifiers.setdefault("android_application_id", android["package"])
    if isinstance(ios.get("infoPlist"), dict):
        record_ios_keys(s, f.rel, text, ios["infoPlist"], "expo ios.infoPlist")
    for dom in ios.get("associatedDomains") or []:
        s.platform["associated_domains"].append("%s (%s)" % (dom, f.rel))
    for p in android.get("permissions") or []:
        name = p if "." in p else "android.permission." + p
        add_android_perm(s, f, text, name, False, None, True)
    for p in android.get("blockedPermissions") or []:
        name = p if "." in p else "android.permission." + p
        add_android_perm(s, f, text, name, True, None, True)
    plugins = []
    for p in expo.get("plugins") or []:
        pname = p[0] if isinstance(p, list) and p else p
        if isinstance(pname, str):
            plugins.append(pname)
            if pname == "expo-build-properties" and isinstance(p, list) and len(p) > 1 and isinstance(p[1], dict):
                tsdk = (p[1].get("android") or {}).get("targetSdkVersion")
                if tsdk:
                    s.platform["target_sdk"].append({"value": tsdk, "path": f.rel, "line": line_of(text, "targetSdkVersion")})
    s.expo = {"path": f.rel, "plugins": plugins[:40], "sdkVersion": expo.get("sdkVersion"),
              "android_permissions_declared": bool(android.get("permissions")),
              "platforms": expo.get("platforms") if isinstance(expo.get("platforms"), list) else None}
    for key in ("scheme",):
        if expo.get(key):
            s.platform["deep_links"].append("%s:// (%s)" % (expo[key], f.rel))


def h_app_config_js(s, f, data, text):
    s.framework("expo", f.rel)
    s.expo.setdefault("path", f.rel)
    s.expo.setdefault("note", "app.config.js/ts is code; values were not evaluated")


def h_capacitor(s, f, data, text):
    s.framework("capacitor", f.rel)
    m = re.search(r"""appId['"]?\s*:\s*['"]([^'"]+)""", text)
    if m:
        s.identifiers.setdefault("capacitor_app_id", m.group(1))


def h_cordova_config(s, f, data, text):
    if "<widget" in text and ("cordova" in text.lower() or "phonegap" in text.lower()):
        s.framework("cordova", f.rel)


def h_pbxproj(s, f, data, text):
    for m in re.finditer(r"PRODUCT_BUNDLE_IDENTIFIER\s*=\s*\"?([^\";]+)", text):
        if "$(" not in m.group(1):
            s.identifiers.setdefault("ios_bundle_id", m.group(1).strip())
            break
    s.framework("xcode-project", f.rel)


def h_env(s, f, data, text):
    keys = []
    for line in text.splitlines():
        m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s*=", line)
        if m:
            keys.append(m.group(1))
    s.env_files.append({"path": f.rel, "keys": keys[:60], "key_count": len(keys)})


def h_gitignore(s, f, data, text):
    if f.rel == ".gitignore" or f.rel.count("/") <= 1:
        s.gitignore_lines.extend(l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#"))


HANDLERS_BY_NAME = {
    "package.json": h_package_json, "package-lock.json": h_npm_lock, "npm-shrinkwrap.json": h_npm_lock,
    "yarn.lock": h_yarn_lock, "pnpm-lock.yaml": h_pnpm_lock, "pubspec.yaml": h_pubspec,
    "pubspec.lock": h_pubspec_lock, "Podfile": h_podfile, "Podfile.lock": h_podfile_lock,
    "Package.swift": h_package_swift, "Package.resolved": h_package_resolved, "Cartfile": h_cartfile,
    "build.gradle": h_gradle, "build.gradle.kts": h_gradle, "gradle.properties": h_properties,
    "libs.versions.toml": h_versions_toml, "AndroidManifest.xml": h_android_manifest,
    "network_security_config.xml": h_network_security, "PrivacyInfo.xcprivacy": h_privacy_manifest,
    "google-services.json": h_google_service, "GoogleService-Info.plist": h_google_service,
    "app.json": h_app_json, "app.config.js": h_app_config_js, "app.config.ts": h_app_config_js,
    "capacitor.config.json": h_capacitor, "capacitor.config.ts": h_capacitor, "capacitor.config.js": h_capacitor,
    "ionic.config.json": lambda s, f, d, t: s.framework("ionic", f.rel), "config.xml": h_cordova_config,
    "project.pbxproj": h_pbxproj, "requirements.txt": h_requirements, ".gitignore": h_gitignore,
}


def handler_for(f):
    if f.name in HANDLERS_BY_NAME:
        return HANDLERS_BY_NAME[f.name]
    if f.kind == "env":
        return h_env
    if f.ext == ".csproj":
        return h_csproj
    if f.name.endswith("Info.plist"):
        return h_info_plist
    if f.ext == ".entitlements":
        return h_entitlements
    if f.ext == ".xcprivacy":
        return h_privacy_manifest
    return None


# ---- line scanners ------------------------------------------------------------------------
def is_comment(line, ext):
    st = line.lstrip()
    return st.startswith(COMMENT_PREFIXES) or (ext in HASH_COMMENT_EXTS and st.startswith("#"))


def scan_secrets(s, f, text):
    kv_file = f.kind == "env" or f.ext in (".properties", ".xcconfig")
    for i, line in enumerate(text.splitlines(), 1):
        if len(line) > 5000:
            line = line[:5000]
        hit = False
        for rid, sev, rx in SECRET_RULES:
            m = rx.search(line)
            if not m:
                continue
            hit = True
            if rid == "jwt":
                role = jwt_role(m.group(0))
                if role == "service_role":
                    s.secret("supabase_service_role_key", "critical", f.rel, i, len(m.group(0)))
                elif role == "anon":
                    s.secret("supabase_anon_key", "info", f.rel, i, len(m.group(0)))
                else:
                    s.secret("jwt", sev, f.rel, i, len(m.group(0)))
            else:
                s.secret(rid, sev, f.rel, i, len(m.group(0)))
            break
        if hit:
            continue
        m = (GENERIC_KV.match(line) if kv_file else None) or GENERIC_QUOTED.search(line)
        if m:
            val = m.group(2)
            if not PLACEHOLDER_RE.search(val) and len(val) >= 12 and re.search(r"\d", val) \
                    and re.search(r"[A-Za-z]", val) and entropy(val) >= 3.0:
                s.secret("generic_secret", "medium", f.rel, i, len(val))
                continue
        for um in URL_RE.finditer(line):
            _safe, _host, flags = redact_url(um.group(0))
            if "credentials_in_url" in flags:
                try:
                    pw = urlsplit(um.group(0)).password or ""
                except ValueError:
                    pw = ""
                if len(pw) >= 6 and not PLACEHOLDER_RE.search(pw) and not pw.startswith(("%", "{", "<", ":")):
                    s.secret("url_credentials", "high", f.rel, i, len(um.group(0)))
            elif "secret_like_query" in flags:
                qv = [v for k, v in parse_qsl(urlsplit(um.group(0)).query) if k.lower() in SENSITIVE_QUERY]
                if any(len(v) >= 8 and not PLACEHOLDER_RE.search(v) for v in qv):
                    s.secret("url_query_secret", "medium", f.rel, i, len(um.group(0)))


def scan_lines(s, f, text, do_rules, do_urls):
    lines = text.splitlines()
    if lines and (len(text) > 50_000 and len(text) / max(len(lines), 1) > MINIFIED_LINE):
        s.coverage["minified_skipped"].append(f.rel)
        return
    rules = [r for r in RULES if r[6] is None or f.ext in r[6]] if do_rules else []
    for i, line in enumerate(lines, 1):
        if len(line) > 4000 or is_comment(line, f.ext):
            continue
        for rid, _kind, _cap, _cat, _conf, rx, _exts in rules:
            m = rx.search(line)
            if m and not (rid == "children" and CHILD_OPT_OUT.search(line)):
                s.signal(rid, f.rel, i, m.group(0), line)
        if do_urls and "://" in line:
            for um in URL_RE.finditer(line):
                safe, host, flags = redact_url(um.group(0))
                if not host or host in IGNORE_HOSTS or host.endswith(IGNORE_HOST_SUFFIX) or "." not in host \
                        and host != "localhost":
                    continue
                ep = s.endpoints.setdefault(host, {"host": host, "count": 0, "urls": [], "locations": [],
                                                   "flags": [], "test_only": True})
                ep["count"] += 1
                if not is_test_path(f.rel):
                    ep["test_only"] = False
                if safe not in ep["urls"] and len(ep["urls"]) < 5:
                    ep["urls"].append(safe)
                if len(ep["locations"]) < 5:
                    ep["locations"].append("%s:%d" % (f.rel, i))
                for fl in flags:
                    if fl not in ep["flags"]:
                        ep["flags"].append(fl)


# ---- analysis -----------------------------------------------------------------------------
def build_sdks(s):
    by_id = {}
    for d in s.deps:
        for sdk in s.catalog_match(d["ecosystem"], d["name"]):
            e = by_id.setdefault(sdk["id"], {
                "id": sdk["id"], "vendor": sdk.get("vendor"), "categories": sdk.get("category", []),
                "possible_data": sdk.get("possible_data", []), "capabilities": sdk.get("capabilities", []),
                "tracking": sdk.get("tracking", "no"), "docs": sdk.get("docs"), "matched": [],
                "direct": False, "dev_only": True, "evidence": []})
            if d["name"] not in e["matched"] and len(e["matched"]) < 6:
                e["matched"].append(d["name"])
            e["direct"] = e["direct"] or d["direct"]
            e["dev_only"] = e["dev_only"] and d["dev"]
            loc = "%s:%s" % (d["path"], d["line"]) if d["line"] else d["path"]
            if loc not in e["evidence"] and len(e["evidence"]) < 4:
                e["evidence"].append(loc)
    manifest_list = {n.lower() for n in s.catalog.get("apple_privacy_manifest_sdks", {}).get("names", [])}
    apple_sdks = set()
    for d in s.deps:
        if d["ecosystem"] in ("pod", "pub", "spm", "npm"):
            base = d["name"].split("/")[0].lower()
            tail = re.sub(r"\.git$", "", d["name"].lower().rstrip("/").rsplit("/", 1)[-1])
            if base in manifest_list or tail in manifest_list:
                apple_sdks.add(d["name"].split("/")[0])
    for f in s.frameworks:
        if f in ("flutter", "capacitor", "cordova"):
            apple_sdks.add(f.capitalize())
    unique = {n.lower(): n for n in sorted(apple_sdks)}
    return sorted(by_id.values(), key=lambda x: (x["dev_only"], not x["direct"], x["id"])), sorted(unique.values())


def platforms(s):
    p = set()
    fw = set(s.frameworks)
    if s.android_perms or s.platform["android_manifests"] or "android-gradle-app" in fw:
        p.add("android")
    if s.platform["ios_plists"] or "xcode-project" in fw or any(d["ecosystem"] in ("pod", "spm") for d in s.deps):
        p.add("ios")
    if fw & {"expo", "react-native", "flutter", "capacitor", "cordova", "dotnet-maui", "ionic", "nativescript"}:
        p.update(["android", "ios"])  # cross-platform frameworks target both unless configured otherwise
    if s.expo.get("platforms"):  # Expo's explicit platform list wins
        p &= set(s.expo["platforms"]) | ({"web"} if "web" in s.expo["platforms"] else set())
    if s.web_frameworks and not p:
        p.add("web")
    return sorted(p)


def framework_list(s):
    fw = dict(s.frameworks)
    native = []
    langs = s.languages
    if "android-gradle-app" in fw and not set(fw) & {"react-native", "expo", "flutter", "capacitor", "cordova", "dotnet-maui"}:
        native.append("native-android (%s)" % ("/".join(l for l in ("kotlin", "java") if langs.get(l)) or "no Kotlin/Java sources"))
    if "xcode-project" in fw and not set(fw) & {"react-native", "expo", "flutter", "capacitor", "cordova", "dotnet-maui"}:
        native.append("native-ios (%s)" % ("/".join(l for l in ("swift", "objective-c") if langs.get(l)) or "no Swift/ObjC sources"))
    fw.pop("android-gradle-app", None)
    fw.pop("xcode-project", None)
    out = [{"id": k, "evidence": v} for k, v in sorted(fw.items())]
    out += [{"id": n, "evidence": "project structure"} for n in native]
    if not out:  # web frameworks only matter when there is no mobile framework (Expo/RN apps often pull react-dom)
        out = [{"id": "web:" + k, "evidence": v} for k, v in sorted(s.web_frameworks.items())]
    return out


def used_capabilities(s, sdks):
    caps = {}
    for rid, _kind, cap, _cat, _conf, _rx, _exts in RULES:
        if cap:
            hits = [h for h in s.signals.get(rid, []) if not h["test_context"]]
            if hits:
                caps.setdefault(cap, []).append("%s:%d" % (hits[0]["path"], hits[0]["line"]))
    for sdk in sdks:
        if sdk["dev_only"]:
            continue
        for cap in sdk.get("capabilities", []):
            caps.setdefault(cap, []).append("sdk:" + sdk["id"])
    return caps


def live(s, rid):
    return [h for h in s.signals.get(rid, []) if not h["test_context"]]


def loc(h):
    return "%s:%s" % (h["path"], h["line"])


def build_data_leads(s, sdks):
    leads = {}

    def add(cat, kind, ref):
        if not cat:
            return
        e = leads.setdefault(cat, {"category": cat, "label": DATA_CATEGORIES[cat][0], "apple": DATA_CATEGORIES[cat][1],
                                   "play": DATA_CATEGORIES[cat][2], "evidence": []})
        item = {"type": kind, "ref": ref}
        if item not in e["evidence"] and len(e["evidence"]) < 8:
            e["evidence"].append(item)

    for p in s.android_perms:
        if not p["removed"] and not p["debug_only"]:
            add(p["data_category"], "permission_declared", "%s:%s %s" % (p["path"], p["line"], strip_android(p["name"])))
    for k in s.ios_keys:
        add(k["data_category"], "purpose_string_declared", "%s:%s %s" % (k["path"], k["line"], k["key"]))
    for rid, kind, _cap, cat, _conf, _rx, _exts in RULES:
        if kind in ("sensitive_api", "data_collection"):
            for h in live(s, rid)[:3]:
                add(cat, "code_" + kind, "%s %s" % (loc(h), rid))
    for sdk in sdks:
        if sdk["dev_only"]:
            continue
        for cat in sdk["possible_data"]:
            if cat in DATA_CATEGORIES:
                add(cat, "sdk_may_collect", sdk["id"])
    order = {"code_sensitive_api": 0, "code_data_collection": 0, "permission_declared": 1, "purpose_string_declared": 1, "sdk_may_collect": 2}
    for e in leads.values():
        e["strongest"] = min((order[x["type"]] for x in e["evidence"]), default=2)
        e["strongest"] = ["code", "declaration", "sdk_documentation"][e["strongest"]]
    return sorted(leads.values(), key=lambda e: e["category"])


def check(checks, cid, status, summary, evidence=(), ref=None):
    checks.append({"id": cid, "status": status, "summary": summary, "evidence": list(evidence)[:6], "ref": ref})


def build_checks(s, sdks, apple_sdks, plats, caps):
    c = []
    A, G = "references/apple-app-store.md", "references/google-play.md"
    live_secrets = [x for x in s.secrets if not x["test_context"]]
    serious = [x for x in live_secrets if x["severity"] in ("critical", "high", "medium")]
    if serious:
        check(c, "SECRETS_IN_SOURCE", "attention", "%d credential-like value(s) found in source/config (values not shown)" % len(serious),
              ["%s %s:%s" % (x["rule"], x["path"], x["line"]) for x in serious], "references/security-and-scanning.md")
    unignored = [e["path"] for e in s.env_files if e["key_count"] and not env_ignored(s, e["path"])
                 and not re.search(r"(?i)example|sample|template|defaults", e["path"])]
    if unignored:
        check(c, "ENV_FILE_NOT_GITIGNORED", "attention", ".env file(s) not matched by a root .gitignore rule (heuristic)", unignored)

    tracking_sdks = [x["id"] for x in sdks if x["tracking"] in ("yes", "possible") and not x["dev_only"]]
    sdk_ids = {x["id"] for x in sdks if not x["dev_only"]}
    cats = {cat for x in sdks if not x["dev_only"] for cat in x["categories"]}

    if "ios" in plats:
        keys = {k["key"]: k for k in s.ios_keys}
        expo = "expo" in s.frameworks
        has_plist = bool(s.platform["ios_plists"])
        for cap, ev in sorted(caps.items()):
            need = CAP_IOS_KEYS.get(cap)
            if need and not any(k in keys for k in need):
                status = "attention" if has_plist and not expo else "info"
                why = " (Expo config plugins may inject a default string; review its wording)" if expo else \
                    "" if has_plist else " (no Info.plist in the repository; add it when the iOS project is generated)"
                check(c, "IOS_PURPOSE_STRING_MISSING", status, "%s used but no %s found%s" % (cap, " / ".join(need), why), ev, A + "#purpose-strings")
        for k in s.ios_keys:
            if k["status"] in ("empty", "weak"):
                check(c, "IOS_PURPOSE_STRING_WEAK", "attention", "%s is %s; Apple requires a clear, specific purpose" % (k["key"], k["status"]),
                      ["%s:%s" % (k["path"], k["line"])], A + "#purpose-strings")
        if tracking_sdks or live(s, "advertising_id"):
            att_key = "NSUserTrackingUsageDescription" in keys
            att_call = bool(live(s, "att_request")) or "att" in sdk_ids
            definite = [x["id"] for x in sdks if x["tracking"] == "yes" and not x["dev_only"]] or live(s, "advertising_id")
            if not (att_key and att_call):
                check(c, "IOS_ATT_REVIEW", "attention" if definite else "info",
                      "SDKs/APIs that can track are present; ATT purpose string %s, ATT request %s. Needed only if the app tracks as Apple defines it"
                      % ("found" if att_key else "missing", "found" if att_call else "not found"),
                      tracking_sdks[:5] + [loc(h) for h in live(s, "advertising_id")[:2]], A + "#tracking-and-att")
        manifests = [m for m in s.platform["privacy_manifests"] if not is_test_path(m["path"])]
        rr_used = {RR_TYPES[r]: loc(live(s, r)[0]) for r in RR_TYPES if live(s, r)}
        declared = {t for m in manifests for t in m["accessed_api_types"] if t}
        if not manifests:
            check(c, "IOS_PRIVACY_MANIFEST_MISSING", "attention" if rr_used else "info",
                  "No app-level PrivacyInfo.xcprivacy found%s" % ("; native code uses required-reason APIs" if rr_used else ""),
                  ["%s %s" % (k, v) for k, v in rr_used.items()], A + "#privacy-manifest")
        else:
            missing = {k: v for k, v in rr_used.items() if k not in declared}
            if missing:
                check(c, "IOS_REQUIRED_REASON_UNDECLARED", "attention", "Required-reason API categories used but not declared in PrivacyInfo.xcprivacy",
                      ["%s %s" % (k, v) for k, v in missing.items()], A + "#privacy-manifest")
            if tracking_sdks and not any(m["tracking"] for m in manifests):
                check(c, "IOS_PRIVACY_MANIFEST_TRACKING", "info", "Tracking-capable SDKs present but NSPrivacyTracking is not true; confirm whether the app tracks",
                      tracking_sdks[:5], A + "#privacy-manifest")
        if apple_sdks:
            check(c, "IOS_SDKS_NEED_MANIFEST_SIGNATURE", "info", "Dependencies on Apple's list of SDKs that require a privacy manifest and signature; use versions that include them",
                  apple_sdks[:12], A + "#privacy-manifest")
        if s.platform["ats"]:
            check(c, "IOS_ATS_EXCEPTION", "attention", "App Transport Security exceptions allow insecure HTTP", s.platform["ats"], A + "#transport-security")
        if live(s, "social_login") and not live(s, "apple_login") and "apple-auth" not in sdk_ids:
            check(c, "IOS_LOGIN_SERVICES_4_8", "attention", "Third-party social login found without Sign in with Apple; guideline 4.8 requires an equivalent privacy-focused login option unless an exception applies",
                  [loc(h) for h in live(s, "social_login")[:3]], A + "#login-services")
        if live(s, "payments_external"):
            check(c, "IOS_PAYMENTS_REVIEW", "info", "External payment code found; digital goods/features must use in-app purchase (guideline 3.1.1); physical goods/services may not",
                  [loc(h) for h in live(s, "payments_external")[:3]], A + "#payments")
        if s.platform["ios_plists"] and not s.platform["export_compliance"]:
            check(c, "IOS_EXPORT_COMPLIANCE", "info", "ITSAppUsesNonExemptEncryption not set; App Store Connect will ask about encryption on each build", [], A)
        if s.platform["associated_domains"]:
            check(c, "IOS_ASSOCIATED_DOMAINS", "info", "Associated domains declared; each domain must serve a valid apple-app-site-association file", s.platform["associated_domains"], A)

    if "android" in plats:
        restricted = [p for p in s.android_perms if p["play_policy"] and not p["removed"] and not p["debug_only"]]
        if restricted:
            check(c, "PLAY_SENSITIVE_PERMISSIONS", "attention", "Permissions with Play policy declarations or restrictions",
                  ["%s (%s:%s): %s" % (strip_android(p["name"]), p["path"], p["line"], p["play_policy"]) for p in restricted], G + "#sensitive-permissions")
        tsdk = [t for t in s.platform["target_sdk"] if isinstance(t["value"], int)]
        if not tsdk:  # RN/Expo default comes from the installed react-native's version catalog
            rn_toml = "node_modules/react-native/gradle/libs.versions.toml"
            try:
                text = (Path(s.root) / rn_toml).read_text(encoding="utf-8", errors="replace")
                m = re.search(r'^targetSdk\s*=\s*"(\d+)"', text, re.M)
                if m:
                    tsdk = [{"value": int(m.group(1)), "path": rn_toml + " (framework default)",
                             "line": text.count("\n", 0, m.start()) + 1}]
            except OSError:
                pass
        req = s.catalog.get("meta", {}).get("play_target_sdk", {})
        if tsdk and req.get("value") and min(t["value"] for t in tsdk) < req["value"]:
            check(c, "PLAY_TARGET_SDK_LOW", "attention", "targetSdk %s is below the Play requirement recorded on %s (API %s from %s); verify current rule"
                  % (min(t["value"] for t in tsdk), req.get("checked"), req["value"], req.get("effective")),
                  ["%s:%s" % (t["path"], t["line"]) for t in tsdk], G + "#target-api-level")
        elif not tsdk:
            fw_ver = ["%s %s" % (d["name"], d["version"]) for d in s.deps
                      if d["direct"] and d["name"] in ("expo", "react-native", "flutter", "@capacitor/android") and d["version"]]
            check(c, "PLAY_TARGET_SDK_UNKNOWN", "info", "targetSdk not resolvable statically (set by framework/tooling defaults); confirm the framework version targets API %s or later"
                  % req.get("value", "?"), fw_ver[:3], G + "#target-api-level")
        ads = cats & {"advertising", "attribution"} or live(s, "advertising_id")
        if ads:
            adid = [p for p in s.android_perms if strip_android(p["name"]) == "AD_ID"]
            check(c, "PLAY_ADVERTISING_ID", "info", "Ads/attribution code present; answer the Advertising ID declaration in Play Console (AD_ID permission %s)"
                  % ("removed" if adid and adid[0]["removed"] else "declared" if adid else "not declared in source manifests; SDKs may merge it"),
                  [p["path"] for p in adid][:2], G + "#advertising-id")
        if s.platform["cleartext"]:
            release = [x for x in s.platform["cleartext"] if not x.endswith(DEBUG_SUFFIX)]
            check(c, "ANDROID_CLEARTEXT_OR_DEBUG", "attention" if release else "info",
                  "Cleartext traffic or debuggable flag enabled" + ("" if release else " in debug source sets only (normal for React Native dev builds)"),
                  release or s.platform["cleartext"], G)
        if s.platform["app_links"]:
            check(c, "ANDROID_APP_LINKS", "info", "Verified App Links declared; each host must serve /.well-known/assetlinks.json", s.platform["app_links"], G)
        if s.platform["exported_components"]:
            check(c, "ANDROID_EXPORTED_COMPONENTS", "info", "Exported components without a permission; confirm they are meant to be public", s.platform["exported_components"])
        if s.platform["foreground_services"]:
            check(c, "PLAY_FOREGROUND_SERVICE", "attention", "Foreground service types need a Play Console declaration", s.platform["foreground_services"], G + "#sensitive-permissions")

    account = live(s, "auth_signup") + live(s, "social_login") + live(s, "phone_auth")
    if account or cats & {"auth"}:
        ev = [loc(h) for h in account[:3]] + [x["id"] for x in sdks if "auth" in x["categories"]][:3]
        if not live(s, "account_deletion"):
            check(c, "ACCOUNT_DELETION_NOT_FOUND", "attention", "Account creation/auth found but no account-deletion code path; Apple 5.1.1(v) and Google Play require in-app deletion (Play also a web link)",
                  ev, A + "#account-deletion")
        check(c, "REVIEWER_ACCESS", "info", "Login detected: provide a demo account or review instructions (Apple 2.1, Play App access)", ev[:2], A + "#review-access")
    if not live(s, "privacy_policy_link") and not any("privacy" in u.lower() for e in s.endpoints.values() for u in e["urls"]):
        check(c, "PRIVACY_POLICY_LINK_NOT_FOUND", "attention", "No privacy policy link/screen found in code; both stores require a privacy policy URL and Apple requires an in-app link",
              [], A + "#privacy-policy")
    http_eps = [e["host"] for e in s.endpoints.values() if "cleartext" in e["flags"] and not e["test_only"]
                and not re.fullmatch(r"[\d.]+|localhost", e["host"])]
    if http_eps:
        check(c, "CLEARTEXT_ENDPOINTS", "attention", "http:// or ws:// endpoints (unencrypted in transit; affects Data safety 'encrypted in transit')", http_eps[:8])
    for rid, cid, msg in (("pii_logging", "PII_IN_LOGS", "Personal data or credentials may be written to logs"),
                          ("insecure_storage", "TOKENS_IN_PLAIN_STORAGE", "Tokens/credentials may be stored in unencrypted storage; prefer Keychain/Keystore/SecureStore"),
                          ("webview_bridge", "WEBVIEW_BRIDGE", "WebView JavaScript bridge/settings that widen attack surface")):
        if live(s, rid):
            check(c, cid, "attention" if rid != "webview_bridge" else "info", msg, [loc(h) for h in live(s, rid)[:5]], "references/security-and-scanning.md")
    replay = [x["id"] for x in sdks if "session_replay" in x["categories"] and not x["dev_only"]]
    if replay:
        check(c, "SESSION_REPLAY_SDK", "attention", "Session replay / screen recording SDKs can capture user content; mask sensitive views and disclose", replay)
    ai = [x["id"] for x in sdks if "ai" in x["categories"] and not x["dev_only"]] + \
         [e["host"] for e in s.endpoints.values() if (s.vendor_for_host(e["host"]) or {}).get("category", [None])[0] == "ai"]
    if ai or live(s, "ai_call"):
        check(c, "THIRD_PARTY_AI", "attention", "Data may be sent to third-party AI providers; Apple 5.1.2(i) requires clear disclosure and explicit permission before sharing personal data with third-party AI",
              sorted(set(ai))[:5] + [loc(h) for h in live(s, "ai_call")[:2]], A + "#third-party-ai")
    if live(s, "children"):
        check(c, "CHILDREN_SIGNALS", "attention", "Child-directed signals found; Kids Category/Families policy and children's privacy laws may apply%s"
              % ("; third-party analytics/ads SDKs present" if cats & {"analytics", "advertising"} else ""),
              [loc(h) for h in live(s, "children")[:4]], "references/jurisdictions.md#children")
    elif live(s, "children_opt_out"):
        check(c, "ADS_NOT_CHILD_DIRECTED", "info", "Ad requests explicitly opt out of child-directed treatment; the store age rating, target audience and privacy policy must agree that the app is not for children",
              [loc(h) for h in live(s, "children_opt_out")[:3]], "references/jurisdictions.md#children")
    cmp = [x["id"] for x in sdks if "consent" in x["categories"] and x["id"] != "att"]
    if (tracking_sdks or cats & {"advertising"}) and not live(s, "consent_tooling") and not cmp:
        check(c, "CONSENT_MECHANISM_NOT_FOUND", "info", "Tracking/ads-capable SDKs without consent tooling in code; whether consent is required depends on processing and jurisdiction",
              tracking_sdks[:5], "references/consent.md")
    order = {"attention": 0, "info": 1}
    return sorted(c, key=lambda x: order.get(x["status"], 2))


def env_ignored(s, rel):
    name = Path(rel).name
    return any(fnmatch.fnmatch(name, p.lstrip("/")) or fnmatch.fnmatch(rel, p.lstrip("/"))
               for p in s.gitignore_lines if not p.startswith("!"))


# ---- orchestration ------------------------------------------------------------------------
def load_catalog():
    try:
        return json.loads((HERE / "sdk_catalog.json").read_text(encoding="utf-8")), None
    except Exception as e:
        return {"sdks": []}, "sdk_catalog.json unavailable (%s); SDK identification disabled" % type(e).__name__


LANG = {".kt": "kotlin", ".java": "java", ".swift": "swift", ".m": "objective-c", ".mm": "objective-c",
        ".dart": "dart", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript", ".jsx": "javascript",
        ".cs": "csharp", ".py": "python", ".vue": "vue", ".svelte": "svelte", ".go": "go", ".rb": "ruby", ".php": "php"}


def fingerprint(root, max_files):
    h = hashlib.sha256(VERSION.encode())
    cov = {"files_seen": 0, "files_scanned": 0, "skipped_dirs": [], "skipped_large": [], "symlinks_skipped": [],
           "skipped_generated": 0, "unreadable": [], "file_limit_hit": False}
    for f in walk(root, cov, max_files):
        try:
            st = os.stat(f.path)
        except OSError:
            continue
        h.update(("%s|%d|%d\n" % (f.rel, st.st_size, st.st_mtime_ns)).encode())
    for own in (HERE / "sdk_catalog.json", Path(__file__)):  # scanner or catalog changes invalidate the cache
        try:
            h.update(own.read_bytes())
        except OSError:
            pass
    return h.hexdigest()[:20]


def run_scan(root, max_files=MAX_FILES, snippets=False):
    catalog, cat_err = load_catalog()
    s = Scan(root, catalog, snippets)
    if cat_err:
        s.coverage["parse_errors"].append({"path": "sdk_catalog.json", "error": cat_err})
    for f in walk(str(root), s.coverage, max_files):
        try:
            with open(f.path, "rb") as fh:
                data = fh.read()
        except OSError:
            s.coverage["unreadable"].append(f.rel)
            continue
        if f.ext in LANG:
            s.languages[LANG[f.ext]] = s.languages.get(LANG[f.ext], 0) + 1
        text = decode(data, f.rel, s.coverage)
        handler = handler_for(f)
        if handler:
            try:
                handler(s, f, data, text if text is not None else "")
            except Exception as e:  # malformed input must never abort the scan
                s.parse_error(f.rel, e)
        if text is None:
            if not handler:
                s.coverage["skipped_binary"] += 1
            continue
        if f.kind != "lock" and f.name != ".gitignore":
            scan_secrets(s, f, text)
        if f.kind in ("source", "config", "env", "manifest") and f.name != ".gitignore":
            scan_lines(s, f, text, do_rules=f.kind == "source",
                       do_urls=f.name not in NO_URL_SCAN and not NO_URL_SCAN_RE.search(f.rel))
    return s


def assemble(s, root):
    # gitignored android/ or ios/ folders are generated (e.g. by `expo prebuild`) and may be stale vs the app config
    s.coverage["generated_native_dirs"] = [
        d for d in ("android", "ios") if (Path(root) / d).is_dir()
        and any(fnmatch.fnmatch(d, p.strip("/")) for p in s.gitignore_lines if not p.startswith("!"))]
    sdks, apple_sdks = build_sdks(s)
    plats = platforms(s)
    caps = used_capabilities(s, sdks)
    for ep in s.endpoints.values():
        v = s.vendor_for_host(ep["host"])
        ep["vendor"] = v.get("vendor") if v else None
        ep["vendor_category"] = (v.get("category") or [None])[0] if v else None
    endpoints = sorted(s.endpoints.values(), key=lambda e: (e["test_only"], e["vendor"] is None, -e["count"], e["host"]))
    signals = {rid: {"count": s.signal_counts.get(rid, 0), "kind": next(r[1] for r in RULES if r[0] == rid),
                     "hits": hits} for rid, hits in sorted(s.signals.items())}
    total_deps = len(s.deps)
    return {
        "tool": "ship-to-store", "scanner_version": VERSION, "generated_at": now_iso(),
        "root_name": Path(root).name,
        "interpretation": "Leads for review, not findings. Matches show code or configuration, not runtime behaviour. "
                          "Absence of a match is not evidence of absence. Secret values are never recorded.",
        "app": {"frameworks": framework_list(s), "platforms": plats,
                "languages": dict(sorted(s.languages.items(), key=lambda kv: -kv[1])),
                "identifiers": s.identifiers, "entry_points": s.entry_points[:10], "expo": s.expo or None},
        "dependencies": {"count": total_deps, "items": s.deps},
        "sdks": sdks, "apple_privacy_manifest_sdks": apple_sdks,
        "permissions": {"android": s.android_perms, "ios": s.ios_keys},
        "platform_config": s.platform, "capabilities_used": caps,
        "signals": signals, "endpoints": endpoints, "secrets": s.secrets, "env_files": s.env_files,
        "data_leads": build_data_leads(s, sdks),
        "checks": build_checks(s, sdks, apple_sdks, plats, caps),
        "coverage": s.coverage,
    }


def summarize(full, detail_rel, cached=False):
    cov = full["coverage"]
    live_secrets = [x for x in full["secrets"] if not x["test_context"]]
    by_sev = {}
    for x in live_secrets:
        by_sev[x["severity"]] = by_sev.get(x["severity"], 0) + 1
    perms = full["permissions"]
    eps = [e for e in full["endpoints"] if not e["test_only"]]
    return {
        "scanner": full["scanner_version"], "cached": cached, "generated_at": full["generated_at"],
        "detail_file": detail_rel,
        "how_to_drill_down": "scan.py --root <root> --show <section> [--grep TEXT] [--limit N]; sections: " + ", ".join(SECTIONS),
        "app": {"frameworks": [f["id"] for f in full["app"]["frameworks"]], "platforms": full["app"]["platforms"],
                "identifiers": full["app"]["identifiers"], "languages": dict(list(full["app"]["languages"].items())[:6])},
        "sdks": ["%s [%s]%s%s" % (x["id"], ",".join(x["categories"]), "" if x["direct"] else " transitive",
                                  " dev-only" if x["dev_only"] else "") for x in full["sdks"][:40]],
        "permissions": {
            "android": sorted({strip_android(p["name"]) + (" (removed)" if p["removed"] else " (debug)" if p["debug_only"] else "")
                               for p in perms["android"]})[:40],
            "ios": sorted({"%s%s" % (k["key"], "" if k["status"] == "ok" else " [%s]" % k["status"]) for k in perms["ios"]})[:30]},
        "endpoints": ["%s%s x%d%s" % (e["host"], " (%s)" % e["vendor"] if e["vendor"] else "", e["count"],
                                      " [%s]" % ",".join(e["flags"]) if e["flags"] else "") for e in eps[:25]],
        "endpoint_hosts_total": len(eps),
        "secrets": {"by_severity": by_sev,
                    "items": ["%s %s %s:%s" % (x["severity"], x["rule"], x["path"], x["line"]) for x in live_secrets[:10]]},
        "env_files": [{"path": e["path"], "key_count": e["key_count"]} for e in full["env_files"][:5]],
        "data_leads": {d["category"]: d["strongest"] for d in full["data_leads"]},
        "signals": {k: v["count"] for k, v in full["signals"].items() if v["count"]},
        "checks": [{"id": c["id"], "status": c["status"], "summary": c["summary"], "evidence": c["evidence"][:3]}
                   for c in full["checks"]],
        "coverage": {"files_scanned": cov["files_scanned"], "files_seen": cov["files_seen"],
                     "skipped_dirs": len(cov["skipped_dirs"]), "skipped_large": cov["skipped_large"][:5],
                     "skipped_binary": cov["skipped_binary"], "symlinks_skipped": len(cov["symlinks_skipped"]),
                     "minified_skipped": len(cov["minified_skipped"]), "parse_errors": cov["parse_errors"][:5],
                     "file_limit_hit": cov["file_limit_hit"], "truncated_rules": cov["truncated_rules"],
                     "test_context_hits_excluded": cov["test_context_hits"],
                     "generated_native_dirs": cov.get("generated_native_dirs", [])},
    }


def show(full, section, grep, limit):
    data = full.get(section)
    if section == "dependencies":
        data = data["items"]
    if isinstance(data, dict) and section == "signals":
        items = [dict(h, rule=rid) for rid, v in data.items() for h in v["hits"]]
    elif isinstance(data, list):
        items = data
    else:
        return data
    if grep:
        g = grep.lower()
        items = [i for i in items if g in json.dumps(i).lower()]
    return {"section": section, "total": len(items), "shown": min(len(items), limit), "items": items[:limit]}


def emit(obj, pretty=False):
    out = json.dumps(obj, indent=1 if pretty else None, separators=None if pretty else (",", ":"), ensure_ascii=True)
    sys.stdout.write(out + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Ship-to-Store local repository scanner (read-only, offline).")
    ap.add_argument("--root", default=".", help="app repository root")
    ap.add_argument("--out-dir", help="where to write scan.json (default: a per-app folder in the OS temp dir, so the app repo stays untouched)")
    ap.add_argument("--reuse", action="store_true", help="print cached summary if no scanned file changed")
    ap.add_argument("--show", choices=SECTIONS, help="print one section of the last scan.json")
    ap.add_argument("--grep", help="filter --show items by substring")
    ap.add_argument("--limit", type=int, default=50, help="max items for --show (default 50)")
    ap.add_argument("--snippets", action="store_true", help="include redacted 160-char line snippets in scan.json")
    ap.add_argument("--max-files", type=int, default=MAX_FILES)
    ap.add_argument("--no-write", action="store_true", help="do not write scan.json; print full JSON instead of the summary")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        sys.stderr.write("Not a directory: %s\n" % args.root)
        return 2
    out_dir = Path(args.out_dir).resolve() if args.out_dir else \
        Path(tempfile.gettempdir()) / "ship-to-store" / ("%s-%s" % (root.name, hashlib.sha256(str(root).encode()).hexdigest()[:12]))
    detail = out_dir / "scan.json"
    try:
        detail_rel = detail.relative_to(root).as_posix()
    except ValueError:
        detail_rel = detail.as_posix()

    if args.show:
        if not detail.exists():
            sys.stderr.write("No scan.json yet; run a scan first.\n")
            return 2
        emit(show(json.loads(detail.read_text(encoding="utf-8")), args.show, args.grep, max(args.limit, 1)), pretty=True)
        return 0

    fp = fingerprint(str(root), args.max_files)
    if args.reuse and detail.exists():
        try:
            cached = json.loads(detail.read_text(encoding="utf-8"))
            if cached.get("fingerprint") == fp:
                emit(summarize(cached, detail_rel, cached=True))
                return 0
        except (ValueError, OSError, KeyError, TypeError, AttributeError):
            pass  # unreadable or old-format cache: rescan

    full = assemble(run_scan(root, args.max_files, args.snippets), root)
    full["fingerprint"] = fp
    if args.no_write:
        emit(full, pretty=True)
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    detail.write_text(json.dumps(full, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    emit(summarize(full, detail_rel))
    return 0


if __name__ == "__main__":
    sys.exit(main())
