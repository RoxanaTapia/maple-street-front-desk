"""Tests for the note written when a call fails.

Run this area with
python3 scripts/run_checks.py tests/test_answer_notes.py.
"""

import io
import json
import os
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

import answer_reply
import front_desk
import serve_sample_site
import urgent_reply
from answer_support import (
    ROOT,
    RunningSite,
    _SavedEnv,
)


class FailureNoteChecks(unittest.TestCase):
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

    def _block_network(self):
        def fail(*_args, **_kwargs):
            raise AssertionError("the real API was called")

        answer_reply._post_message = fail

    def test_a_failed_call_is_noted_and_the_outage_reply_is_used(self):
        """A failed call gets the outage reply,
        and a note records the time and the kind of error.
        """
        callback = answer_reply.callback_reply()
        outage = answer_reply.outage_reply()
        self.assertNotEqual(outage, callback)
        key = "test-key"
        token = "maple-street-question-token"
        question = f"Are you open Saturdays? {token}"
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "setup-guide.md").read_text(encoding="utf-8")
        notes = (ROOT / "docs" / "developer-guide.md").read_text(encoding="utf-8")
        self.assertEqual(self._saved_log, ROOT / "logs" / "error-notes.log")
        self.assertTrue(any(line.strip() == "logs/" for line in ignore.splitlines()))
        self.assertIn("logs/error-notes.log", notes)
        self.assertNotIn("sk-ant-", guide)
        self.assertNotIn(key, guide)
        self.assertNotIn("sk-ant-", notes)
        self.assertNotIn(key, notes)

        self._block_network()
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        ordinary = front_desk.reply_to("Are you open Saturdays?", base_url=self.site.base)
        self.assertIn("From Hours & FAQ.", ordinary)
        self.assertNotEqual(ordinary, callback)
        self.assertNotEqual(ordinary, outage)
        self.assertFalse(answer_reply.FAILURE_LOG.exists())

        os.environ["ANTHROPIC_API_KEY"] = key

        def client_down(_payload):
            raise TimeoutError(token)

        urgent = front_desk.reply_to(
            "I have a burst pipe",
            base_url=self.site.base,
            client=client_down,
        )
        self.assertEqual(urgent, urgent_reply.fixed_urgent_reply())
        self.assertFalse(answer_reply.FAILURE_LOG.exists())

        def client_ok(payload):
            self.assertIn("Are you open Saturdays?", payload["messages"][0]["content"])
            self.assertNotIn(key, json.dumps(payload))
            return {
                "content": [
                    {"type": "text", "text": "Yes, we are open Saturdays. From Hours & FAQ."}
                ]
            }

        answered = front_desk.reply_to(
            "Are you open Saturdays?",
            base_url=self.site.base,
            client=client_ok,
        )
        self.assertNotEqual(answered, callback)
        self.assertNotEqual(answered, outage)
        self.assertNotIn(key, answered)
        self.assertFalse(answer_reply.FAILURE_LOG.exists())

        unauthorized = urllib.error.HTTPError(
            "https://api.anthropic.com/v1/messages",
            401,
            "Unauthorized",
            hdrs=None,
            fp=io.BytesIO(f"invalid {key} {token}".encode("utf-8")),
        )
        cases = (
            (TimeoutError(f"timed out {token} {key}"), "timeout"),
            (unauthorized, "key missing or expired"),
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

        started = datetime.now(timezone.utc)
        with self.assertLogs(level="WARNING") as logged:
            for error, kind in cases:
                got = front_desk.reply_to(question, base_url=self.site.base, client=raising(error))
                self.assertEqual(got, outage)
                self.assertNotEqual(got, callback)
                self.assertNotIn(token, got)
                self.assertNotIn(key, got)
                self.assertNotIn(kind, got)
            got = front_desk.reply_to(question, base_url=self.site.base, client=empty)
            self.assertEqual(got, outage)
            self.assertNotEqual(got, callback)
            self.assertNotIn(token, got)
            self.assertNotIn(key, got)
        self.assertEqual(
            [record.getMessage() for record in logged.records],
            [
                "Claude could not answer (timeout).",
                "Claude could not answer (key missing or expired).",
                "Claude could not answer (Claude is down).",
                "Claude could not answer (call failed).",
                "Claude could not answer (empty reply).",
            ],
        )
        warning_text = "\n".join(logged.output)
        self.assertNotIn(token, warning_text)
        self.assertNotIn(key, warning_text)
        self.assertNotIn("Traceback", warning_text)

        note = answer_reply.FAILURE_LOG.read_text(encoding="utf-8")
        self.assertTrue(note.endswith("\n"))
        self.assertNotIn("\n\n", note)
        self.assertNotIn(token, note)
        self.assertNotIn(key, note)
        self.assertNotIn(question, note)
        self.assertNotIn("Unauthorized", note)
        self.assertNotIn("timed out", note)
        self.assertNotIn("Traceback", note)
        lines = note.splitlines()
        expected = (
            "timeout",
            "key missing or expired",
            "Claude is down",
            "call failed",
            "empty reply",
        )
        self.assertEqual(len(lines), len(expected))
        for line, kind in zip(lines, expected):
            stamp, found = line.split(" ", 1)
            self.assertEqual(found, kind)
            seen = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            self.assertGreaterEqual(seen, started.replace(microsecond=0))
            self.assertLessEqual((datetime.now(timezone.utc) - seen).total_seconds(), 120)

        again = front_desk.reply_to(
            "Are you open Saturdays?",
            base_url=self.site.base,
            client=client_ok,
        )
        self.assertNotEqual(again, callback)
        self.assertNotEqual(again, outage)
        self.assertEqual(answer_reply.FAILURE_LOG.read_text(encoding="utf-8"), note)


if __name__ == "__main__":
    unittest.main()
