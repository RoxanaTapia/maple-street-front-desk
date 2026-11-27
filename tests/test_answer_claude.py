"""Tests for the Claude call that writes an answer.

Run this area with
python3 scripts/run_checks.py tests/test_answer_claude.py.
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

class ClaudeAnswerChecks(unittest.TestCase):
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

    def test_a_failed_call_gets_the_outage_reply(self):
        """A failed Claude call gets the outage reply, not the missing-information reply."""
        pages = self._pages()
        callback = self._callback()
        outage = answer_reply.outage_reply()
        self.assertNotEqual(outage, callback)
        question = "Are you open Saturdays?"
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        def client(_payload):
            raise TimeoutError("timed out")

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            got = front_desk.reply_to(question, base_url=self.site.base, client=client)
        self.assertEqual(got, outage)
        self.assertNotEqual(got, callback)
        self.assertNotIn("test-key", got)
        self.assertNotIn("Traceback", got)
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertNotIn("timed out", got)

        def client_down(_payload):
            raise urllib.error.URLError("network down")

        down = answer_reply.write_answer(question, pages, client=client_down)
        self.assertEqual(down, outage)
        self.assertNotEqual(down, callback)

        def client_empty(_payload):
            return {"content": [{"type": "thinking", "thinking": "no text"}]}

        empty = answer_reply.write_answer(question, pages, client=client_empty)
        self.assertEqual(empty, outage)
        self.assertNotEqual(empty, callback)

        def boom(payload, key, timeout):
            self.assertEqual(key, "test-key")
            self.assertEqual(timeout, answer_reply.TIMEOUT_SECONDS)
            self.assertNotIn("test-key", json.dumps(payload))
            raise urllib.error.HTTPError(
                "https://api.anthropic.com/v1/messages",
                401,
                "Unauthorized",
                hdrs=None,
                fp=io.BytesIO(b""),
            )

        answer_reply._post_message = boom
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            got = answer_reply.write_answer(question, pages)
        self.assertEqual(got, answer_reply.outage_reply())
        self.assertNotEqual(got, callback)
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertNotIn("Unauthorized", got)
        self.assertNotIn("test-key", got)

    def test_the_call_uses_a_short_timeout(self):
        """The Claude call uses a short timeout and keeps the key out of the message."""
        seen = {}

        class Fake:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"content":[{"type":"text","text":"Yes. From Services."}]}'

        def fake_open(request, timeout=None):
            seen["timeout"] = timeout
            seen["key"] = request.get_header("X-api-key")
            seen["body"] = request.data.decode("utf-8")
            seen["url"] = request.full_url
            return Fake()

        original = urllib.request.urlopen
        answer_reply.urllib.request.urlopen = fake_open
        try:
            body = answer_reply._post_message(
                {"model": answer_reply.DEFAULT_MODEL, "messages": []},
                "test-key",
                answer_reply.TIMEOUT_SECONDS,
            )
        finally:
            answer_reply.urllib.request.urlopen = original
        self.assertGreater(answer_reply.TIMEOUT_SECONDS, 0)
        self.assertLessEqual(answer_reply.TIMEOUT_SECONDS, 20)
        self.assertEqual(seen["timeout"], answer_reply.TIMEOUT_SECONDS)
        self.assertEqual(seen["url"], "https://api.anthropic.com/v1/messages")
        self.assertEqual(seen["key"], "test-key")
        self.assertNotIn("test-key", seen["body"])
        self.assertEqual(answer_reply._message_text(body), "Yes. From Services.")

    def test_the_agreements_record_the_simpler_setup(self):
        """The agreements record the simpler setup and Claude as the AI."""
        agreements = AGREEMENTS.read_text(encoding="utf-8")
        self.assertIn("## How answers are written\n", agreements)
        section = agreements.split("## How answers are written", 1)[1]
        self.assertIn("simpler setup", section.lower())
        self.assertIn("Claude", section)
        self.assertIn("six pages", section.lower())
        self.assertIn("document search engine", section.lower())
        for path in docs():
            text = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("ai-doc", text, path.relative_to(ROOT))
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("ANTHROPIC_API_KEY", example)
        self.assertIn("CLAUDE_MODEL", example)
        self.assertNotIn("sk-ant-", example)
        self.assertNotIn("sk-ant-", ignore)
        self.assertTrue(any(line.strip() == ".env" for line in ignore.splitlines()))

if __name__ == "__main__":
    unittest.main()
