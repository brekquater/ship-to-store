"""Tests for .github/release.py, the helper behind the release workflow."""
import datetime
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("release", REPO / ".github" / "release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)

CHANGELOG = """# Changelog

## Unreleased

### Fixed
- A thing.

## 1.4.2 (2026-01-01)

- Old entry.
"""


class Release(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sts-rel-"))
        self.plugin, self.log = self.tmp / "plugin.json", self.tmp / "CHANGELOG.md"
        self.plugin.write_text('{\n  "name": "x",\n  "version": "1.4.2",\n  "keywords": ["a", "b"]\n}\n', encoding="utf-8")
        self.log.write_text(CHANGELOG, encoding="utf-8")
        self.saved = release.PLUGIN, release.CHANGELOG
        release.PLUGIN, release.CHANGELOG = self.plugin, self.log

    def tearDown(self):
        release.PLUGIN, release.CHANGELOG = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_bump_parts(self):
        day = datetime.date(2026, 2, 3)
        self.assertEqual("1.4.3", release.bump("patch", day))
        self.log.write_text(self.log.read_text(encoding="utf-8").replace("## Unreleased\n", "## Unreleased\n- more\n"), encoding="utf-8")
        self.assertEqual("1.5.0", release.bump("minor", day))
        self.log.write_text(self.log.read_text(encoding="utf-8").replace("## Unreleased\n", "## Unreleased\n- more\n"), encoding="utf-8")
        self.assertEqual("2.0.0", release.bump("major", day))
        self.assertEqual("2.0.0", json.loads(self.plugin.read_text(encoding="utf-8"))["version"])
        self.assertIn('"keywords": ["a", "b"]', self.plugin.read_text(encoding="utf-8"))  # formatting kept

    def test_changelog_rolls_over_and_notes(self):
        release.bump("patch", datetime.date(2026, 2, 3))
        log = self.log.read_text(encoding="utf-8")
        self.assertTrue(log.startswith("# Changelog\n\n## Unreleased\n\n## 1.4.3 (2026-02-03)\n"))
        self.assertEqual("### Fixed\n- A thing.", release.notes("1.4.3"))
        self.assertEqual("- Old entry.", release.notes("1.4.2"))

    def test_refuses_empty_release(self):
        self.log.write_text("# Changelog\n\n## Unreleased\n\n## 1.4.2 (2026-01-01)\n- Old.\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            release.bump("patch")
        self.assertIn('"version": "1.4.2"', self.plugin.read_text(encoding="utf-8"))  # nothing written
        with self.assertRaises(SystemExit):
            release.notes("9.9.9")

    def test_real_repo_files(self):
        """The live CHANGELOG has notes for the current plugin version."""
        self.tearDown()
        self.assertTrue(release.notes(release.version()))

    def test_cli_prints_utf8_on_any_console(self):
        import os
        import subprocess
        import sys
        (self.tmp / ".github").mkdir()
        (self.tmp / ".claude-plugin").mkdir()
        shutil.copy(str(REPO / ".github" / "release.py"), str(self.tmp / ".github" / "release.py"))
        shutil.copy(str(self.plugin), str(self.tmp / ".claude-plugin" / "plugin.json"))
        (self.tmp / "CHANGELOG.md").write_text(CHANGELOG.replace("- Old entry.", "- Old entry → new."), encoding="utf-8")
        p = subprocess.run([sys.executable, "-I", str(self.tmp / ".github" / "release.py"), "notes", "1.4.2"],
                           capture_output=True, env=dict(os.environ, PYTHONIOENCODING="cp1252"), timeout=60)
        self.assertEqual(0, p.returncode, p.stderr)
        self.assertEqual("- Old entry → new.", p.stdout.decode("utf-8").strip())


if __name__ == "__main__":
    unittest.main()
