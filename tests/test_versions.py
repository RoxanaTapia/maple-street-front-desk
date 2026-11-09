"""The setup guide names the versions the assistant was tested on.

The Claude model and the API version are read from the answer script.
The Python version is read from .python-version. The note has to name
those same values.

Run this area with
python3 scripts/run_checks.py tests/test_versions.py
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import answer_reply

SETUP = ROOT / "docs" / "setup-guide.md"
HEADING = "Versions it was tested on"


def versions_note():
    found = False
    lines = []
    for line in SETUP.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if found:
                break
            found = line[3:].strip() == HEADING
            continue
        if found:
            lines.append(line)
    return "\n".join(lines)


def names_exactly(text, value):
    """True when value appears as its own token, not as part of a longer one."""
    return re.search(rf"(?<![\w.-]){re.escape(value)}(?![\w.-])", text) is not None


class TestedVersionChecks(unittest.TestCase):
    def test_the_note_matches_the_tested_versions(self):
        """The setup guide names the Claude model, the API version, and the Python version that were tested."""
        note = versions_note()
        self.assertTrue(note.strip(), "The setup guide has no versions note.")
        python_version = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
        self.assertTrue(python_version)
        for value in (
            answer_reply.DEFAULT_MODEL,
            answer_reply.API_VERSION,
            answer_reply.MODEL_ENV,
            python_version,
        ):
            self.assertTrue(
                names_exactly(note, value),
                f"{value} is missing from the versions note.",
            )


if __name__ == "__main__":
    unittest.main()
