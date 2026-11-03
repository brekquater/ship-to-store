# Contributing

Ship-to-Store is a local Claude Code Skill: one stdlib-only Python scanner, a JSON SDK catalog, and Markdown references. Please keep it that way. No runtime dependencies, no network calls in scripts, no hosted services.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

Python 3.9+ on Linux, macOS or Windows.

## Add or fix an SDK

Edit `skills/ship-to-store/scripts/sdk_catalog.json`:

```json
{"id": "vendor-sdk", "vendor": "Vendor", "category": ["analytics"], "tracking": "no|possible|yes",
 "match": {"npm": ["pkg", "@scope/*"], "pub": [], "pod": [], "spm": ["repo-name"], "maven": ["group:artifact", "group:*"], "nuget": [], "pypi": []},
 "domains": ["api.vendor.com"], "possible_data": ["device_id", "app_interactions"], "capabilities": [],
 "docs": "https://vendor.com/privacy"}
```

- `possible_data` uses the category keys in `DATA_CATEGORIES` (`scan.py`) and must come from the vendor's own documentation.
- `tracking: "yes"` only for SDKs whose main purpose is ads or attribution.
- `capabilities` (`camera`, `location`, `photos`, …) only for SDKs that access a protected resource.
- Add the package to a fixture and assert it in `tests/test_scan.py`.

## Update a platform or legal rule

Rules change. When you update a reference file, link the **official** source (Apple, Google, legislation, regulator) and update its "checked" date. Do not cite blogs as authority.

## Release

1. Bump `version` in `.claude-plugin/plugin.json`, and add a matching `## <version>` heading to `CHANGELOG.md` (a test checks they agree). Without a version bump, `claude plugin update` keeps users on the old copy.
2. Run `claude plugin validate --strict .` and the tests.
3. Merge to `master`. Plugin users get the release with `claude plugin update ship-to-store@brekquater`. A directory listing picks up the new version from GitHub.

## Test data

Fixtures must be synthetic. Never commit real credentials, personal data, or secret-shaped strings. Tests build fake secrets at runtime by string concatenation.

## Security issues

Do not open a public issue for a vulnerability such as a redaction bypass. Contact the maintainers privately via the repository's security advisory feature.
