#!/usr/bin/env python3
"""Release helper used by .github/workflows/release.yml (stdlib only).

  release.py version                 print the plugin version from .claude-plugin/plugin.json
  release.py bump patch|minor|major  bump plugin.json and turn CHANGELOG "## Unreleased" into the new version
  release.py notes VERSION           print the CHANGELOG section for VERSION (the release notes)
"""
import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
CHANGELOG = ROOT / "CHANGELOG.md"
VERSION_RE = re.compile(r'("version"\s*:\s*")(\d+)\.(\d+)\.(\d+)(")')


def section(log, heading):
    """Match a '## <heading>' section up to the next '## ' heading."""
    return re.search(r"^## %s\b[^\n]*\n(.*?)(?=^## |\Z)" % re.escape(heading), log, re.M | re.S)


def version():
    m = VERSION_RE.search(PLUGIN.read_text(encoding="utf-8"))
    if not m:
        sys.exit("plugin.json has no x.y.z version")
    return "%s.%s.%s" % m.group(2, 3, 4)


def bump(part, today=None):
    major, minor, patch = (int(n) for n in version().split("."))
    new = {"major": "%d.0.0" % (major + 1), "minor": "%d.%d.0" % (major, minor + 1),
           "patch": "%d.%d.%d" % (major, minor, patch + 1)}[part]
    log = CHANGELOG.read_text(encoding="utf-8")
    m = section(log, "Unreleased")
    if not m or not m.group(1).strip():
        sys.exit('CHANGELOG.md has nothing under "## Unreleased"; add entries before releasing')
    date = (today or datetime.date.today()).isoformat()
    log = log[:m.start()] + "## Unreleased\n\n## %s (%s)\n%s" % (new, date, m.group(1)) + log[m.end():]
    CHANGELOG.write_text(log, encoding="utf-8")
    PLUGIN.write_text(VERSION_RE.sub(lambda v: v.group(1) + new + v.group(5), PLUGIN.read_text(encoding="utf-8"), 1),
                      encoding="utf-8")
    return new


def notes(ver):
    m = section(CHANGELOG.read_text(encoding="utf-8"), ver)
    if not m or not m.group(1).strip():
        sys.exit("CHANGELOG.md has no entries for %s" % ver)
    return m.group(1).strip()


def out(text):
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))  # UTF-8 even on a cp1252 Windows console


if __name__ == "__main__":
    cmd = sys.argv[1:] or ["help"]
    if cmd[0] == "version":
        out(version())
    elif cmd[0] == "bump" and len(cmd) == 2 and cmd[1] in ("patch", "minor", "major"):
        out(bump(cmd[1]))
    elif cmd[0] == "notes" and len(cmd) == 2:
        out(notes(cmd[1]))
    else:
        sys.exit(__doc__)
