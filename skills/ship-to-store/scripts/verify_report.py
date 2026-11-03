#!/usr/bin/env python3
"""Check generated Ship-to-Store documents before they are shared.

  verify_report.py --dir <root>/ship-to-store-report

Errors (exit 1): secret-like values in any report file; data-inventory.json that
is not valid JSON or misses required fields/enums.
Warnings: wording that reads as a compliance or approval guarantee.
Info: open placeholders per file (documents with placeholders are incomplete).
Local and read-only; prints JSON.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan import GENERIC_QUOTED, PLACEHOLDER_RE, SECRET_RULES, URL_RE, redact_url  # noqa: E402

EVIDENCE = {"observed", "static_inference", "vendor_documentation", "user_confirmed", "unknown"}
CONFIDENCE = {"high", "medium", "low"}
SEVERITY = {"critical", "high", "medium", "low", "info"}
TRI = {"yes", "no", "unknown"}
ITEM_VERIFY = {"unverified", "developer_confirmed", "runtime_verified"}
FINDING_VERIFY = {"unverified", "developer_confirmed", "fixed_pending_rescan", "resolved"}
ITEM_FIELDS = ("id", "category", "description", "sources", "purpose", "recipients", "optional",
               "linked_to_user", "used_for_tracking", "retention", "evidence_type", "confidence", "verification")
FINDING_FIELDS = ("id", "category", "title", "description", "severity", "file", "line", "evidence",
                  "evidence_type", "confidence", "impact", "remediation", "verification_status")
CLAIMS = re.compile(r"(?i)(fully|100%|completely)\s+compliant|guarantee[sd]?\s+(compliance|approval|that)|"
                    r"(is|are|will be)\s+(gdpr|ccpa|dpdp|coppa|hipaa)[- ]compliant|lawsuit[- ]proof|"
                    r"approval (is )?guaranteed|will (be|get) approved|certified (compliant|safe)")
NEGATION = re.compile(r"(?i)\b(not|never|no|cannot|can't|does not|doesn't|without)\b")
PLACEHOLDER = re.compile(r"\[TO CONFIRM[^\]]*\]")


def check_secrets(path, text, errors):
    for i, line in enumerate(text.splitlines(), 1):
        for rid, _sev, rx in SECRET_RULES:
            if rx.search(line) and rid != "google_api_key":
                errors.append({"file": path, "line": i, "problem": "secret-like value (%s)" % rid})
        m = GENERIC_QUOTED.search(line)
        if m and not PLACEHOLDER_RE.search(m.group(2)) and re.search(r"\d", m.group(2)) and len(m.group(2)) >= 12:
            errors.append({"file": path, "line": i, "problem": "credential-like assignment"})
        for um in URL_RE.finditer(line):
            if {"credentials_in_url", "secret_like_query"} & set(redact_url(um.group(0))[2]):
                errors.append({"file": path, "line": i, "problem": "URL with credentials or secret-like query"})


def check_claims(path, text, warnings):
    for i, line in enumerate(text.splitlines(), 1):
        for m in CLAIMS.finditer(line):
            if not NEGATION.search(line[:m.start()]):
                warnings.append({"file": path, "line": i, "problem": "guarantee-like wording: %r" % m.group(0)})


def check_enum(errors, where, obj, field, allowed):
    if obj.get(field) not in allowed:
        errors.append({"file": where, "problem": "%s=%r not in %s" % (field, obj.get(field), sorted(allowed))})


def check_inventory(path, text, errors):
    try:
        inv = json.loads(text)
    except ValueError as e:
        errors.append({"file": path, "problem": "invalid JSON: %s" % e})
        return
    if not isinstance(inv, dict):
        errors.append({"file": path, "problem": "top level must be an object"})
        return
    for key in ("schema", "generated_at", "app", "data_items", "findings", "unresolved_questions"):
        if key not in inv:
            errors.append({"file": path, "problem": "missing top-level key: %s" % key})
    for kind, fields in (("data_items", ITEM_FIELDS), ("findings", FINDING_FIELDS)):
        items = inv.get(kind)
        if not isinstance(items, list):
            continue
        for n, item in enumerate(items):
            where = "%s %s[%d]" % (path, kind, n)
            if not isinstance(item, dict):
                errors.append({"file": where, "problem": "not an object"})
                continue
            missing = [f for f in fields if f not in item]
            if missing:
                errors.append({"file": where, "problem": "missing fields: %s" % ", ".join(missing)})
            check_enum(errors, where, item, "evidence_type", EVIDENCE)
            check_enum(errors, where, item, "confidence", CONFIDENCE)
            if kind == "data_items":
                for f in ("optional", "linked_to_user", "used_for_tracking"):
                    check_enum(errors, where, item, f, TRI)
                check_enum(errors, where, item, "verification", ITEM_VERIFY)
            else:
                check_enum(errors, where, item, "severity", SEVERITY)
                check_enum(errors, where, item, "verification_status", FINDING_VERIFY)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", required=True, help="report directory")
    args = ap.parse_args(argv)
    root = Path(args.dir)
    if not root.is_dir():
        sys.stderr.write("Not a directory: %s\n" % args.dir)
        return 2
    errors, warnings, placeholders = [], [], {}
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.is_symlink() or p.suffix.lower() not in (".md", ".json", ".txt", ".csv"):
            continue
        rel = p.relative_to(root).as_posix()
        text = p.read_text(encoding="utf-8", errors="replace")
        check_secrets(rel, text, errors)
        if p.suffix.lower() == ".md":
            check_claims(rel, text, warnings)
        if p.name == "data-inventory.json":
            check_inventory(rel, text, errors)
        n = len(PLACEHOLDER.findall(text))
        if n:
            placeholders[rel] = n
    result = {"ok": not errors, "errors": errors[:100], "warnings": warnings[:100],
              "open_placeholders": placeholders,
              "note": "Files with open placeholders are incomplete and need business-owner input."}
    sys.stdout.write(json.dumps(result, indent=1, ensure_ascii=True) + "\n")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
