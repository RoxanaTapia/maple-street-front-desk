"""Tests for the stand-in that answers when no key is set.

Run this area with
python3 scripts/run_checks.py tests/test_answer_stand_in.py.
"""

import os
import sys
import tempfile
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
from answer_support import (
    RunningSite,
    _SavedEnv,
)


class StandInChecks(unittest.TestCase):
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

    def test_no_key_uses_the_stand_in(self):
        """With no key, the stand-in answers and no call is made."""
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        pages = self._pages()
        question = "Are you open Saturdays?"
        called = {"n": 0}

        def boom(*_args, **_kwargs):
            called["n"] += 1
            raise AssertionError("the API was called with no key")

        answer_reply._post_message = boom
        got = front_desk.reply_to(question, base_url=self.site.base)
        written = answer_reply.write_answer(question, pages)
        self.assertEqual(called["n"], 0)
        self.assertEqual(got, written)
        self.assertIn("Hours & FAQ", got)
        self.assertIn("From Hours & FAQ.", got)
        self.assertIn("8:00 am", got)
        self.assertNotEqual(got, self._callback())
        os.environ["ANTHROPIC_API_KEY"] = "   "
        again = answer_reply.write_answer(question, pages)
        self.assertEqual(called["n"], 0)
        self.assertEqual(again, written)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        uncovered = answer_reply.write_answer("How long is your warranty?", pages)
        self.assertEqual(uncovered, self._callback())
        self.assertEqual(called["n"], 0)


if __name__ == "__main__":
    unittest.main()
