"""Tests for opening hours and a Saturday booking.

Run this area with
python3 scripts/run_checks.py tests/test_answer_hours.py.
"""

import os
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
import read_pages
import serve_sample_site
import urgent_reply
from answer_support import (
    AGREEMENTS,
    ROOT,
    RunningSite,
    _SavedEnv,
    page_named,
    question_rows,
)


class HoursFaqAnswerChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def test_questions_13_to_15_come_from_hours_and_faq(self):
        """Questions 13 to 15 are answered from the Hours & FAQ page,
        and the after-hours question is not urgent.
        """
        rows = {row["number"]: row for row in question_rows()}
        callback = answer_reply.callback_reply()
        urgent = urgent_reply.fixed_urgent_reply()
        expected = {
            13: "No, we don't install or service septic systems. From Hours & FAQ.",
            14: "Yes, we're fully licensed and insured in New Jersey. From Hours & FAQ.",
            15: (
                "Yes, we handle emergencies after hours too. "
                "Just call our main line at 030 0000 0000. From Hours & FAQ."
            ),
        }
        agreements = AGREEMENTS.read_text(encoding="utf-8")
        self.assertNotIn("Yours to decide", agreements)
        self.assertNotIn("Waiting for the Hours & FAQ page", agreements)
        pages = read_pages.read_pages(self.site.base)
        hours = next(page for page in pages if page["name"] == "Hours & FAQ")
        self.assertEqual(hours["status"], "read")
        page_html = (ROOT / "sample-site" / "hours.html").read_text(encoding="utf-8")
        self.assertIn("Do you install septic systems?", page_html)
        self.assertIn("Are you licensed and insured?", page_html)
        self.assertIn("Do you do after-hours emergency callouts?", page_html)
        self.assertIn("emergency", rows[15]["question"].lower())
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        for number, reply in expected.items():
            row = rows[number]
            sentence = reply.split(" From Hours & FAQ.", 1)[0]
            self.assertEqual(row["group"], "Answered by your pages", number)
            self.assertEqual(page_named(row["detail"]), "Hours & FAQ", number)
            self.assertIn(sentence, hours["text"], number)
            self.assertIn(sentence, page_html, number)
            self.assertIsNone(urgent_reply.reply_if_urgent(row["question"]), row["question"])
            got = front_desk.reply_to(row["question"], base_url=self.site.base)
            self.assertEqual(got, reply, row["question"])
            self.assertEqual(
                answer_reply.write_answer(row["question"], pages),
                reply,
                row["question"],
            )
            self.assertNotEqual(got, callback, row["question"])
            self.assertNotEqual(got, urgent, row["question"])
            self.assertTrue(got.endswith("From Hours & FAQ."), row["question"])


class SaturdayBookingChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def test_a_saturday_booking_names_hours_and_contact(self):
        """How do I book a visit for Saturday morning names Hours & FAQ and Contact."""
        question = "How do I book a visit for Saturday morning?"
        expected = (
            "We're open Saturdays from 8:00 am to 12:00 pm. "
            "To book, call our main line at 030 0000 0000. "
            "From Hours & FAQ and Contact."
        )
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        self.assertIn("names every page it used", behaviour)
        pages = read_pages.read_pages(self.site.base)
        hours = next(page for page in pages if page["name"] == "Hours & FAQ")
        contact = next(page for page in pages if page["name"] == "Contact")
        self.assertEqual(hours["status"], "read")
        self.assertEqual(contact["status"], "read")
        self.assertIn("8:00 am to 12:00 pm", hours["text"])
        self.assertIn("open Saturdays", hours["text"])
        self.assertIn("book", contact["text"].lower())
        self.assertIn("030 0000 0000", contact["text"])
        self.assertIsNone(urgent_reply.reply_if_urgent(question))
        got = front_desk.reply_to(question, base_url=self.site.base)
        self.assertEqual(got, expected)
        self.assertEqual(answer_reply.write_answer(question, pages), expected)
        self.assertTrue(got.endswith("From Hours & FAQ and Contact."))
        self.assertNotEqual(got, answer_reply.callback_reply())
        saturday = front_desk.reply_to("Are you open Saturdays?", base_url=self.site.base)
        self.assertTrue(saturday.endswith("From Hours & FAQ."))
        self.assertNotIn("Contact", saturday)
        booking = front_desk.reply_to(
            "How do I book or cancel an appointment?",
            base_url=self.site.base,
        )
        self.assertTrue(booking.endswith("From Contact."))
        self.assertNotIn("Hours & FAQ", booking)
        instructions = answer_reply.build_instructions(question, pages)
        self.assertIn("From Hours & FAQ and Contact.", instructions)
        self.assertIn("name every page", instructions.casefold())
        buggy = (
            "Yes, we're open Saturdays from 8:00 am to 12:00 pm. "
            "To book, call our main line at 030 0000 0000. From Contact."
        )

        def writer(question_arg, instructions_arg, pages_arg):
            return buggy

        self.assertEqual(
            front_desk.reply_to(question, base_url=self.site.base, writer=writer),
            expected,
        )
        self.assertEqual(answer_reply.write_answer(question, pages, writer=writer), expected)


if __name__ == "__main__":
    unittest.main()
