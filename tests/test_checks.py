"""Automatic checks for Maple Street Front Desk.

Later changes add the page, question, urgent-word, and price checks here.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "README.md",
    "AGENTS.md",
    ".python-version",
    "scripts/run_checks.py",
    "docs/behaviour.md",
    "docs/agreements.md",
    ".cursor/rules/working-in-this-repo.mdc",
    ".cursor/rules/tests.mdc",
    "tests/test_links.py",
    ".cursor/team/README.md",
    ".cursor/team/shared-standards.mdc",
    ".cursor/team/architect.mdc",
    ".cursor/team/qa-engineer.mdc",
    ".cursor/team/technical-writer.mdc",
    ".cursor/commands/run-checks.md",
    ".cursor/commands/pr-summary.md",
    ".github/pull_request_template.md",
    ".github/workflows/ci.yml",
)


class ProjectChecks(unittest.TestCase):
    def test_setup_files_are_present(self):
        missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
        self.assertEqual(missing, [])

    def test_python_pin_is_set(self):
        """The running interpreter matches the Python pin in .python-version."""
        version = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
        running = f"{sys.version_info.major}.{sys.version_info.minor}"
        self.assertTrue(version == running or version.startswith(running + "."))


if __name__ == "__main__":
    unittest.main()
