"""Tests that an answer names the page it came from.

Run this area with
python3 scripts/run_checks.py tests/test_answer_pages.py.
"""

import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _folder in (_ROOT / "tests", _ROOT / "scripts"):
    _text = str(_folder)
    if _text not in sys.path:
        sys.path.insert(0, _text)

from answer_support import (
    AGREEMENTS,
    CLOCK,
    ROOT,
    SCRIPTS,
    RunningSite,
    _FrozenClock,
    _SavedEnv,
    _wrapped_forms,
    docs,
    page_named,
    question_rows,
)
import agreed
import answer_reply
import demo_chat
import front_desk
import price_reply
import read_pages
import serve_sample_site
import urgent_reply

class AnswerChecks(unittest.TestCase):
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

    def test_every_answered_question_names_the_right_page(self):
        """Every question your pages answer ends with the page it used."""
        rows = question_rows()
        self.assertEqual(len(rows), 28)
        pages = self._pages()
        by_name = {page["name"]: page for page in pages}
        answered = [row for row in rows if row["group"] == "Answered by your pages"]
        self.assertEqual(
            [row["number"] for row in answered],
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14, 15, 16, 17, 18, 19, 20, 23],
        )
        for row in answered:
            self.assertIsNone(urgent_reply.reply_if_urgent(row["question"]), row["question"])
            name = page_named(row["detail"])
            self.assertIn(name, by_name, row["question"])
            answer = front_desk.reply_to(row["question"], base_url=self.site.base)
            written = answer_reply.write_answer(row["question"], pages)
            self.assertEqual(answer, written, row["question"])
            self.assertNotEqual(answer, self._callback(), row["question"])
            self.assertIn(name, answer, row["question"])
            self.assertTrue(answer.endswith(f"From {name}."), row["question"])
            self.assertNotIn("Maple Street Plumbing is a fictional business", answer, row["question"])
            self.assertNotIn("Home Services Pricing", answer, row["question"])
            body = answer[: -len(f"From {name}.")].strip()
            page_text = by_name[name]["text"]
            parts = [part for part in re.split(r"(?<=[.!?])\s+", body) if part]
            copied = bool(parts) and all(part in page_text for part in parts)
            if not copied:
                self.assertRegex(body, r"^(?:Yes|No),", row["question"])
                self.assertTrue(price_reply.find_amounts(answer), row["question"])
            for fact in CLOCK.findall(row["detail"]) + price_reply.find_amounts(row["detail"]):
                self.assertIn(fact, answer, row["question"])
                self.assertIn(fact, by_name[name]["text"], row["question"])
        sunday = next(row for row in answered if row["question"] == "Are you open Sundays?")
        sunday_answer = front_desk.reply_to(sunday["question"], base_url=self.site.base)
        self.assertIn("closed", sunday_answer.lower())
        self.assertNotIn("saturday", sunday_answer.lower())
        booking = next(row for row in answered if "book or cancel" in row["question"].lower())
        booking_answer = front_desk.reply_to(booking["question"], base_url=self.site.base)
        self.assertIn("book", booking_answer.lower())
        self.assertIn("cancel", booking_answer.lower())
        self.assertIn("Contact", booking_answer)

class FromPageChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()
        self._post = answer_reply._post_message
        self._saved_log = answer_reply.FAILURE_LOG
        self._log_dir = tempfile.TemporaryDirectory()
        answer_reply.FAILURE_LOG = Path(self._log_dir.name) / "error-notes.log"

    def tearDown(self):
        answer_reply._post_message = self._post
        answer_reply.FAILURE_LOG = self._saved_log
        self._log_dir.cleanup()
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def _pages(self):
        return read_pages.read_pages(self.site.base)

    def _callback(self):
        return answer_reply.callback_reply()

    def _block_network(self):
        def fail(*_args, **_kwargs):
            raise AssertionError("the real API was called")

        answer_reply._post_message = fail

    def test_a_mocked_reply_ends_with_the_page_name(self):
        """A page-based answer ends with From and the page name."""
        pages = self._pages()
        callback = self._callback()
        question = "Are you open Saturdays?"
        cases = (
            (
                "Yes, we service tankless water heaters. (Source: Services page)",
                "Yes, we service tankless water heaters. From Services.",
            ),
            (
                "Yes. (Source: the Services page)",
                "Yes. From Services.",
            ),
            (
                "Monday to Friday: 8:00 am to 5:00 pm.\nSource: Hours & FAQ page",
                "Monday to Friday: 8:00 am to 5:00 pm. From Hours & FAQ.",
            ),
            (
                "Sunday: closed. (Hours & FAQ page)",
                "Sunday: closed. From Hours & FAQ.",
            ),
            (
                "We are open Saturdays. From the Hours & FAQ page.",
                "We are open Saturdays. From Hours & FAQ.",
            ),
            (
                "Yes, open Saturday morning. From Hours & FAQ.",
                "Yes, open Saturday morning. From Hours & FAQ.",
            ),
        )
        seen = {}

        def client(payload):
            seen["instructions"] = payload["messages"][0]["content"]
            return {
                "content": [
                    {"type": "thinking", "thinking": "pick a page"},
                    {"type": "text", "text": seen["reply"]},
                ]
            }

        self._block_network()
        for raw, expected in cases:
            seen["reply"] = raw
            got = front_desk.reply_to(question, base_url=self.site.base, client=client)
            self.assertEqual(got, expected, raw)
            self.assertNotIn("pick a page", got)
        instructions = seen["instructions"]
        self.assertIn("End the answer with exactly From <Page name>.", instructions)
        self.assertIn("For example, From Hours & FAQ.", instructions)
        self.assertIn("Name the page the answer came from.", instructions)
        seen["reply"] = callback
        self.assertEqual(answer_reply.write_answer(question, pages, client=client), callback)
        seen["reply"] = callback + "\n(Source: Home page)"
        self.assertEqual(answer_reply.write_answer(question, pages, client=client), callback)
        called = {"n": 0}

        def client_urgent(_payload):
            called["n"] += 1
            return {"content": [{"type": "text", "text": "No. (Source: Contact page)"}]}

        urgent = front_desk.reply_to("I have a frozen pipe", client=client_urgent)
        self.assertEqual(urgent, urgent_reply.fixed_urgent_reply())
        self.assertEqual(called["n"], 0)

class SourceLineChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def test_no_reply_contains_its_source_line_twice(self):
        """No reply contains its source line twice."""
        question = "How do I book a visit for Saturday morning?"
        pages = read_pages.read_pages(self.site.base)
        replies = []
        for row in question_rows():
            replies.append(front_desk.reply_to(row["question"], base_url=self.site.base))
        replies.append(front_desk.reply_to(question, base_url=self.site.base))
        duplicated = (
            "We're open Saturday from 8:00 am to 12:00 pm. "
            "To book, call our main line at 030 0000 0000.\n\n"
            "From Hours & FAQ and Contact. From Hours & FAQ and Contact."
        )
        on_its_own_line = (
            "We're open Saturday from 8:00 am to 12:00 pm. "
            "To book, call our main line at 030 0000 0000.\n\n"
            "From Hours & FAQ and Contact."
        )
        named_apart = (
            "We're open Saturday from 8:00 am to 12:00 pm. From Hours & FAQ.\n\n"
            "To book, call our main line at 030 0000 0000. From Contact."
        )
        once = (
            "We're open Saturday from 8:00 am to 12:00 pm. "
            "To book, call our main line at 030 0000 0000. "
            "From Hours & FAQ and Contact."
        )
        named_once = (
            "We're open Saturday from 8:00 am to 12:00 pm.\n\n"
            "To book, call our main line at 030 0000 0000. "
            "From Hours & FAQ and Contact."
        )

        def client(payload, text):
            return {"content": [{"type": "text", "text": text}]}

        for draft, expected in (
            (duplicated, once),
            (on_its_own_line, once),
            (named_apart, named_once),
        ):
            got = front_desk.reply_to(
                question,
                base_url=self.site.base,
                client=lambda payload, text=draft: client(payload, text),
            )
            self.assertEqual(got, expected, draft)
            replies.append(got)
        for reply in replies:
            sources = re.findall(r"(?<!\S)From\s+", reply)
            self.assertLessEqual(len(sources), 1, reply)
            self.assertNotRegex(reply, r"\n\s*From\s+")

    def test_a_reversed_source_line_is_written_once(self):
        """A model source line in another order is replaced by one fixed line."""
        question = "How do I book a visit for Saturday morning?"
        draft = (
            "To book, call our main line at 030 0000 0000. "
            "We're open Saturdays from 8:00 am to 12:00 pm.\n\n"
            "From Contact and Hours & FAQ."
        )
        missing_period = (
            "To book, call our main line at 030 0000 0000. "
            "We're open Saturdays from 8:00 am to 12:00 pm.\n\n"
            "From Contact and Hours & FAQ"
        )
        joined_with_ampersand = (
            "To book, call our main line at 030 0000 0000. "
            "We're open Saturdays from 8:00 am to 12:00 pm.\n\n"
            "From Contact & Hours & FAQ."
        )
        expected = (
            "To book, call our main line at 030 0000 0000. "
            "We're open Saturdays from 8:00 am to 12:00 pm. "
            "From Hours & FAQ and Contact."
        )

        def client(payload, text):
            return {"content": [{"type": "text", "text": text}]}

        for model_reply in (draft, missing_period, joined_with_ampersand):
            got = front_desk.reply_to(
                question,
                base_url=self.site.base,
                client=lambda payload, text=model_reply: client(payload, text),
            )
            self.assertEqual(got, expected, model_reply)
            self.assertEqual(len(re.findall(r"(?<!\S)From\s+", got)), 1, got)
            self.assertIn("from 8:00 am", got)

if __name__ == "__main__":
    unittest.main()
