"""Automated tests for Maple Street Front Desk.

Page tests live in test_pages.py. Urgent reply tests live in
test_urgent.py. Price tests live in test_prices.py.
Answer tests live in one file for each kind of reply.
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
    "docs/how-it-works.md",
    "docs/handover.md",
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
    "scripts/agreed.py",
    "scripts/read_pages.py",
    "scripts/serve_sample_site.py",
    "scripts/urgent_reply.py",
    "scripts/price_reply.py",
    "scripts/answer_reply.py",
    "scripts/front_desk.py",
    "tests/test_pages.py",
    "tests/test_urgent.py",
    "tests/test_prices.py",
    "tests/answer_support.py",
    "tests/test_answer_pages.py",
    "tests/test_answer_hours.py",
    "tests/test_answer_prices.py",
    "tests/test_answer_spoken.py",
    "tests/test_answer_callback.py",
    "tests/test_answer_fixed.py",
    "tests/test_answer_instructions.py",
    "tests/test_answer_stand_in.py",
    "tests/test_answer_claude.py",
    "tests/test_answer_notes.py",
    "tests/test_answer_text.py",
    "tests/test_answer_write.py",
    "tests/test_off_topic.py",
)


class ProjectChecks(unittest.TestCase):
    def test_setup_files_are_present(self):
        """The project files are in place."""
        missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
        self.assertEqual(missing, [])
        self.assertFalse((ROOT / "docs" / "contributing.md").exists())

    def test_python_pin_is_set(self):
        """Python matches the version this project records."""
        version = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
        running = f"{sys.version_info.major}.{sys.version_info.minor}"
        self.assertTrue(version == running or version.startswith(running + "."))

    def test_a_proposed_change_runs_the_checks(self):
        """A proposed change runs the automated tests for the pages, urgent words, prices, answers, the demo chat, the calm screen, the Saturday night chips, the daily limit, the icons, and the demo kit."""
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        for command in (
            "tests/test_checks.py",
            "tests/test_links.py",
            "tests/test_pages.py:PageListChecks",
            "tests/test_pages.py:QuestionCoverageChecks",
            "tests/test_urgent.py:UrgentReplyChecks",
            "tests/test_prices.py:PriceChecks",
            "tests/test_prices.py:LongerPriceChecks",
            "tests/test_prices.py:ServicePriceChecks",
            "tests/test_answer_pages.py",
            "tests/test_answer_claude.py",
            "tests/test_answer_notes.py",
            "tests/test_unreadable_pages.py:UnreadablePageNoteChecks",
            "tests/test_answer_fixed.py",
            "tests/test_answer_hours.py",
            "tests/test_answer_callback.py",
            "tests/test_answer_text.py",
            "tests/test_answer_prices.py",
            "tests/test_answer_spoken.py",
            "tests/test_answer_stand_in.py",
            "tests/test_answer_instructions.py",
            "tests/test_answer_write.py",
            "tests/test_run_through.py:RunThroughReplyChecks",
            "tests/test_run_through.py:SecondRunThroughChecks",
            "tests/test_off_topic.py:OffTopicReplyChecks",
            "tests/test_demo.py:DemoChatChecks",
            "tests/test_case_flow.py:CaseFlowChecks",
            "tests/test_calm_screen.py:CalmScreenChecks",
            "tests/test_chat_limit.py:ChatLimitChecks",
            "tests/test_brand.py:IconChecks",
            "tests/test_brand.py:DemoKitCopyChecks",
        ):
            self.assertIn(command, workflow)
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        self.assertIn("fixed urgent reply", behaviour)
        self.assertIn("A price", behaviour)
        self.assertIn("ends by naming the page it used (From `<Page>`.)", behaviour)


if __name__ == "__main__":
    unittest.main()
