"""Tests for choosing a reply and printing it.

Run this area with
python3 scripts/run_checks.py tests/test_answer_write.py.
"""

import contextlib
import io
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _folder in (_ROOT / "tests", _ROOT / "scripts"):
    _text = str(_folder)
    if _text not in sys.path:
        sys.path.insert(0, _text)

import answer_reply
import front_desk
import read_pages
import serve_sample_site
import urgent_reply
from answer_support import (
    RunningSite,
    _SavedEnv,
    question_rows,
)


class UrgentPathChecks(unittest.TestCase):
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

    def test_an_urgent_message_stops_at_the_first_part(self):
        """An urgent message stops at the first part."""
        reply = urgent_reply.fixed_urgent_reply()
        rows = question_rows()
        urgent_rows = [row for row in rows if urgent_reply.reply_if_urgent(row["question"])]
        self.assertGreaterEqual(len(urgent_rows), 1)
        called = {"pages": 0, "writer": 0}

        def read_fail(base_url):
            called["pages"] += 1
            raise AssertionError("pages were read for an urgent message")

        def writer(question, instructions, pages):
            called["writer"] += 1
            raise AssertionError("the answer writer ran for an urgent message")

        original = read_pages.read_pages
        read_pages.read_pages = read_fail
        try:
            for word in urgent_reply.urgent_words():
                got = front_desk.reply_to(f"We have {word}.", writer=writer)
                self.assertEqual(got, reply, word)
                self.assertNotIn("$", got)
            for row in urgent_rows:
                got = front_desk.reply_to(row["question"], writer=writer)
                self.assertEqual(got, reply, row["question"])
        finally:
            read_pages.read_pages = original
        self.assertEqual(called["pages"], 0)
        self.assertEqual(called["writer"], 0)
        pages = self._pages()
        for row in urgent_rows:
            self.assertEqual(
                answer_reply.write_answer(row["question"], pages),
                self._callback(),
                row["question"],
            )


class PrintedReplyChecks(unittest.TestCase):
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

    def test_checking_a_message_prints_the_reply(self):
        """Checking a message prints the answer, the callback reply, or the urgent reply."""
        rows = question_rows()
        callback = self._callback()
        urgent = urgent_reply.fixed_urgent_reply()
        answered = next(row for row in rows if row["group"] == "Answered by your pages")
        uncovered = next(
            row
            for row in rows
            if row["group"] != "Answered by your pages"
            and urgent_reply.reply_if_urgent(row["question"]) is None
        )
        urgent_row = next(row for row in rows if urgent_reply.reply_if_urgent(row["question"]))
        expected = front_desk.reply_to(answered["question"], base_url=self.site.base)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = answer_reply.main(answered["question"].split() + [self.site.base])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), expected + "\n")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = front_desk.main(uncovered["question"].split() + [self.site.base])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), callback + "\n")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = front_desk.main(urgent_row["question"].split())
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), urgent + "\n")
        for command in (answer_reply.main, front_desk.main):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(command(["--help"]), 2)
            self.assertIn("Usage:", stderr.getvalue())
            self.assertNotIn(callback, stderr.getvalue())
            self.assertNotIn(urgent, stderr.getvalue())
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(command([]), 2)


if __name__ == "__main__":
    unittest.main()
