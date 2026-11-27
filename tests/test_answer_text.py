"""Tests for shared wording, wrapping, and a fact-first reply.

Run this area with
python3 scripts/run_checks.py tests/test_answer_text.py.
"""

import contextlib
import io
import os
import re
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
import price_reply
import serve_sample_site
import urgent_reply
from answer_support import (
    ROOT,
    RunningSite,
    _SavedEnv,
    _wrapped_forms,
)


class FactFirstChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def test_a_how_question_does_not_start_with_yes(self):
        """A how question does not start with Yes. A yes or no question still does."""
        question = "How do I book a visit for Saturday morning?"
        expected = (
            "We're open Saturdays from 8:00 am to 12:00 pm. "
            "To book, call our main line at 030 0000 0000. "
            "From Hours & FAQ and Contact."
        )
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        self.assertIn("starts with the fact", behaviour)
        self.assertIn("yes or no question", behaviour)
        got = front_desk.reply_to(question, base_url=self.site.base)
        self.assertEqual(got, expected)
        self.assertFalse(re.match(r"(?i)yes\b", got))
        self.assertFalse(got.startswith("Yes"))
        saturday = front_desk.reply_to("Are you open on Saturday?", base_url=self.site.base)
        self.assertIn("Yes, we are open Saturdays.", saturday)
        self.assertTrue(saturday.endswith("From Hours & FAQ."))
        self.assertNotEqual(saturday, answer_reply.callback_reply())
        agreed = front_desk.reply_to("Are you open Saturdays?", base_url=self.site.base)
        self.assertEqual(agreed, saturday)
        drafted = (
            "Yes, we're open Saturdays from 8:00 am to 12:00 pm. "
            "To book, call our main line at 030 0000 0000. "
            "From Hours & FAQ and Contact."
        )

        def writer(question_arg, instructions_arg, pages_arg):
            if question_arg.startswith("How"):
                return drafted
            return "Yes, we are open Saturdays. From Hours & FAQ."

        rewritten = front_desk.reply_to(question, base_url=self.site.base, writer=writer)
        self.assertEqual(rewritten, expected)
        self.assertFalse(rewritten.startswith("Yes"))
        kept = front_desk.reply_to(
            "Are you open on Saturday?",
            base_url=self.site.base,
            writer=writer,
        )
        self.assertTrue(kept.startswith("Yes"))


class WrappedQuestionChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def test_a_wrapped_question_matches_the_plain_one(self):
        """A question in quotes or markdown gets the same reply as the plain question."""
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        callback = answer_reply.callback_reply()
        cases = (
            "Are you open Saturdays?",
            "How much is a drain cleaning?",
            "Do you clean drains?",
            "How much is a call-out?",
            "Can I get same-day service?",
        )
        for plain in cases:
            expected = front_desk.reply_to(plain, base_url=self.site.base)
            self.assertNotEqual(expected, callback, plain)
            self.assertNotEqual(expected, urgent_reply.fixed_urgent_reply(), plain)
            for wrapped in _wrapped_forms(plain):
                got = front_desk.reply_to(wrapped, base_url=self.site.base)
                self.assertEqual(got, expected, wrapped)
        saturday = front_desk.reply_to(
            "Are you open Saturdays?",
            base_url=self.site.base,
        )
        self.assertTrue(saturday.endswith("From Hours & FAQ."))
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = front_desk.main(['"Are you open Saturdays?"', self.site.base])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), saturday + "\n")
        drain = front_desk.reply_to(
            "How much is a drain cleaning?",
            base_url=self.site.base,
        )
        self.assertIn("$149", drain)
        self.assertTrue(drain.endswith("From Pricing."))
        call_out = front_desk.reply_to("How much is a call-out?", base_url=self.site.base)
        self.assertIn("call-out", call_out)
        self.assertIn("$99", call_out)
        same_day = front_desk.reply_to(
            "Can I get same-day service?",
            base_url=self.site.base,
        )
        self.assertIn("same-day", same_day)

    def test_wrapping_does_not_change_urgent_or_price_safety(self):
        """Quotes and markdown do not weaken an urgent word or a price."""
        urgent = urgent_reply.fixed_urgent_reply()
        callback = answer_reply.callback_reply()
        basement = "my basement has water everywhere"
        self.assertEqual(front_desk.reply_to(basement), urgent)
        for wrapped in _wrapped_forms(basement):
            self.assertEqual(urgent_reply.reply_if_urgent(wrapped), urgent, wrapped)
            self.assertEqual(front_desk.reply_to(wrapped), urgent, wrapped)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = urgent_reply.main(['"my basement has water everywhere?"'])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), urgent + "\n")
        for message in (
            "I have a leaky faucet",
            '"I have a leaky faucet"',
            "I have a leaky faucet?",
            "**I have a leaky faucet**",
            "frozen pipes",
            '"frozen pipes?"',
            "no-heat",
            '"no-heat"',
            "leak_2",
            "_leak_",
            "_water everywhere_",
        ):
            self.assertIsNone(urgent_reply.reply_if_urgent(message), message)
            self.assertNotEqual(
                front_desk.reply_to(message, base_url=self.site.base),
                urgent,
                message,
            )
        self.assertEqual(urgent_reply.reply_if_urgent('"no heat"'), urgent)
        self.assertEqual(
            price_reply.service_words('"How much is a call-out?"'),
            price_reply.service_words("How much is a call-out?"),
        )
        self.assertIn("call-out", price_reply.service_words("How much is a call-out?"))
        self.assertIn("same-day", price_reply.service_words("Can I get same-day service?"))
        kept = "A drain cleaning is $149."
        for question in (
            "How much is a drain cleaning?",
            '"How much is a drain cleaning?"',
        ):
            got = front_desk.reply_to(
                question,
                base_url=self.site.base,
                writer=lambda question, instructions, pages: kept,
            )
            self.assertEqual(got, kept, question)
        invented = "A water heater replacement is $1,200."
        decimal = "A drain cleaning is $149.00."
        self.assertEqual(price_reply.find_amounts(decimal), ["$149.00"])
        self.assertNotIn("$149.00", price_reply.published_amounts(self.site.base))
        for question in (
            "How much is a drain cleaning?",
            '"How much is a drain cleaning?"',
            "**How much is a drain cleaning?**",
        ):
            for answer in (invented, decimal):
                got = front_desk.reply_to(
                    question,
                    base_url=self.site.base,
                    writer=lambda question, instructions, pages, answer=answer: answer,
                )
                self.assertEqual(got, callback, (question, answer))
                self.assertNotIn("$1,200", got)
                self.assertNotIn("$149.00", got)
        other_service = front_desk.reply_to(
            '"How much is a call-out?"',
            base_url=self.site.base,
            writer=lambda question, instructions, pages: kept,
        )
        self.assertEqual(other_service, callback)
        seen = {}

        def remember(question, instructions, pages):
            seen["question"] = question
            return decimal

        mixed = '"How much is a call-out? $149.00"'
        got = front_desk.reply_to(mixed, base_url=self.site.base, writer=remember)
        self.assertEqual(got, callback)
        self.assertEqual(seen["question"], mixed)
        self.assertIn("$149.00", seen["question"])
        self.assertIn("call-out", seen["question"])
        self.assertIn("-", seen["question"])
        self.assertEqual(price_reply.find_amounts(seen["question"]), ["$149.00"])
        self.assertIn("call-out", price_reply.service_words(seen["question"]))


if __name__ == "__main__":
    unittest.main()
