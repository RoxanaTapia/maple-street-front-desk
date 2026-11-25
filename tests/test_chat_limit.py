"""Checks for the public chat's daily limit.

ChatLimitChecks is the "The daily chat limit holds" area.
A message under the cap may reach the AI. At the cap, the visitor
gets a friendly note and the AI is not called. The count starts again
on the next Berlin day. The docstring of each test is what the
checklist prints.

Run one area with
python3 scripts/run_checks.py tests/test_chat_limit.py:ChatLimitChecks.
"""

import contextlib
import io
import json
import os
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import answer_reply
import chat_limit
import demo_chat
import front_desk
import serve_sample_site
import urgent_reply

BERLIN = ZoneInfo("Europe/Berlin")
HOURS = "What are your hours?"
SECRET = "test-key-for-the-daily-limit-check"


class _SavedEnv:
    def __init__(self):
        self.values = {
            name: os.environ.pop(name, None)
            for name in (
                "ANTHROPIC_API_KEY",
                "CLAUDE_MODEL",
                "DEMO_HOST",
                "DEMO_PORT",
                "CHAT_DAILY_LIMIT",
                "CHAT_VISITOR_DAILY_LIMIT",
            )
        }

    def restore(self):
        for name, value in self.values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class RunningDemo:
    def __init__(self):
        serve_sample_site.pricing_live = True
        self.site = serve_sample_site.make_server(serve_sample_site.DEFAULT_HOST, 0)
        self.site_thread = threading.Thread(target=self.site.serve_forever, daemon=True)
        self.site_thread.start()
        site_host, site_port = self.site.server_address[:2]
        self.base = f"http://{site_host}:{site_port}"
        self._wait(self.base + "/")
        self.demo = demo_chat.make_server("127.0.0.1", 0, self.base)
        self.demo_thread = threading.Thread(target=self.demo.serve_forever, daemon=True)
        self.demo_thread.start()
        host, port = self.demo.server_address[:2]
        self.url = f"http://{host}:{port}"
        self._wait(self.url + "/")

    def _wait(self, url):
        deadline = time.time() + 3
        last_error = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=0.5) as response:
                    response.read()
                    if response.status == 200:
                        return
            except Exception as error:
                last_error = error
                time.sleep(0.02)
        raise AssertionError(f"demo did not start: {last_error}")

    def close(self):
        self.demo.shutdown()
        self.demo.server_close()
        self.demo_thread.join(timeout=2)
        self.site.shutdown()
        self.site.server_close()
        self.site_thread.join(timeout=2)

    def post(self, message, headers=None):
        data = json.dumps({"message": message}).encode("utf-8")
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(
            self.url + "/reply",
            data=data,
            headers=request_headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                raw = response.read().decode("utf-8")
                return response.status, raw, json.loads(raw)
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return error.code, raw, parsed


class ChatLimitChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self._post = answer_reply._post_message
        chat_limit.clock = None
        chat_limit.reset()
        self.demo = RunningDemo()
        self.called = {"n": 0}

    def tearDown(self):
        answer_reply._post_message = self._post
        chat_limit.clock = None
        chat_limit.reset()
        demo = getattr(self, "demo", None)
        if demo is not None:
            demo.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def _caps(self, daily, visitor):
        os.environ["CHAT_DAILY_LIMIT"] = str(daily)
        os.environ["CHAT_VISITOR_DAILY_LIMIT"] = str(visitor)

    def _arm_model(self):
        expected = front_desk.reply_to(HOURS, base_url=self.demo.base)
        self.assertNotEqual(expected, chat_limit.busy_reply())
        os.environ["ANTHROPIC_API_KEY"] = SECRET

        def fake(payload, key, timeout):
            self.called["n"] += 1
            self.assertEqual(key, SECRET)
            self.assertNotIn(SECRET, json.dumps(payload))
            return {"content": [{"type": "text", "text": expected}]}

        answer_reply._post_message = fake
        return expected

    def _reply(self, message, headers=None):
        status, raw, parsed = self.demo.post(message, headers=headers)
        self.assertEqual(status, 200, message)
        self.assertEqual(parsed, {"reply": parsed.get("reply")}, message)
        self.assertNotIn(SECRET, raw)
        self.assertNotIn("<", raw)
        return parsed["reply"]

    def test_under_the_limit_the_model_is_called(self):
        """Under the daily limit, a public chat message calls the model."""
        self._caps(2, 0)
        expected = self._arm_model()
        first = self._reply(HOURS)
        second = self._reply(HOURS)
        self.assertEqual(first, expected)
        self.assertEqual(second, expected)
        self.assertEqual(self.called["n"], 2)
        self.assertNotEqual(first, chat_limit.busy_reply())

    def test_at_the_limit_the_visitor_gets_a_friendly_message(self):
        """At the daily limit, the visitor gets a friendly message and the model is not called."""
        self._caps(1, 0)
        expected = self._arm_model()
        answered = self._reply(HOURS)
        self.assertEqual(answered, expected)
        self.assertEqual(self.called["n"], 1)
        blocked = self._reply(HOURS)
        self.assertEqual(blocked, chat_limit.busy_reply())
        self.assertIn("roxanatapia.dev", blocked)
        self.assertIn("tomorrow", blocked)
        self.assertIn("book a call", blocked)
        self.assertNotEqual(blocked, answer_reply.outage_reply())
        self.assertNotEqual(blocked, answer_reply.callback_reply())
        self.assertEqual(self.called["n"], 1)
        seen = {"n": 0}

        def client(_payload):
            seen["n"] += 1
            return {"content": [{"type": "text", "text": expected}]}

        local = front_desk.reply_to(HOURS, base_url=self.demo.base, client=client)
        self.assertEqual(seen["n"], 1)
        self.assertEqual(local, expected)
        self.assertEqual(self.called["n"], 1)

    def test_an_urgent_message_is_still_answered_at_the_limit(self):
        """An urgent message still gets the fixed reply when the daily limit is reached."""
        self._caps(1, 0)
        self._arm_model()
        self._reply(HOURS)
        self.assertEqual(self.called["n"], 1)
        urgent = urgent_reply.fixed_urgent_reply()
        got = self._reply("I have a burst pipe")
        self.assertEqual(got, urgent)
        self.assertEqual(self.called["n"], 1)
        blocked = self._reply(HOURS)
        self.assertEqual(blocked, chat_limit.busy_reply())
        self.assertEqual(self.called["n"], 1)

    def test_a_question_the_ai_is_not_asked_does_not_use_the_day(self):
        """A question the AI is not asked does not use up the daily limit."""
        self._caps(1, 0)
        expected = self._arm_model()
        for _ in range(3):
            got = self._reply("Do you sell pizza?")
            self.assertEqual(got, answer_reply.off_topic_reply())
        self.assertEqual(self.called["n"], 0)
        answered = self._reply(HOURS)
        self.assertEqual(answered, expected)
        self.assertEqual(self.called["n"], 1)

    def test_the_count_resets_on_the_next_berlin_day(self):
        """The count resets on the next Berlin day, and the model is called again."""
        self._caps(1, 0)
        expected = self._arm_model()
        self.now = [datetime(2026, 11, 25, 23, 30, tzinfo=BERLIN)]
        chat_limit.clock = lambda: self.now[0]
        chat_limit.reset()
        first = self._reply(HOURS)
        self.assertEqual(first, expected)
        self.assertEqual(self.called["n"], 1)
        self.now[0] = datetime(2026, 11, 25, 23, 50, tzinfo=BERLIN)
        later = self._reply(HOURS)
        self.assertEqual(later, chat_limit.busy_reply())
        self.assertEqual(self.called["n"], 1)
        self.now[0] = datetime(2026, 11, 26, 0, 10, tzinfo=BERLIN)
        again = self._reply(HOURS)
        self.assertEqual(again, expected)
        self.assertEqual(self.called["n"], 2)

    def test_one_visitor_can_reach_a_cap_while_another_has_not(self):
        """One visitor can reach a daily cap while another visitor has not."""
        self._caps(10, 1)
        expected = self._arm_model()
        first_visitor = {"X-Forwarded-For": "203.0.113.1, 10.0.0.1"}
        second_visitor = {"X-Forwarded-For": "203.0.113.2"}
        opened = self._reply(HOURS, headers=first_visitor)
        self.assertEqual(opened, expected)
        blocked = self._reply(HOURS, headers=first_visitor)
        self.assertEqual(blocked, chat_limit.busy_reply())
        other = self._reply(HOURS, headers=second_visitor)
        self.assertEqual(other, expected)
        self.assertEqual(self.called["n"], 2)
        direct = self._reply(HOURS)
        self.assertEqual(direct, expected)
        again = self._reply(HOURS)
        self.assertEqual(again, chat_limit.busy_reply())
        self.assertEqual(self.called["n"], 3)

    def test_the_limits_are_written_down(self):
        """The daily limits are written down, with the defaults and the Berlin day."""
        self.assertEqual(chat_limit.limits(), (200, 20))
        self.assertEqual(chat_limit.DEFAULT_DAILY_LIMIT, 200)
        self.assertEqual(chat_limit.DEFAULT_VISITOR_LIMIT, 20)
        os.environ["CHAT_DAILY_LIMIT"] = "0"
        os.environ["CHAT_VISITOR_DAILY_LIMIT"] = "0"
        self.assertEqual(chat_limit.limits(), (0, 0))
        chat_limit.reset()
        with chat_limit.public_chat("203.0.113.9"):
            self.assertTrue(chat_limit.allow_model_call())
            self.assertTrue(chat_limit.allow_model_call())
        os.environ["CHAT_DAILY_LIMIT"] = "1"
        os.environ["CHAT_VISITOR_DAILY_LIMIT"] = "0"
        chat_limit.reset()
        self.assertTrue(chat_limit.allow_model_call())
        with chat_limit.public_chat("203.0.113.8"):
            self.assertTrue(chat_limit.allow_model_call())
            self.assertFalse(chat_limit.allow_model_call())
        os.environ["CHAT_DAILY_LIMIT"] = "many"
        with self.assertRaises(ValueError):
            chat_limit.limits()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(demo_chat.main([]), 1)
        self.assertIn("CHAT_DAILY_LIMIT", err.getvalue())
        os.environ.pop("CHAT_DAILY_LIMIT", None)
        os.environ.pop("CHAT_VISITOR_DAILY_LIMIT", None)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(chat_limit.main([]), 0)
        printed = out.getvalue()
        self.assertIn("200", printed)
        self.assertIn("20", printed)
        self.assertIn("Berlin", printed)
        self.assertIn("memory", printed)
        self.assertIn(chat_limit.busy_reply(), printed)
        self.assertNotIn("—", chat_limit.busy_reply())
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        how = (ROOT / "docs" / "how-it-works.md").read_text(encoding="utf-8")
        for text, name in (
            (readme, "README.md"),
            (example, ".env.example"),
            (how, "docs/how-it-works.md"),
        ):
            self.assertIn("CHAT_DAILY_LIMIT", text, name)
            self.assertIn("CHAT_VISITOR_DAILY_LIMIT", text, name)
            self.assertIn("200", text, name)
            self.assertIn("20", text, name)
            self.assertIn("Berlin", text, name)
            self.assertIn("memory", text, name)
        self.assertIn("book a call on roxanatapia.dev", behaviour)
        self.assertIn("The AI is not called", behaviour)
        self.assertIn("fixed urgent reply", behaviour)
        self.assertIn("scripts/chat_limit.py", how)
