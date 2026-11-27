"""Tests for the fixed replies read from the agreements.

Run this area with
python3 scripts/run_checks.py tests/test_answer_fixed.py.
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

class OutageReplyChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()
        self._post = answer_reply._post_message
        self._saved_log = answer_reply.FAILURE_LOG
        self._saved_clock = answer_reply.datetime
        self._log_dir = tempfile.TemporaryDirectory()
        answer_reply.FAILURE_LOG = Path(self._log_dir.name) / "error-notes.log"

    def tearDown(self):
        answer_reply._post_message = self._post
        answer_reply.datetime = self._saved_clock
        answer_reply.FAILURE_LOG = self._saved_log
        self._log_dir.cleanup()
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def _pages(self):
        return read_pages.read_pages(self.site.base)

    def _block_network(self):
        def fail(*_args, **_kwargs):
            raise AssertionError("the real API was called")

        answer_reply._post_message = fail

    def test_the_two_replies_are_separate_sentences(self):
        """The outage reply and the missing-information reply are separate agreed sentences."""
        self._block_network()
        missing = answer_reply.callback_reply()
        outage = answer_reply.outage_reply()
        self.assertEqual(price_reply.callback_reply(), missing)
        self.assertNotEqual(outage, missing)
        self.assertNotEqual(missing, "I can't confirm that from your pages.")
        agreements = AGREEMENTS.read_text(encoding="utf-8")
        self.assertIn("## When the pages don't say\n", agreements)
        self.assertIn("## When the assistant can't look it up\n", agreements)
        self.assertEqual(agreements.count(missing), 1)
        self.assertEqual(agreements.count(outage), 1)
        for name in ("answer_reply.py", "price_reply.py", "front_desk.py", "demo_chat.py"):
            source = (SCRIPTS / name).read_text(encoding="utf-8")
            self.assertNotIn(missing, source, name)
            self.assertNotIn(outage, source, name)
        sample = (
            "## When the pages don't say\n\n> Call the office.\n\n"
            "## When the assistant can't look it up\n\n> The lookup is down.\n"
        )
        self.assertEqual(answer_reply.callback_reply(sample), "Call the office.")
        self.assertEqual(answer_reply.outage_reply(sample), "The lookup is down.")
        pages = self._pages()
        question = "Where is the shop?"

        def client(_payload):
            raise TimeoutError(question)

        with self.assertLogs(level="WARNING"):
            got = answer_reply.write_answer(question, pages, client=client, text=sample)
        self.assertEqual(got, "The lookup is down.")
        self.assertNotEqual(got, "Call the office.")
        note = answer_reply.FAILURE_LOG.read_text(encoding="utf-8")
        self.assertNotIn(question, note)
        self.assertNotIn("The lookup is down.", note)
        self.assertNotIn("Call the office.", note)
        stamp, kind = note.strip().split(" ", 1)
        self.assertEqual(kind, "timeout")
        datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
        self.assertEqual(note, f"{stamp} timeout\n")

    def test_a_changed_call_us_sentence_is_what_the_replies_use(self):
        """A changed call-us sentence, including the phone number, is what the replies and the automated tests use."""
        self._block_network()
        original_callback = answer_reply.callback_reply()
        original_outage = answer_reply.outage_reply()
        callback = "Please phone the office on 030 0000 1111 and we will check."
        outage = "Sorry, that lookup is unavailable. Please phone the office on 030 0000 1111."
        self.assertNotEqual(callback, original_callback)
        self.assertNotEqual(outage, original_outage)
        self.assertNotIn("030 0000 0000", callback)
        self.assertNotIn("030 0000 0000", outage)
        self.assertIn("030 0000 1111", callback)
        self.assertIn("030 0000 1111", outage)
        body = AGREEMENTS.read_text(encoding="utf-8")
        changed = body
        for old, new in ((original_callback, callback), (original_outage, outage)):
            needle = f"> {old}"
            self.assertEqual(changed.count(needle), 1)
            changed = changed.replace(needle, f"> {new}", 1)
        self.assertNotIn(original_callback, changed)
        self.assertNotIn(original_outage, changed)
        saved_agreements = agreed.AGREEMENTS
        try:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "agreements.md"
                path.write_text(changed, encoding="utf-8")
                agreed.AGREEMENTS = path
                self.assertEqual(answer_reply.callback_reply(), callback)
                self.assertEqual(answer_reply.outage_reply(), outage)
                self.assertEqual(price_reply.callback_reply(), callback)
                missing = front_desk.reply_to(
                    "How long is your warranty?",
                    base_url=self.site.base,
                )
                self.assertEqual(missing, callback)
                self.assertNotEqual(missing, outage)

                def client(_payload):
                    raise TimeoutError("down")

                with self.assertLogs(level="WARNING"):
                    failed = front_desk.reply_to(
                        "Are you open Saturdays?",
                        base_url=self.site.base,
                        client=client,
                    )
                self.assertEqual(failed, outage)
                self.assertNotEqual(failed, callback)

                def bad_price(_question, _instructions, _pages):
                    return "A water heater replacement is $1,200."

                rejected = front_desk.reply_to(
                    "How much is a water heater replacement?",
                    base_url=self.site.base,
                    writer=bad_price,
                )
                self.assertEqual(rejected, callback)
                self.assertNotIn("$1,200", rejected)
                self.assertEqual(
                    price_reply.checked_answer(
                        "A water heater is $1499.",
                        base_url=self.site.base,
                    ),
                    callback,
                )
                kept = front_desk.reply_to(
                    "How much is a drain cleaning?",
                    base_url=self.site.base,
                )
                self.assertEqual(kept, "A drain cleaning is $149. From Pricing.")
                self.assertNotEqual(kept, callback)
                self.assertNotEqual(kept, outage)
        finally:
            agreed.AGREEMENTS = saved_agreements
        self.assertEqual(AGREEMENTS.read_text(encoding="utf-8"), body)
        self.assertEqual(answer_reply.callback_reply(), original_callback)
        self.assertEqual(answer_reply.outage_reply(), original_outage)

    def test_a_failed_call_returns_only_the_outage_reply(self):
        """A failed call returns only the outage reply, and the note keeps the time and the kind of error."""
        self.assertEqual(self._saved_log, ROOT / "logs" / "error-notes.log")
        answer_reply.datetime = _FrozenClock
        missing = answer_reply.callback_reply()
        outage = answer_reply.outage_reply()
        key = "test-key"
        token = "maple-street-question-token"
        question = f"Are you open Saturdays? {token}"
        os.environ["ANTHROPIC_API_KEY"] = key
        self._block_network()
        pages = self._pages()
        unauthorized = urllib.error.HTTPError(
            "https://api.anthropic.com/v1/messages",
            401,
            "Unauthorized",
            hdrs=None,
            fp=io.BytesIO(f"invalid {key} {token}".encode("utf-8")),
        )
        service_down = urllib.error.HTTPError(
            "https://api.anthropic.com/v1/messages",
            503,
            "unavailable",
            hdrs=None,
            fp=io.BytesIO(token.encode("utf-8")),
        )
        cases = (
            (TimeoutError(f"timed out {token} {key}"), "timeout"),
            (unauthorized, "key missing or expired"),
            (service_down, "Claude is down"),
            (urllib.error.URLError(f"network down {token} {key}"), "Claude is down"),
            (RuntimeError(f"boom {token} {key}"), "call failed"),
        )

        def raising(error):
            def client(payload):
                self.assertIn(token, payload["messages"][0]["content"])
                self.assertNotIn(key, json.dumps(payload))
                raise error

            return client

        def empty(payload):
            self.assertIn(token, payload["messages"][0]["content"])
            self.assertNotIn(key, json.dumps(payload))
            return {"content": [{"type": "thinking", "thinking": f"{token} {key}"}]}

        with self.assertLogs(level="WARNING") as logged:
            for error, kind in cases:
                got = front_desk.reply_to(question, base_url=self.site.base, client=raising(error))
                self.assertEqual(got, outage, kind)
                self.assertNotEqual(got, missing, kind)
                self.assertNotIn(token, got, kind)
                self.assertNotIn(key, got, kind)
                self.assertNotIn(kind, got, kind)
                written = answer_reply.write_answer(question, pages, client=raising(error))
                self.assertEqual(written, outage, kind)
            got = front_desk.reply_to(question, base_url=self.site.base, client=empty)
            self.assertEqual(got, outage)
            self.assertNotEqual(got, missing)

            def boom(payload, header_key, timeout):
                self.assertEqual(header_key, key)
                self.assertIn(token, payload["messages"][0]["content"])
                self.assertNotIn(key, json.dumps(payload))
                raise TimeoutError(token)

            answer_reply._post_message = boom
            shown = demo_chat.safe_reply(question, self.site.base)
            self.assertEqual(shown, outage)
            self.assertNotEqual(shown, missing)
            self.assertNotIn(token, shown)
            self.assertNotIn(key, shown)

        warning_text = "\n".join(logged.output)
        self.assertNotIn(token, warning_text)
        self.assertNotIn(key, warning_text)
        self.assertNotIn("Traceback", warning_text)
        self.assertNotIn("Unauthorized", warning_text)
        note = answer_reply.FAILURE_LOG.read_text(encoding="utf-8")
        self.assertNotIn(token, note)
        self.assertNotIn(key, note)
        self.assertNotIn(question, note)
        self.assertNotIn("Unauthorized", note)
        self.assertNotIn("timed out", note)
        self.assertNotIn(outage, note)
        self.assertNotIn(missing, note)
        lines = note.splitlines()
        expected = (
            "2026-11-07T15:30:00Z timeout",
            "2026-11-07T15:30:00Z timeout",
            "2026-11-07T15:30:00Z key missing or expired",
            "2026-11-07T15:30:00Z key missing or expired",
            "2026-11-07T15:30:00Z Claude is down",
            "2026-11-07T15:30:00Z Claude is down",
            "2026-11-07T15:30:00Z Claude is down",
            "2026-11-07T15:30:00Z Claude is down",
            "2026-11-07T15:30:00Z call failed",
            "2026-11-07T15:30:00Z call failed",
            "2026-11-07T15:30:00Z empty reply",
            "2026-11-07T15:30:00Z timeout",
        )
        self.assertEqual(lines, list(expected))
        urgent = front_desk.reply_to("I have a burst pipe", base_url=self.site.base, client=raising(TimeoutError(token)))
        self.assertEqual(urgent, urgent_reply.fixed_urgent_reply())
        self.assertEqual(answer_reply.FAILURE_LOG.read_text(encoding="utf-8"), note)
        priced = "Sorry, the lookup is down. A visit is $1,200."
        original = answer_reply.outage_reply

        def pricey(text=None):
            return priced

        answer_reply.outage_reply = pricey
        try:
            def client(_payload):
                raise TimeoutError(token)

            with self.assertLogs(level="WARNING"):
                got = front_desk.reply_to(
                    "Are you open Saturdays?",
                    base_url=self.site.base,
                    client=client,
                )
        finally:
            answer_reply.outage_reply = original
        self.assertEqual(got, priced)
        self.assertNotEqual(got, missing)
        self.assertNotIn("$1,200", missing)
        self.assertNotIn(token, got)
        self.assertNotIn(key, got)
        saved = answer_reply.FAILURE_LOG.read_text(encoding="utf-8")
        self.assertNotIn(token, saved)
        self.assertNotIn(key, saved)
        self.assertNotIn(priced, saved)
        self.assertTrue(saved.startswith(note))
        self.assertTrue(saved.endswith("2026-11-07T15:30:00Z timeout\n"))

if __name__ == "__main__":
    unittest.main()
