"""Tests for the instructions sent with one question.

Run this area with
python3 scripts/run_checks.py tests/test_answer_instructions.py.
"""

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _folder in (_ROOT / "tests", _ROOT / "scripts"):
    _text = str(_folder)
    if _text not in sys.path:
        sys.path.insert(0, _text)

import answer_reply
import read_pages
import serve_sample_site
import urgent_reply
from answer_support import (
    SCRIPTS,
    RunningSite,
    _SavedEnv,
)


class InstructionChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def _pages(self):
        return read_pages.read_pages(self.site.base)

    def _callback(self):
        return answer_reply.callback_reply()

    def test_the_instructions_include_every_page_and_the_callback(self):
        """The instructions sent to the writer include every page and the callback reply."""
        pages = self._pages()
        self.assertEqual(len(pages), 6)
        callback = self._callback()
        question = "Are you open Saturdays?"
        sent = {}

        def writer(question_arg, instructions, pages_arg):
            sent["question"] = question_arg
            sent["instructions"] = instructions
            sent["pages"] = pages_arg
            return answer_reply.stand_in_writer(question_arg, instructions, pages_arg)

        got = answer_reply.write_answer(question, pages, writer=writer)
        self.assertEqual(sent["question"], question)
        self.assertIs(sent["pages"], pages)
        instructions = sent["instructions"]
        self.assertEqual(instructions, answer_reply.build_instructions(question, pages))
        self.assertIn("Answer the customer's question only from these pages.", instructions)
        self.assertIn("Keep the answer short.", instructions)
        self.assertIn("Name the page the answer came from.", instructions)
        self.assertIn(callback, instructions)
        self.assertNotIn(answer_reply.outage_reply(), instructions)
        self.assertIn(question, instructions)
        for page in pages:
            self.assertEqual(page["status"], "read", page["name"])
            self.assertTrue(page["text"], page["name"])
            self.assertIn(f"Page: {page['name']}", instructions)
            self.assertIn(page["text"], instructions)
        self.assertIn("Hours & FAQ", got)
        self.assertNotEqual(got, callback)
        self.assertEqual(
            answer_reply.stand_in_writer(question, "No pages here.", pages),
            callback,
        )
        self.assertIn("not a real AI", answer_reply.stand_in_writer.__doc__)

        def custom(question_arg, instructions, pages_arg):
            return "CUSTOM"

        self.assertEqual(
            answer_reply.write_answer("Are you open Saturdays?", pages, writer=custom),
            "CUSTOM",
        )
        self.assertEqual(answer_reply.write_answer("Hello", pages, writer=custom), "CUSTOM")
        for name in ("answer_reply.py", "front_desk.py"):
            source = (SCRIPTS / name).read_text(encoding="utf-8")
            self.assertNotIn(callback, source)
            self.assertNotIn(answer_reply.outage_reply(), source)
            self.assertNotIn(urgent_reply.fixed_urgent_reply(), source)
            lowered = source.lower()
            self.assertNotIn("openai", lowered)
            self.assertNotIn("grok", lowered)
            self.assertNotIn("sk-ant-", lowered)
        front = (SCRIPTS / "front_desk.py").read_text(encoding="utf-8")
        self.assertNotIn("anthropic", front.lower())
        self.assertNotIn("API_KEY", front)
        writer = (SCRIPTS / "answer_reply.py").read_text(encoding="utf-8")
        self.assertIn("https://api.anthropic.com/v1/messages", writer)
        self.assertIn("ANTHROPIC_API_KEY", writer)
        self.assertIn("CLAUDE_MODEL", writer)


if __name__ == "__main__":
    unittest.main()
