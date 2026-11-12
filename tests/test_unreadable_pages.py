"""Checks that a page that can't be read is noted for the owner.

UnreadablePageNoteChecks is the "A page that can't be read is noted
for the owner" area. Pricing is switched off, the note is written once,
and the replies stay the same. The same page is noted again only after
an hour. A different page is noted on its own.

Run this area with
python3 scripts/run_checks.py tests/test_unreadable_pages.py:UnreadablePageNoteChecks
"""

import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import answer_reply
import front_desk
import read_pages
import serve_sample_site
import urgent_reply

STAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class RunningSite:
    def __init__(self):
        serve_sample_site.pricing_live = True
        self.httpd = serve_sample_site.make_server("127.0.0.1", 0)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        deadline = time.time() + 3
        last_error = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(self.base + "/", timeout=0.5) as response:
                    response.read()
                    if response.status == 200:
                        return
            except Exception as error:
                last_error = error
                time.sleep(0.02)
        raise AssertionError(f"sample site did not start: {last_error}")

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)


class _SavedEnv:
    """Keep a developer key from turning the checks into a live call."""

    def __init__(self):
        self.key = os.environ.pop("ANTHROPIC_API_KEY", None)
        self.model = os.environ.pop("CLAUDE_MODEL", None)

    def restore(self):
        if self.key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = self.key
        if self.model is None:
            os.environ.pop("CLAUDE_MODEL", None)
        else:
            os.environ["CLAUDE_MODEL"] = self.model


class UnreadablePageNoteChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()
        self._saved_log = answer_reply.FAILURE_LOG
        self._log_dir = tempfile.TemporaryDirectory()
        answer_reply.FAILURE_LOG = Path(self._log_dir.name) / "error-notes.log"

    def tearDown(self):
        answer_reply.FAILURE_LOG = self._saved_log
        self._log_dir.cleanup()
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def _lines(self):
        if not answer_reply.FAILURE_LOG.exists():
            return []
        text = answer_reply.FAILURE_LOG.read_text(encoding="utf-8")
        self.assertTrue(text.endswith("\n"))
        self.assertNotIn("\n\n", text)
        return text.splitlines()

    def _restamp(self, when):
        lines = []
        for line in self._lines():
            _stamp, _, rest = line.partition(" ")
            lines.append(f"{when.strftime(STAMP_FORMAT)} {rest}")
        answer_reply.FAILURE_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _detail(self, line):
        _stamp, _, rest = line.partition(" ")
        return rest

    def test_a_down_page_is_noted_once_and_the_replies_stay_the_same(self):
        """A down page is noted once, and the replies stay the same."""
        self.assertEqual(self._saved_log, ROOT / "logs" / "error-notes.log")
        self.assertEqual(answer_reply.PAGE_NOTE_WINDOW, timedelta(hours=1))
        callback = answer_reply.callback_reply()
        outage = answer_reply.outage_reply()
        friendly = answer_reply.off_topic_reply()
        urgent = urgent_reply.fixed_urgent_reply()
        self.assertNotEqual(callback, outage)
        saturday = "Are you open Saturdays?"
        drain = "How much is a drain cleaning?"
        wrong = "A drain cleaning is 200?"
        token = "maple-customer-token"
        personal = f"How much is a drain cleaning, {token}?"
        saturday_live = front_desk.reply_to(saturday, base_url=self.site.base)
        drain_live = front_desk.reply_to(drain, base_url=self.site.base)
        self.assertIn("From Hours & FAQ.", saturday_live)
        self.assertNotEqual(saturday_live, callback)
        self.assertNotEqual(drain_live, callback)
        self.assertFalse(answer_reply.FAILURE_LOG.exists())

        serve_sample_site.pricing_live = False
        pages = read_pages.read_pages(self.site.base)
        pricing = next(page for page in pages if page["name"] == "Pricing")
        self.assertEqual(pricing["status"], "unreadable")
        self.assertIn("503", pricing["reason"])
        self.assertFalse(answer_reply.FAILURE_LOG.exists())

        got = front_desk.reply_to("I have a burst pipe", base_url=self.site.base)
        self.assertEqual(got, urgent)
        self.assertFalse(answer_reply.FAILURE_LOG.exists())

        started = datetime.now(timezone.utc).replace(microsecond=0)
        with self.assertLogs(level="WARNING") as logged:
            cases = (
                (drain, callback),
                (wrong, callback),
                (saturday, saturday_live),
                (personal, callback),
                ("Do you sell pizza?", friendly),
                (drain, callback),
                (wrong, callback),
                (saturday, saturday_live),
            )
            for message, expected in cases:
                got = front_desk.reply_to(message, base_url=self.site.base)
                self.assertEqual(got, expected, message)
                self.assertNotEqual(got, outage, message)
                self.assertNotIn(token, got)
        self.assertEqual(len(logged.records), 1)
        warning = logged.records[0].getMessage()
        self.assertIn("Pricing", warning)
        self.assertIn("503", warning)
        self.assertNotIn(token, warning)
        self.assertNotIn(drain, warning)
        self.assertNotIn(wrong, warning)
        self.assertNotIn(saturday, warning)

        lines = self._lines()
        self.assertEqual(len(lines), 1)
        stamp, _, detail = lines[0].partition(" ")
        self.assertEqual(detail, f"Pricing: {pricing['reason']}")
        seen = datetime.strptime(stamp, STAMP_FORMAT).replace(tzinfo=timezone.utc)
        self.assertGreaterEqual(seen, started)
        self.assertLessEqual((datetime.now(timezone.utc) - seen).total_seconds(), 120)
        note = answer_reply.FAILURE_LOG.read_text(encoding="utf-8")
        for hidden in (
            token,
            drain,
            wrong,
            saturday,
            personal,
            "200",
            callback,
            saturday_live,
            outage,
            pricing["address"],
        ):
            self.assertNotIn(hidden, note, hidden)

    def test_the_same_page_is_noted_once_an_hour(self):
        """The same page is noted once an hour, and a different page is noted on its own."""
        self.assertEqual(answer_reply.PAGE_NOTE_WINDOW, timedelta(hours=1))
        callback = answer_reply.callback_reply()
        drain = "How much is a drain cleaning?"
        saturday = "Are you open Saturdays?"
        serve_sample_site.pricing_live = False
        with self.assertLogs(level="WARNING"):
            self.assertEqual(front_desk.reply_to(drain, base_url=self.site.base), callback)
        self.assertEqual(len(self._lines()), 1)
        first = self._detail(self._lines()[0])
        self.assertTrue(first.startswith("Pricing: "))

        saturday_answer = front_desk.reply_to(saturday, base_url=self.site.base)
        self.assertIn("From Hours & FAQ.", saturday_answer)
        self.assertNotEqual(saturday_answer, callback)
        self.assertEqual(len(self._lines()), 1)

        aged = datetime.now(timezone.utc) - timedelta(minutes=30)
        self._restamp(aged)
        self.assertEqual(front_desk.reply_to(drain, base_url=self.site.base), callback)
        lines = self._lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].split(" ", 1)[0], aged.strftime(STAMP_FORMAT))
        self.assertEqual(self._detail(lines[0]), first)

        pages = read_pages.read_pages(self.site.base)
        changed = []
        for page in pages:
            if page["name"] == "Pricing":
                changed.append({**page, "reason": "connection refused"})
            else:
                changed.append(page)
        before = answer_reply.FAILURE_LOG.read_text(encoding="utf-8")
        self.assertEqual(answer_reply.write_answer(drain, changed), callback)
        self.assertEqual(answer_reply.FAILURE_LOG.read_text(encoding="utf-8"), before)
        self.assertNotIn("connection refused", before)

        self._restamp(datetime.now(timezone.utc) - timedelta(hours=2))
        wrong = "A drain cleaning is 200?"
        with self.assertLogs(level="WARNING") as logged:
            self.assertEqual(front_desk.reply_to(wrong, base_url=self.site.base), callback)
        self.assertEqual(len(logged.records), 1)
        self.assertNotIn(wrong, logged.records[0].getMessage())
        lines = self._lines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(self._detail(lines[0]), first)
        self.assertEqual(self._detail(lines[1]), first)
        self.assertNotIn("200", answer_reply.FAILURE_LOG.read_text(encoding="utf-8"))

        contact_down = []
        for page in pages:
            if page["name"] == "Contact":
                contact_down.append(
                    {
                        **page,
                        "status": "unreadable",
                        "title": "",
                        "text": "",
                        "reason": "HTTP 503",
                    }
                )
            else:
                contact_down.append(page)
        with self.assertLogs(level="WARNING") as logged:
            got = answer_reply.write_answer(saturday, contact_down)
        self.assertEqual(got, saturday_answer)
        self.assertEqual(len(logged.records), 1)
        self.assertIn("Contact", logged.records[0].getMessage())
        self.assertNotIn(saturday, logged.records[0].getMessage())
        lines = self._lines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(self._detail(lines[2]), "Contact: HTTP 503")

        hours_down = []
        for page in pages:
            if page["name"] == "Hours & FAQ":
                hours_down.append(
                    {
                        **page,
                        "status": "unreadable",
                        "title": "",
                        "text": "",
                        "reason": "HTTP 404",
                    }
                )
            else:
                hours_down.append(page)
        with self.assertLogs(level="WARNING") as logged:
            got = answer_reply.write_answer(saturday, hours_down)
        self.assertEqual(got, callback)
        self.assertEqual(len(logged.records), 1)
        self.assertIn("Hours & FAQ", logged.records[0].getMessage())
        self.assertNotIn(saturday, logged.records[0].getMessage())
        matches = [line for line in self._lines() if self._detail(line).startswith("Hours & FAQ: ")]
        self.assertEqual(matches, [line for line in self._lines() if "Hours & FAQ:" in line])
        self.assertEqual(len(matches), 1)
        self.assertEqual(self._detail(matches[0]), "Hours & FAQ: HTTP 404")
        again = answer_reply.write_answer(saturday, hours_down)
        self.assertEqual(again, callback)
        self.assertEqual(
            [line for line in self._lines() if self._detail(line).startswith("Hours & FAQ: ")],
            matches,
        )
        note = answer_reply.FAILURE_LOG.read_text(encoding="utf-8")
        self.assertNotIn(saturday, note)
        self.assertNotIn(drain, note)
        self.assertNotIn(wrong, note)


if __name__ == "__main__":
    unittest.main()
