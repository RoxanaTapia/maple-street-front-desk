"""Tests that a price on the pages is offered.

Run this area with
python3 scripts/run_checks.py tests/test_answer_prices.py.
"""

import contextlib
import io
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
import price_reply
import read_pages
import serve_sample_site
import urgent_reply
from answer_support import (
    ROOT,
    RunningSite,
    _SavedEnv,
    page_named,
    question_rows,
)


class PricedServiceChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def test_a_priced_service_is_offered(self):
        """A service with a price on the pages gets a yes, the price, and the page."""
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        question = "Do you clean drains?"
        expected = "Yes, we do drain cleaning. It's $149. From Pricing."
        callback = answer_reply.callback_reply()
        rows = question_rows()
        row = next(item for item in rows if item["question"] == question)
        self.assertEqual(row["number"], 16)
        self.assertEqual(row["group"], "Answered by your pages")
        self.assertEqual(page_named(row["detail"]), "Pricing")
        self.assertIn("$149", row["detail"])
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        self.assertIn("A question about a service that has a price on the pages", behaviour)
        self.assertIn("says yes", behaviour.lower())
        pages = read_pages.read_pages(self.site.base)
        pricing = next(page for page in pages if page["name"] == "Pricing")
        self.assertEqual(pricing["status"], "read")
        self.assertIn("A drain cleaning is $149.", pricing["text"])
        self.assertTrue(
            price_reply.price_is_near_service(pricing["text"], "$149", ["clean", "drains"])
        )
        self.assertFalse(
            price_reply.price_is_near_service(pricing["text"], "$149", ["garbage", "disposals"])
        )
        self.assertIsNone(urgent_reply.reply_if_urgent(question))
        got = front_desk.reply_to(question, base_url=self.site.base)
        written = answer_reply.write_answer(question, pages)
        self.assertEqual(got, expected)
        self.assertEqual(written, expected)
        self.assertNotEqual(got, callback)
        self.assertNotEqual(got, urgent_reply.fixed_urgent_reply())
        self.assertTrue(got.endswith("From Pricing."))
        self.assertIn("$149", got)
        self.assertNotIn("$99", got)
        self.assertNotIn("the customer", got.casefold())
        for wrapped in (f'"{question}"', f"**{question}**", f"{question}?"):
            self.assertEqual(
                front_desk.reply_to(wrapped, base_url=self.site.base),
                expected,
                wrapped,
            )
        same = front_desk.reply_to("Do you clean the drains?", base_url=self.site.base)
        self.assertEqual(same, expected)
        can = front_desk.reply_to("Can you clean drains?", base_url=self.site.base)
        self.assertEqual(can, expected)
        price_question = front_desk.reply_to(
            "How much is a drain cleaning?",
            base_url=self.site.base,
        )
        self.assertEqual(price_question, "A drain cleaning is $149. From Pricing.")
        septic = front_desk.reply_to(
            "Do you install septic systems?",
            base_url=self.site.base,
        )
        self.assertEqual(
            septic,
            "No, we don't install or service septic systems. From Hours & FAQ.",
        )
        instructions = answer_reply.build_instructions(question, pages)
        self.assertIn(answer_reply.PRICED_SERVICE_IS_OFFERED, instructions)
        self.assertIn("Say yes, include that price, and name the page.", instructions)

        def other_service(question_arg, instructions_arg, pages_arg):
            return "The call-out fee is $99. From Services."

        swapped = front_desk.reply_to(question, base_url=self.site.base, writer=other_service)
        self.assertEqual(swapped, callback)
        self.assertNotIn("$99", swapped)

        def invented(question_arg, instructions_arg, pages_arg):
            return "Yes, we do drain cleaning. It's $1,200. From Pricing."

        made_up = front_desk.reply_to(question, base_url=self.site.base, writer=invented)
        self.assertEqual(made_up, callback)
        self.assertNotIn("$1,200", made_up)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = front_desk.main([question, self.site.base])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), expected + "\n")


class InventedPriceChecks(unittest.TestCase):
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

    def test_an_invented_price_is_replaced(self):
        """An invented price from Claude is replaced by the callback reply."""
        invented = "$1,200"
        published = price_reply.published_amounts(self.site.base)
        self.assertNotIn(invented, published)
        callback = self._callback()
        seen = {"n": 0}

        def client(payload):
            seen["n"] += 1
            self.assertEqual(len(payload["messages"]), 1)
            self.assertIn("Page: Pricing", payload["messages"][0]["content"])
            return {
                "content": [{"type": "text", "text": f"A water heater replacement is {invented}."}]
            }

        self._block_network()
        got = front_desk.reply_to(
            "How much is a water heater replacement?",
            base_url=self.site.base,
            client=client,
        )
        self.assertEqual(seen["n"], 1)
        self.assertEqual(got, callback)
        self.assertNotEqual(got, answer_reply.outage_reply())
        self.assertNotIn(invented, got)

        def client_urgent(_payload):
            seen["n"] += 1
            return {"content": [{"type": "text", "text": "This should not be sent."}]}

        urgent = front_desk.reply_to("I have a burst pipe", client=client_urgent)
        self.assertEqual(urgent, urgent_reply.fixed_urgent_reply())
        self.assertEqual(seen["n"], 1)
        self.assertNotIn("$", urgent)


if __name__ == "__main__":
    unittest.main()
