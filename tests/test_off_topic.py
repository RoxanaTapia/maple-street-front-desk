"""Checks that an unrelated question gets the friendly reply.

OffTopicReplyChecks is the "Off-topic questions get the friendly reply" area.
The off-topic reply and the callback reply are read from your agreements.
The page text is what the page reader returns. A check sends the message
through the front desk and compares the reply. The docstring of each
test is what the checklist prints.

Run this area with
python3 scripts/run_checks.py tests/test_off_topic.py:OffTopicReplyChecks.
"""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import answer_reply
import demo_chat
import front_desk
import read_pages
import serve_sample_site
import urgent_reply

# The sentence the owner chose. The code reads it from the agreements.
OFF_TOPIC = "I can help with Maple Street\u2019s plumbing services. What do you need help with?"


class _SavedEnv:
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


class OffTopicReplyChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()
        self._post = answer_reply._post_message
        self._saved_log = answer_reply.FAILURE_LOG
        self._log_dir = tempfile.TemporaryDirectory()
        answer_reply.FAILURE_LOG = Path(self._log_dir.name) / "claude-failures.log"

    def tearDown(self):
        answer_reply._post_message = self._post
        answer_reply.FAILURE_LOG = self._saved_log
        self._log_dir.cleanup()
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def _reply(self, message, **kwargs):
        return front_desk.reply_to(message, base_url=self.site.base, **kwargs)

    def test_the_agreements_hold_the_friendly_reply(self):
        """The agreements hold the friendly off-topic reply, and the code reads it from there."""
        friendly = answer_reply.off_topic_reply()
        callback = answer_reply.callback_reply()
        self.assertEqual(friendly, OFF_TOPIC)
        self.assertNotEqual(friendly, callback)
        self.assertNotIn("$", friendly)
        sample = "## Off-topic questions\n\n> Ask about the pipes.\n"
        self.assertEqual(answer_reply.off_topic_reply(sample), "Ask about the pipes.")
        pages = read_pages.read_pages(self.site.base)
        self.assertEqual(
            answer_reply.write_answer("Do you sell pizza?", pages, text=sample),
            "Ask about the pipes.",
        )
        for name in (
            "answer_reply.py",
            "front_desk.py",
            "price_reply.py",
            "demo_chat.py",
            "urgent_reply.py",
        ):
            source = (SCRIPTS / name).read_text(encoding="utf-8")
            self.assertNotIn(OFF_TOPIC, source, name)
            self.assertNotIn(callback, source, name)
        for path in (
            ROOT / "docs" / "behaviour.md",
            ROOT / "docs" / "how-it-works.md",
            ROOT / "README.md",
            ROOT / "docs" / "setup-guide.md",
        ):
            self.assertNotIn(OFF_TOPIC, path.read_text(encoding="utf-8"), path.name)
            self.assertNotIn(callback, path.read_text(encoding="utf-8"), path.name)

    def test_an_unrelated_question_gets_the_friendly_reply(self):
        """Do you sell pizza gets the friendly reply, and the model is not called."""
        friendly = answer_reply.off_topic_reply()
        callback = answer_reply.callback_reply()
        called = {"writer": 0, "client": 0, "post": 0}

        def writer(question, instructions, pages):
            called["writer"] += 1
            return "CUSTOM"

        def client(payload):
            called["client"] += 1
            raise AssertionError("the model was called")

        def post(*_args, **_kwargs):
            called["post"] += 1
            raise AssertionError("the API was called")

        answer_reply._post_message = post
        os.environ["ANTHROPIC_API_KEY"] = "test-key-should-not-be-sent"
        for message in (
            "Do you sell pizza?",
            "do you sell pizza",
            "DO YOU SELL PIZZA?",
            "Do you sell pizza on Saturday?",
            "Do you sell pizzas on Saturdays?",
            "What's the weather today?",
            "What's the weather during your hours?",
            "Do you sell pizza when you are open?",
            "How much is a pizza?",
            "Can you recommend a movie?",
        ):
            got = self._reply(message, writer=writer, client=client)
            self.assertEqual(got, friendly, message)
            self.assertNotEqual(got, callback, message)
            self.assertNotIn("From ", got, message)
            written = answer_reply.write_answer(
                message,
                read_pages.read_pages(self.site.base),
                writer=writer,
                client=client,
            )
            self.assertEqual(written, friendly, message)
        self.assertEqual(called, {"writer": 0, "client": 0, "post": 0})
        self.assertFalse(answer_reply.FAILURE_LOG.exists())

    def test_a_missing_plumbing_fact_keeps_the_callback(self):
        """A plumbing question the pages don't answer keeps the callback reply."""
        friendly = answer_reply.off_topic_reply()
        callback = answer_reply.callback_reply()
        missing = (
            "Do you cover Moorestown?",
            "How much is a water heater replacement?",
            "How long is your warranty?",
            "Do you repair garbage disposals?",
            "I have a leaky faucet",
            "My tap is dripping.",
            "Do you accept credit cards?",
            "Can you replace a bidet?",
            "The aerator won't unscrew.",
        )
        for message in missing:
            self.assertIsNone(urgent_reply.reply_if_urgent(message), message)
            got = self._reply(message)
            self.assertEqual(got, callback, message)
            self.assertNotEqual(got, friendly, message)
        saturday = self._reply("Are you open Saturdays?")
        self.assertTrue(saturday.endswith("From Hours & FAQ."))
        self.assertNotEqual(saturday, callback)
        self.assertNotEqual(saturday, friendly)
        drain = self._reply("How much is a drain cleaning?")
        self.assertIn("$149", drain)
        self.assertTrue(drain.endswith("From Pricing."))
        self.assertNotEqual(drain, callback)
        self.assertNotEqual(drain, friendly)

    def test_an_unknown_question_still_reaches_the_answer_path(self):
        """A dripping tap, a card payment, and an unfamiliar job are still sent on."""
        friendly = answer_reply.off_topic_reply()
        seen = []

        def client(payload):
            seen.append(payload["messages"][0]["content"])
            return {"content": [{"type": "text", "text": "We can look that up."}]}

        def writer(question, instructions, pages):
            raise AssertionError("the writer ran for a clearly unrelated question")

        for message in (
            "My tap is dripping.",
            "Do you accept credit cards?",
            "Can you replace a bidet?",
        ):
            before = len(seen)
            got = self._reply(message, client=client)
            self.assertEqual(len(seen), before + 1, message)
            self.assertIn(message, seen[-1])
            self.assertNotEqual(got, friendly, message)
            self.assertNotIn("From ", got)
        pizza = "Do you sell pizza on Saturday?"
        got = self._reply(pizza, writer=writer, client=client)
        self.assertEqual(got, friendly)
        self.assertEqual(len(seen), 3)
        mixed = self._reply("Do you sell pizza and my tap is dripping?")
        self.assertEqual(mixed, answer_reply.callback_reply())
        self.assertNotEqual(mixed, friendly)

    def test_the_demo_http_matches_the_front_desk(self):
        """The demo HTTP reply matches the front desk for a tap, a payment, and pizza on Saturday."""
        friendly = answer_reply.off_topic_reply()
        callback = answer_reply.callback_reply()
        demo = demo_chat.make_server("127.0.0.1", 0, self.site.base)
        thread = threading.Thread(target=demo.serve_forever, daemon=True)
        thread.start()
        host, port = demo.server_address[:2]
        url = f"http://{host}:{port}/reply"
        cases = {
            "Do you sell pizza on Saturday?": friendly,
            "What's the weather during your hours?": friendly,
            "My tap is dripping.": callback,
            "Do you accept credit cards?": callback,
            "Can you replace a bidet?": callback,
        }
        try:
            for message, expected in cases.items():
                self.assertEqual(self._reply(message), expected, message)
                data = json.dumps({"message": message}).encode("utf-8")
                request = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    self.assertEqual(response.status, 200, message)
                    body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(body, {"reply": expected}, message)
        finally:
            demo.shutdown()
            demo.server_close()
            thread.join(timeout=2)

    def test_an_urgent_message_still_stops_first(self):
        """An urgent message still gets the call-now reply, even when it also mentions pizza."""
        called = {"pages": 0}
        original = read_pages.read_pages

        def boom(_base):
            called["pages"] += 1
            raise AssertionError("pages were read for an urgent message")

        read_pages.read_pages = boom
        try:
            got = front_desk.reply_to("I have a burst pipe. Do you sell pizza?")
        finally:
            read_pages.read_pages = original
        self.assertEqual(got, urgent_reply.fixed_urgent_reply())
        self.assertNotEqual(got, answer_reply.off_topic_reply())
        self.assertEqual(called["pages"], 0)

    def test_a_failed_plumbing_question_still_uses_the_callback_and_the_note(self):
        """A failed call for a plumbing question gets the outage reply and the owner note."""
        friendly = answer_reply.off_topic_reply()
        callback = answer_reply.callback_reply()
        outage = answer_reply.outage_reply()
        self.assertEqual(self._saved_log, ROOT / "logs" / "claude-failures.log")
        question = "How long is your warranty?"
        called = {"client": 0}

        def client(payload):
            called["client"] += 1
            self.assertIn(question, payload["messages"][0]["content"])
            raise TimeoutError("timed out")

        got = self._reply(question, client=client)
        self.assertEqual(called["client"], 1)
        self.assertEqual(got, outage)
        self.assertNotEqual(got, callback)
        self.assertNotEqual(got, friendly)
        note = answer_reply.FAILURE_LOG.read_text(encoding="utf-8")
        self.assertNotIn(question, note)
        self.assertNotIn("test-key", note)
        self.assertTrue(note.endswith(" timeout\n") or note.endswith("timeout\n"))
        self.assertIn("timeout", note.splitlines()[-1])

        def refused(_payload):
            called["client"] += 1
            raise AssertionError("an off-topic question must not call the model")

        before = note
        pizza = self._reply("Do you sell pizza?", client=refused)
        self.assertEqual(pizza, friendly)
        self.assertEqual(called["client"], 1)
        self.assertEqual(answer_reply.FAILURE_LOG.read_text(encoding="utf-8"), before)
