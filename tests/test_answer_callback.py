"""Tests for a reply when the pages don't list the answer.

Run this area with
python3 scripts/run_checks.py tests/test_answer_callback.py.
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

class UncoveredQuestionChecks(unittest.TestCase):
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

    def test_a_question_the_pages_dont_cover_gets_the_callback(self):
        """Every question your pages don't cover gets the callback reply."""
        rows = question_rows()
        pages = self._pages()
        callback = self._callback()
        urgent_reply_text = urgent_reply.fixed_urgent_reply()
        self.assertNotEqual(callback, urgent_reply_text)
        uncovered = []
        for row in rows:
            if row["group"] == "Answered by your pages":
                continue
            if urgent_reply.reply_if_urgent(row["question"]) is not None:
                continue
            uncovered.append(row)
        self.assertEqual(
            [row["number"] for row in uncovered if "callback" in row["detail"].lower()],
            [11, 12, 26, 27],
        )
        for row in uncovered:
            self.assertIsNone(page_named(row["detail"]), row["question"])
            if "callback" not in row["detail"].lower():
                continue
            got = front_desk.reply_to(row["question"], base_url=self.site.base)
            self.assertEqual(got, callback, row["question"])
            self.assertEqual(
                answer_reply.write_answer(row["question"], pages),
                callback,
                row["question"],
            )
        self.assertEqual(
            answer_reply.write_answer("How long is your warranty?", pages),
            callback,
        )
        services = next(page for page in pages if page["name"] == "Services")
        missing = []
        for page in pages:
            if page["name"] == "Services":
                missing.append(
                    {
                        "name": page["name"],
                        "title": "",
                        "text": "",
                        "status": "unreadable",
                        "reason": "HTTP 503",
                    }
                )
            else:
                missing.append(page)
        tankless = next(row["question"] for row in rows if "tankless" in row["question"].lower())
        self.assertEqual(answer_reply.write_answer(tankless, missing), callback)
        self.assertIn("tankless", services["text"].lower())

class MissingFactChecks(unittest.TestCase):
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

    def test_a_missing_fact_returns_only_the_call_to_confirm(self):
        """A missing fact returns only the call-to-confirm reply, and no failure note is written."""
        self._block_network()
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        missing = answer_reply.callback_reply()
        outage = answer_reply.outage_reply()
        pages = self._pages()
        for question in (
            "Do you cover Moorestown?",
            "How much is a water heater replacement?",
            "How long is your warranty?",
        ):
            got = front_desk.reply_to(question, base_url=self.site.base)
            self.assertEqual(got, missing, question)
            self.assertNotEqual(got, outage, question)
            self.assertEqual(answer_reply.write_answer(question, pages), missing, question)
        pizza = "Do you sell pizza?"
        got = front_desk.reply_to(pizza, base_url=self.site.base)
        self.assertEqual(got, answer_reply.off_topic_reply())
        self.assertNotEqual(got, missing)
        self.assertNotEqual(got, outage)
        self.assertEqual(
            answer_reply.write_answer(pizza, pages),
            answer_reply.off_topic_reply(),
        )
        self.assertFalse(answer_reply.FAILURE_LOG.exists())
        drain = front_desk.reply_to("How much is a drain cleaning?", base_url=self.site.base)
        self.assertEqual(drain, "A drain cleaning is $149. From Pricing.")
        self.assertNotEqual(drain, missing)
        self.assertNotEqual(drain, outage)
        urgent = front_desk.reply_to("I have a burst pipe", base_url=self.site.base)
        self.assertEqual(urgent, urgent_reply.fixed_urgent_reply())
        self.assertNotEqual(urgent, outage)
        self.assertFalse(answer_reply.FAILURE_LOG.exists())

        def wrong_service(payload):
            self.assertIn("Page: Services", payload["messages"][0]["content"])
            self.assertNotIn(outage, payload["messages"][0]["content"])
            return {"content": [{"type": "text", "text": "The call-out fee is $99."}]}

        swapped = front_desk.reply_to(
            "How much is a drain cleaning?",
            base_url=self.site.base,
            client=wrong_service,
        )
        self.assertEqual(swapped, missing)
        self.assertNotEqual(swapped, outage)
        self.assertNotIn("$99", swapped)
        self.assertFalse(answer_reply.FAILURE_LOG.exists())

        def right_price(_payload):
            return {"content": [{"type": "text", "text": "A drain cleaning is $149. From Pricing."}]}

        kept = front_desk.reply_to(
            "How much is a drain cleaning?",
            base_url=self.site.base,
            client=right_price,
        )
        self.assertEqual(kept, "A drain cleaning is $149. From Pricing.")
        self.assertFalse(answer_reply.FAILURE_LOG.exists())

class UnlistedServiceChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def test_a_service_the_pages_never_mention_gets_the_callback(self):
        """A service the pages never mention says so, and gives the call-us number."""
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        callback = answer_reply.callback_reply()
        friendly = answer_reply.off_topic_reply()
        urgent = urgent_reply.fixed_urgent_reply()
        self.assertNotEqual(callback, friendly)
        self.assertNotEqual(callback, urgent)
        pages = read_pages.read_pages(self.site.base)
        joined = " ".join(page.get("text") or "" for page in pages).casefold()
        unlisted = answer_reply.unlisted_service_reply()
        self.assertNotEqual(unlisted, callback)
        for question in (
            "Do you repair garbage disposals?",
            "Do you install solar panels?",
            "Can you replace a bidet?",
        ):
            self.assertNotIn(question.split()[-1].rstrip("?").casefold(), joined, question)
            self.assertIsNone(urgent_reply.reply_if_urgent(question), question)
            got = front_desk.reply_to(question, base_url=self.site.base)
            self.assertEqual(got, unlisted, question)
            self.assertEqual(answer_reply.write_answer(question, pages), unlisted, question)
            self.assertNotIn("$", got, question)
            self.assertIn("don't list", got.lower(), question)
            self.assertNotEqual(got, friendly, question)
            self.assertNotEqual(got, urgent, question)
            self.assertNotEqual(got, callback, question)
        priced = front_desk.reply_to("Do you clean drains?", base_url=self.site.base)
        self.assertNotEqual(priced, callback)
        self.assertIn("$149", priced)
        without_price = []
        for page in pages:
            if page["name"] == "Pricing":
                without_price.append({**page, "text": "Call for a quote."})
            else:
                without_price.append(page)
        self.assertEqual(
            answer_reply.write_answer("Do you clean drains?", without_price),
            answer_reply.unlisted_service_reply(),
        )
        self.assertNotIn("$149", "Call for a quote.")

class MisspelledLeakChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def test_a_misspelled_faucet_price_uses_the_leak_reply(self):
        """A misspelled faucet price question gets the leak reply, with no price."""
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        self.assertIn("faucet problem", behaviour.lower())
        self.assertIn("small misspelling of that problem", behaviour.lower())
        callback = answer_reply.callback_reply()
        urgent = urgent_reply.fixed_urgent_reply()
        leak_reply = f"The pages don't list a price for a leak. {callback}"
        spelled = "how much do u charge for a leaky faucet"
        misspelled = "how much do u charge for a leeky faucet"
        self.assertIsNone(urgent_reply.reply_if_urgent(spelled))
        self.assertIsNone(urgent_reply.reply_if_urgent(misspelled))
        called = {"writer": 0}

        def writer(question, instructions, pages):
            called["writer"] += 1
            return "A leaky faucet is $40."

        for question in (
            spelled,
            misspelled,
            "HOW MUCH DO U CHARGE FOR A LEEKY FAUCET",
            "how much do u charge for a leeky faucet???",
            "what do you charge for a leeky faucet",
        ):
            got = front_desk.reply_to(question, base_url=self.site.base, writer=writer)
            self.assertEqual(got, leak_reply, question)
            self.assertIn("leak", got.casefold(), question)
            self.assertNotIn("leek", got.casefold(), question)
            self.assertNotIn("$", got, question)
            self.assertEqual(price_reply.find_amounts(got), [], question)
            self.assertIn("030 0000 0000", got, question)
            self.assertNotEqual(got, callback, question)
            self.assertNotEqual(got, urgent, question)
        self.assertEqual(called["writer"], 0)
        pages = read_pages.read_pages(self.site.base)
        self.assertEqual(answer_reply.write_answer(misspelled, pages), leak_reply)
        self.assertEqual(answer_reply.write_answer(spelled, pages), leak_reply)
        self.assertNotIn("faucet", " ".join(page.get("text") or "" for page in pages).casefold())
        stated = "I have a leaky faucet"
        slipped = "I have a leeky faucet"
        self.assertEqual(front_desk.reply_to(stated, base_url=self.site.base), callback)
        self.assertEqual(front_desk.reply_to(slipped, base_url=self.site.base), callback)
        self.assertIsNone(urgent_reply.reply_if_urgent(stated))
        self.assertIsNone(urgent_reply.reply_if_urgent(slipped))
        drain = front_desk.reply_to("How much is a drain cleaning?", base_url=self.site.base)
        self.assertEqual(drain, "A drain cleaning is $149. From Pricing.")
        priced = []
        for page in pages:
            if page["name"] == "Pricing":
                priced.append({**page, "text": page["text"] + " A leaky faucet repair is $75."})
            else:
                priced.append(page)
        listed = answer_reply.write_answer(misspelled, priced)
        self.assertIn("$75", listed)
        self.assertNotIn("don't list a price", listed.lower())
        self.assertTrue(listed.endswith("From Pricing."))

    def test_a_leak_slip_matches_the_urgent_spelling_only(self):
        """A slip of an urgent leak spelling gets the urgent reply, and a near miss does not."""
        urgent = urgent_reply.fixed_urgent_reply()
        leak = front_desk.reply_to("I have a leak under the sink")
        leaking = front_desk.reply_to("The pipe is leaking")
        self.assertEqual(leak, urgent)
        self.assertEqual(leaking, urgent)
        for message in (
            "I have a leek under the sink",
            "how much do u charge for a leek",
            "The pipe is leeking",
            "The pipe is leakng",
            "The pipe is leakin",
            "The pipe is leakign",
            "The pipe is leaaking",
        ):
            self.assertEqual(urgent_reply.reply_if_urgent(message), urgent, message)
            self.assertEqual(front_desk.reply_to(message), urgent, message)
        self.assertEqual(
            front_desk.reply_to("I have a leek under the sink"),
            leak,
        )
        self.assertEqual(front_desk.reply_to("The pipe is leeking"), leaking)
        for message in (
            "leakx",
            "xleak",
            "leakingx",
            "xleaking",
            "I have leaks",
            "The faucet is sleek",
            "How much is a weekly drain cleaning?",
            "I have a leaky faucet",
            "how much do u charge for a leeky faucet",
        ):
            self.assertIsNone(urgent_reply.reply_if_urgent(message), message)
        weekly = front_desk.reply_to(
            "How much is a weekly drain cleaning?",
            base_url=self.site.base,
        )
        self.assertNotIn("don't list a price for a leak", weekly.lower())

    def test_a_non_leak_question_is_unaffected(self):
        """A question that is not about a leak keeps its usual reply."""
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        callback = answer_reply.callback_reply()
        urgent = urgent_reply.fixed_urgent_reply()
        leak_reply = f"The pages don't list a price for a leak. {callback}"
        drain = "How much is a drain cleaning?"
        got = front_desk.reply_to(drain, base_url=self.site.base)
        self.assertEqual(got, "A drain cleaning is $149. From Pricing.")
        self.assertIsNone(urgent_reply.reply_if_urgent(drain))
        self.assertNotIn("leak", got.casefold())
        hours = "Are you open Saturdays?"
        got = front_desk.reply_to(hours, base_url=self.site.base)
        self.assertEqual(
            got,
            "Saturday: 8:00 am to 12:00 pm. Yes, we are open Saturdays. From Hours & FAQ.",
        )
        self.assertIsNone(urgent_reply.reply_if_urgent(hours))
        for question in (
            "how much do u charge for a sleek faucet",
            "The faucet is sleek",
            "The pipe is speaking",
            "How much is a weekly drain cleaning?",
        ):
            got = front_desk.reply_to(question, base_url=self.site.base)
            self.assertEqual(got, callback, question)
            self.assertNotEqual(got, leak_reply, question)
            self.assertNotEqual(got, urgent, question)
            self.assertIsNone(urgent_reply.reply_if_urgent(question), question)
            self.assertNotIn("$", got, question)
            self.assertNotIn("don't list a price for a leak", got.lower(), question)

if __name__ == "__main__":
    unittest.main()
