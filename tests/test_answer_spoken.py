"""Tests that a price is spoken to the customer.

Run this area with
python3 scripts/run_checks.py tests/test_answer_spoken.py.
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

class MisspellingAndPlainPriceChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def test_a_misspelling_and_a_plain_price_are_answered(self):
        """A misspelled service gets its price, and a price with no dollar sign is checked."""
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        callback = answer_reply.callback_reply()
        pages = read_pages.read_pages(self.site.base)
        rows = question_rows()
        self.assertEqual([row["number"] for row in rows], list(range(1, 29)))
        spelled = "How much is a drain cleaning?"
        misspelled = "How much is a drane cleaning?"
        plain = "Is drain cleaning 149?"
        drain_price = "A drain cleaning is $149. From Pricing."
        plain_yes = "Yes, a drain cleaning is $149. From Pricing."
        drane = next(row for row in rows if row["question"] == misspelled)
        stated = next(row for row in rows if row["question"] == plain)
        self.assertEqual(drane["number"], 17)
        self.assertEqual(stated["number"], 18)
        self.assertEqual(drane["group"], "Answered by your pages")
        self.assertEqual(stated["group"], "Answered by your pages")
        self.assertEqual(page_named(drane["detail"]), "Pricing")
        self.assertEqual(page_named(stated["detail"]), "Pricing")
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        self.assertIn("small misspelling", behaviour.lower())
        self.assertIn("without a dollar sign", behaviour.lower())
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("18 agreed questions", readme)
        self.assertIn("18 test questions", readme)

        spelled_reply = front_desk.reply_to(spelled, base_url=self.site.base)
        self.assertEqual(spelled_reply, drain_price)
        got = front_desk.reply_to(misspelled, base_url=self.site.base)
        written = answer_reply.write_answer(misspelled, pages)
        self.assertEqual(got, drain_price)
        self.assertEqual(written, drain_price)
        self.assertEqual(got, spelled_reply)
        self.assertNotIn("the customer", got.casefold())
        self.assertNotIn("drane", got.casefold())
        self.assertTrue(got.endswith("From Pricing."))
        slipped = front_desk.reply_to("How much is a drayn cleaning?", base_url=self.site.base)
        self.assertEqual(slipped, drain_price)
        self.assertNotEqual(slipped, callback)

        yes = front_desk.reply_to(plain, base_url=self.site.base)
        self.assertEqual(yes, plain_yes)
        self.assertEqual(answer_reply.write_answer(plain, pages), plain_yes)
        self.assertNotIn("the customer", yes.casefold())
        self.assertNotEqual(yes, callback)
        self.assertIn("$149", yes)
        dollars = front_desk.reply_to("Is drain cleaning 149 dollars?", base_url=self.site.base)
        self.assertEqual(dollars, plain_yes)
        self.assertNotIn("the customer", dollars.casefold())

        def narrate(question_arg, instructions, pages_arg):
            return (
                'The customer says $149, which matches the Pricing page, '
                'but they wrote "149" without a dollar sign. '
                "The answer is yes, and the price is $149. From Pricing."
            )

        spoken = front_desk.reply_to(plain, base_url=self.site.base, writer=narrate)
        self.assertEqual(spoken, plain_yes)
        self.assertNotIn("the customer", spoken.casefold())

        def client_narrate(_payload):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "The customer says $149, but they left off the dollar sign. "
                            "The price is $149. From Pricing."
                        ),
                    }
                ]
            }

        via_call = front_desk.reply_to(plain, base_url=self.site.base, client=client_narrate)
        self.assertEqual(via_call, plain_yes)
        self.assertNotIn("the customer", via_call.casefold())

        instructions = answer_reply.build_instructions(plain, pages)
        self.assertIn(answer_reply.MISSPELLED_SERVICE, instructions)
        self.assertIn(answer_reply.PLAIN_PRICE, instructions)
        self.assertIn("do not mention the customer", instructions.lower())

        self.assertEqual(price_reply.find_amounts("A drain cleaning is 150."), ["150"])
        self.assertEqual(
            price_reply.find_amounts("A drain cleaning is 150 dollars."),
            ["150 dollars"],
        )
        self.assertEqual(price_reply.find_amounts("A drain cleaning is $149."), ["$149"])
        self.assertEqual(price_reply.find_amounts("We're at 149 Maple Street"), [])
        self.assertEqual(price_reply.find_amounts("Call us at 030 0000 0000."), [])
        self.assertEqual(price_reply.find_amounts("Saturday: 8:00 am to 12:00 pm."), [])
        for answer in (
            "A drain cleaning is 150.",
            "A drain cleaning is 150 dollars.",
            "Yes, it is 150.",
            "Yes, a drain cleaning is 149.",
        ):
            got = price_reply.checked_answer(
                answer,
                base_url=self.site.base,
                message=spelled,
            )
            self.assertEqual(got, callback, answer)
            self.assertNotIn("150", got, answer)
            self.assertNotIn("$149", got, answer)

        def wrong_bare(question_arg, instructions, pages_arg):
            return "Yes, a drain cleaning is 150."

        rejected = front_desk.reply_to(plain, base_url=self.site.base, writer=wrong_bare)
        self.assertEqual(rejected, callback)
        self.assertNotIn("150", rejected)
        self.assertNotIn("$149", rejected)

        def wrong_dollars(question_arg, instructions, pages_arg):
            return "Yes, a drain cleaning is 150 dollars."

        rejected_words = front_desk.reply_to(plain, base_url=self.site.base, writer=wrong_dollars)
        self.assertEqual(rejected_words, callback)
        self.assertNotIn("150", rejected_words)

        def agree(question_arg, instructions, pages_arg):
            return "Yes, the customer is right, it is 150."

        agreed = front_desk.reply_to(plain, base_url=self.site.base, writer=agree)
        self.assertEqual(agreed, callback)
        self.assertNotIn("150", agreed)
        self.assertNotIn("$149", agreed)
        self.assertNotIn("the customer", agreed.casefold())

        def other_service(question_arg, instructions, pages_arg):
            return "The call-out fee is $99. From Services."

        swapped = front_desk.reply_to(misspelled, base_url=self.site.base, writer=other_service)
        self.assertEqual(swapped, callback)
        self.assertNotIn("$99", swapped)
        self.assertTrue(
            price_reply.price_is_near_service(
                "A drain cleaning is $149.",
                "$149",
                ["drane", "cleaning"],
            )
        )
        kept = front_desk.reply_to(
            spelled,
            base_url=self.site.base,
            writer=lambda question_arg, instructions, pages_arg: drain_price,
        )
        self.assertEqual(kept, drain_price)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = front_desk.main([misspelled, self.site.base])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), drain_price + "\n")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = price_reply.main(
                ["--asked", spelled, "A drain cleaning is 150.", self.site.base]
            )
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), callback + "\n")

if __name__ == "__main__":
    unittest.main()
