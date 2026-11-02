"""Checks that a price is shown only when your pages state it.

PriceChecks is the "Prices come only from your pages" area.
LongerPriceChecks is the "A longer price isn't mistaken for a shorter one"
area. Amounts are taken from your pages as the page reader reads them.
The callback reply is read from your agreements. The docstring of
each test is what the checklist prints.

Run one area with
python3 scripts/run_checks.py tests/test_prices.py:PriceChecks
or python3 scripts/run_checks.py tests/test_prices.py:LongerPriceChecks.
"""

import contextlib
import io
import re
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import price_reply
import read_pages
import serve_sample_site
import urgent_reply

AGREEMENTS = ROOT / "docs" / "agreements.md"
GROUP_HEADING = re.compile(r"^\*\*(.+?)\*\*$")
QUESTION_LINE = re.compile(r"^(\d+)\.\s+(.+)$")


def question_rows():
    rows = []
    in_section = False
    group = None
    for line in AGREEMENTS.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if in_section:
                break
            in_section = line[3:].strip() == "The 15 test questions"
            continue
        if not in_section:
            continue
        bold = GROUP_HEADING.fullmatch(line.strip())
        if bold:
            group = bold.group(1).strip()
            continue
        match = QUESTION_LINE.match(line.strip())
        if not match or not group:
            continue
        text = match.group(2).strip()
        mark = text.find("?")
        if mark == -1:
            question, detail = text, ""
        else:
            question = text[: mark + 1].strip()
            detail = text[mark + 1 :].strip()
        rows.append({"question": question, "detail": detail, "group": group})
    return rows


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


class PriceChecks(unittest.TestCase):
    def setUp(self):
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True

    def _published(self):
        return price_reply.published_amounts(self.site.base)

    def _callback(self):
        return price_reply.callback_reply()

    def test_a_published_price_is_left_unchanged(self):
        """A price written on your pages is left as written."""
        pages = read_pages.read_pages(self.site.base)
        from_reader = []
        seen = set()
        for page in pages:
            self.assertIn("text", page)
            if page["status"] != "read":
                continue
            for amount in price_reply.find_amounts(f"{page['title']} {page['text']}"):
                if amount not in seen:
                    seen.add(amount)
                    from_reader.append(amount)
        published = self._published()
        self.assertEqual(published, from_reader)
        self.assertGreaterEqual(len(published), 1)
        for amount in published:
            answer = f"The price is {amount}."
            self.assertEqual(
                price_reply.checked_answer(answer, base_url=self.site.base),
                answer,
            )
        priced = [
            row
            for row in question_rows()
            if row["group"] == "Answered by your pages" and price_reply.find_amounts(row["detail"])
        ]
        self.assertGreaterEqual(len(priced), 1)
        for row in priced:
            for amount in price_reply.find_amounts(row["detail"]):
                self.assertIn(amount, published, row["question"])
                answer = f"{row['question']} {amount}"
                self.assertEqual(
                    price_reply.checked_answer(answer, base_url=self.site.base),
                    answer,
                )
                self.assertEqual(
                    price_reply.answer_for(row["question"], answer, base_url=self.site.base),
                    answer,
                )
        both = " and ".join(published)
        self.assertEqual(
            price_reply.checked_answer(both, base_url=self.site.base),
            both,
        )
        page = "A full replacement is $1,200. The visit is 99 dollars."
        for answer in ("A full replacement is $1,200.", "The visit is 99 dollars."):
            self.assertEqual(
                price_reply.checked_answer(answer, page_text=page),
                answer,
            )
        source = (SCRIPTS / "price_reply.py").read_text(encoding="utf-8")
        for amount in published:
            self.assertNotIn(amount, source)

    def test_an_invented_amount_is_replaced_with_the_callback(self):
        """An amount that isn't on your pages is replaced with the callback reply."""
        published = set(self._published())
        callback = self._callback()
        self.assertEqual(price_reply.find_amounts(callback), [])
        source = (SCRIPTS / "price_reply.py").read_text(encoding="utf-8")
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        self.assertNotIn(callback, source)
        self.assertNotIn(callback, behaviour)
        for banned in ("openai", "anthropic", "grok"):
            self.assertNotIn(banned, source)
        invented = [item for item in ("$1,200", "$50", "250 dollars", "$149.00") if item not in published]
        self.assertGreaterEqual(len(invented), 1)
        for amount in invented:
            answer = f"The price is {amount}."
            got = price_reply.checked_answer(answer, base_url=self.site.base)
            self.assertEqual(got, callback, answer)
            self.assertNotIn(amount, got)
        if published:
            mixed = f"The price is {next(iter(published))} or {invented[0]}."
            got = price_reply.checked_answer(mixed, base_url=self.site.base)
            self.assertEqual(got, callback)
            self.assertNotIn(invented[0], got)
        water = next(row for row in question_rows() if "water heater" in row["question"].lower())
        self.assertEqual(price_reply.find_amounts(water["detail"]), [])
        draft = f"A water heater replacement is {invented[0]}."
        self.assertEqual(
            price_reply.checked_answer(draft, base_url=self.site.base),
            callback,
        )
        self.assertEqual(
            price_reply.answer_for(water["question"], draft, base_url=self.site.base),
            callback,
        )
        page = "The visit is 99 dollars."
        self.assertEqual(
            price_reply.checked_answer("The visit is $99.", page_text=page),
            callback,
        )
        self.assertEqual(
            price_reply.checked_answer("The visit is 99 dollars.", page_text=page),
            "The visit is 99 dollars.",
        )
        sample = "## When the pages don't say\n\n> Please ask\n> the owner.\n"
        self.assertEqual(price_reply.callback_reply(sample), "Please ask the owner.")
        self.assertEqual(
            price_reply.checked_answer("It costs $5.", page_text="No prices here.", text=sample),
            "Please ask the owner.",
        )
        with self.assertRaises(ValueError):
            price_reply.checked_answer(
                "It costs $5.",
                page_text="No prices here.",
                text="## When the pages don't say\n\nNo reply here.\n",
            )
        serve_sample_site.pricing_live = False
        still_there = price_reply.published_amounts(self.site.base)
        hidden = [amount for amount in published if amount not in still_there]
        self.assertGreaterEqual(len(hidden), 1)
        for amount in hidden:
            answer = f"The price is {amount}."
            self.assertEqual(
                price_reply.checked_answer(answer, base_url=self.site.base),
                callback,
                answer,
            )

    def test_an_answer_with_no_amount_is_left_as_it_is(self):
        """An answer with no amount is left as it is."""
        callback = self._callback()
        urgent = urgent_reply.fixed_urgent_reply()
        pages = read_pages.read_pages(self.site.base)
        contact = next(page for page in pages if page["name"] == "Contact")
        self.assertEqual(price_reply.find_amounts(contact["text"]), [])
        self.assertEqual(price_reply.find_amounts(urgent), [])
        answers = [
            "Yes, we service tankless water heaters.",
            "Sunday is closed.",
            urgent,
            callback,
            contact["text"],
            "",
            "   ",
        ]
        for row in question_rows():
            if price_reply.find_amounts(row["question"]) or price_reply.find_amounts(row["detail"]):
                continue
            answers.append(row["question"])
        self.assertGreaterEqual(len(answers), 1)
        for answer in answers:
            self.assertEqual(
                price_reply.checked_answer(answer, base_url=self.site.base),
                answer,
            )
        self.assertIsNone(price_reply.checked_answer(None, base_url=self.site.base))
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = price_reply.main(["Yes, we are open Saturdays.", self.site.base])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "Yes, we are open Saturdays.\n")

    def test_an_urgent_message_is_handled_first(self):
        """An urgent message is handled first."""
        word = urgent_reply.urgent_words()[0]
        reply = urgent_reply.fixed_urgent_reply()
        published = self._published()
        self.assertGreaterEqual(len(published), 1)
        invented = "It will be $1,200."
        self.assertNotIn("$1,200", published)
        self.assertEqual(
            price_reply.checked_answer(invented, base_url=self.site.base),
            self._callback(),
        )

        def fail_if_read(base_url):
            raise AssertionError("pages were read for an urgent message")

        original = price_reply.read_pages.read_pages
        price_reply.read_pages.read_pages = fail_if_read
        try:
            got = price_reply.answer_for(
                f"We have {word}.",
                invented,
                base_url=self.site.base,
            )
        finally:
            price_reply.read_pages.read_pages = original
        self.assertEqual(got, reply)
        self.assertNotIn("$", got)
        normal = next(
            row["question"]
            for row in question_rows()
            if urgent_reply.reply_if_urgent(row["question"]) is None
        )
        self.assertEqual(
            price_reply.answer_for(normal, invented, base_url=self.site.base),
            self._callback(),
        )
        kept = f"The price is {published[0]}."
        self.assertEqual(
            price_reply.answer_for(normal, kept, base_url=self.site.base),
            kept,
        )

    def test_checking_an_answer_prints_it_or_the_callback(self):
        """Checking an answer prints it when the price is published, and the callback reply when it is not."""
        published = self._published()
        callback = self._callback()
        self.assertGreaterEqual(len(published), 1)
        answer = f"The price is {published[0]}."
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = price_reply.main([answer, self.site.base])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), answer + "\n")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = price_reply.main(["A water heater replacement is $1,200.", self.site.base])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), callback + "\n")
        self.assertNotIn("$1,200", stdout.getvalue())
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(price_reply.main(["--help"]), 2)
        self.assertIn("Usage:", stderr.getvalue())
        self.assertNotIn(callback, stderr.getvalue())
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(price_reply.main([]), 2)

    def test_you_see_this_check_on_the_pull_request(self):
        """You see this check on the pull request as Prices come only from your pages."""
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("name: Prices come only from your pages\n", workflow)
        self.assertIn("tests/test_prices.py:PriceChecks", workflow)
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        self.assertIn("**Prices come only from your pages**", behaviour)
        self.assertIn("kept only as it is written there", behaviour)
        self.assertIn("an urgent message is still handled first", behaviour)


class LongerPriceChecks(unittest.TestCase):
    def setUp(self):
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True

    def test_a_dollar_amount_is_read_whole(self):
        """A dollar amount is read whole."""
        cases = {
            "$1499": ["$1499"],
            "$1,499": ["$1,499"],
            "$149": ["$149"],
            "A drain cleaning is $149.": ["$149"],
            "A water heater is $1499.": ["$1499"],
            "A water heater replacement is $1,499.": ["$1,499"],
            "It is $1,200, please.": ["$1,200"],
            "It is $50, please.": ["$50"],
            "$149.00": ["$149.00"],
            "$99": ["$99"],
            "99 dollars": ["99 dollars"],
            "250 dollars": ["250 dollars"],
            "1,499 dollars": ["1,499 dollars"],
        }
        for text, expected in cases.items():
            self.assertEqual(price_reply.find_amounts(text), expected, text)
        self.assertNotEqual(price_reply.find_amounts("$1499"), ["$149"])
        self.assertNotEqual(price_reply.find_amounts("$1,499"), ["$1"])
        self.assertNotEqual(price_reply.find_amounts("$1,499"), ["$149"])

    def test_a_longer_price_isnt_mistaken_for_a_shorter_one(self):
        """A longer price isn't mistaken for a shorter one."""
        published = price_reply.published_amounts(self.site.base)
        callback = price_reply.callback_reply()
        self.assertEqual(callback, "I can't confirm that from your pages.")
        self.assertIn("$149", published)
        self.assertNotIn("$1499", published)
        self.assertNotIn("$1,499", published)
        answer = "A water heater is $1499."
        self.assertEqual(price_reply.find_amounts(answer), ["$1499"])
        got = price_reply.checked_answer(answer, base_url=self.site.base)
        self.assertEqual(got, callback)
        self.assertNotIn("$149", got)
        self.assertNotIn("1499", got)
        comma = "A water heater is $1,499."
        self.assertEqual(
            price_reply.checked_answer(comma, base_url=self.site.base),
            callback,
        )
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = price_reply.main([answer, self.site.base])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), callback + "\n")

    def test_a_price_at_the_end_of_a_sentence_stays_the_amount(self):
        """$149 at the end of a sentence is still $149."""
        answer = "A drain cleaning is $149."
        self.assertEqual(price_reply.find_amounts(answer), ["$149"])
        self.assertEqual(
            price_reply.checked_answer(answer, base_url=self.site.base),
            answer,
        )
        page = "A drain cleaning is $149."
        self.assertEqual(
            price_reply.checked_answer(answer, page_text=page),
            answer,
        )
        callback = price_reply.callback_reply()
        for other in (
            "A drain cleaning is $1499.",
            "A drain cleaning is $1,499.",
            "A drain cleaning is $149.00.",
            "A drain cleaning is 149 dollars.",
            "The visit is 99 dollars.",
        ):
            self.assertEqual(
                price_reply.checked_answer(other, page_text=page),
                callback,
                other,
            )

    def test_an_address_a_phone_number_and_a_time_are_not_prices(self):
        """An address, a phone number, and a time are not prices."""
        answers = (
            "We're at 149 Maple Street",
            "We're at 149 Maple Street.",
            "We are at 149 Maple Street.",
            "Call us at (856) 555-0142.",
            "Call us at 555-0142.",
            "Saturday: 8:00 am to 12:00 pm.",
        )
        for answer in answers:
            self.assertEqual(price_reply.find_amounts(answer), [], answer)
            self.assertEqual(
                price_reply.checked_answer(answer, base_url=self.site.base),
                answer,
            )
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = price_reply.main(["We're at 149 Maple Street", self.site.base])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "We're at 149 Maple Street\n")

    def test_you_see_this_check_on_the_pull_request(self):
        """You see this check on the pull request as A longer price isn't mistaken for a shorter one."""
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("name: A longer price isn't mistaken for a shorter one\n", workflow)
        self.assertIn("tests/test_prices.py:LongerPriceChecks", workflow)
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        self.assertIn("**A longer price isn't mistaken for a shorter one**", behaviour)
        self.assertIn("An amount is read whole", behaviour)
        self.assertIn("A water heater is $1499.", behaviour)
        self.assertIn("We're at 149 Maple Street", behaviour)


if __name__ == "__main__":
    unittest.main()
