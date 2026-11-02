"""Checks that an answer comes from your pages.

AnswerChecks is the "Answers come from your pages" area. The questions,
the page each answer comes from, and the callback reply are read from
your agreements. The page text is what the page reader returns. The
docstring of each test is what the checklist prints.

Run this area with
python3 scripts/run_checks.py tests/test_answers.py:AnswerChecks.
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

import answer_reply
import front_desk
import price_reply
import read_pages
import serve_sample_site
import urgent_reply

AGREEMENTS = ROOT / "docs" / "agreements.md"
GROUP_HEADING = re.compile(r"^\*\*(.+?)\*\*$")
QUESTION_LINE = re.compile(r"^(\d+)\.\s+(.+)$")
FROM_PAGE = re.compile(r"\bfrom\s+(.+?)\.?$", re.IGNORECASE)
CLOCK = re.compile(r"\d{1,2}:\d{2} am to \d{1,2}:\d{2} pm", re.IGNORECASE)


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
        rows.append(
            {
                "number": int(match.group(1)),
                "question": question,
                "detail": detail,
                "group": group,
            }
        )
    return rows


def page_named(detail):
    match = FROM_PAGE.search(detail.strip())
    if not match:
        return None
    return match.group(1).strip()


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


class AnswerChecks(unittest.TestCase):
    def setUp(self):
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True

    def _pages(self):
        return read_pages.read_pages(self.site.base)

    def _callback(self):
        return answer_reply.callback_reply()

    def test_every_answered_question_names_the_right_page(self):
        """Every question your pages answer names the page it came from."""
        rows = question_rows()
        self.assertEqual(len(rows), 15)
        pages = self._pages()
        by_name = {page["name"]: page for page in pages}
        answered = [row for row in rows if row["group"] == "Answered by your pages"]
        self.assertEqual(len(answered), 9)
        for row in answered:
            self.assertIsNone(urgent_reply.reply_if_urgent(row["question"]), row["question"])
            name = page_named(row["detail"])
            self.assertIn(name, by_name, row["question"])
            answer = front_desk.reply_to(row["question"], base_url=self.site.base)
            written = answer_reply.write_answer(row["question"], pages)
            self.assertEqual(answer, written, row["question"])
            self.assertNotEqual(answer, self._callback(), row["question"])
            self.assertIn(name, answer, row["question"])
            self.assertTrue(answer.endswith(f"From {name}."), row["question"])
            self.assertNotIn("This is a fictional business", answer, row["question"])
            self.assertNotIn("Home Services Pricing", answer, row["question"])
            body = answer[: -len(f"From {name}.")].strip()
            for part in re.split(r"(?<=[.!?])\s+", body):
                self.assertIn(part, by_name[name]["text"], row["question"])
            for fact in CLOCK.findall(row["detail"]) + price_reply.find_amounts(row["detail"]):
                self.assertIn(fact, answer, row["question"])
                self.assertIn(fact, by_name[name]["text"], row["question"])
        sunday = next(row for row in answered if row["question"] == "Are you open Sundays?")
        sunday_answer = front_desk.reply_to(sunday["question"], base_url=self.site.base)
        self.assertIn("closed", sunday_answer.lower())
        self.assertNotIn("saturday", sunday_answer.lower())
        booking = next(row for row in answered if "book or cancel" in row["question"].lower())
        booking_answer = front_desk.reply_to(booking["question"], base_url=self.site.base)
        self.assertIn("book", booking_answer.lower())
        self.assertIn("cancel", booking_answer.lower())
        self.assertIn("Contact", booking_answer)

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
        self.assertGreaterEqual(len(uncovered), 1)
        self.assertEqual(len(uncovered), 5)
        for row in uncovered:
            self.assertIsNone(page_named(row["detail"]), row["question"])
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

    def test_an_urgent_message_stops_at_the_first_part(self):
        """An urgent message stops at the first part."""
        reply = urgent_reply.fixed_urgent_reply()
        rows = question_rows()
        urgent_rows = [row for row in rows if urgent_reply.reply_if_urgent(row["question"])]
        self.assertGreaterEqual(len(urgent_rows), 1)
        called = {"pages": 0, "writer": 0}

        def read_fail(base_url):
            called["pages"] += 1
            raise AssertionError("pages were read for an urgent message")

        def writer(question, instructions, pages):
            called["writer"] += 1
            raise AssertionError("the answer writer ran for an urgent message")

        original = read_pages.read_pages
        read_pages.read_pages = read_fail
        try:
            for word in urgent_reply.urgent_words():
                got = front_desk.reply_to(f"We have {word}.", writer=writer)
                self.assertEqual(got, reply, word)
                self.assertNotIn("$", got)
            for row in urgent_rows:
                got = front_desk.reply_to(row["question"], writer=writer)
                self.assertEqual(got, reply, row["question"])
        finally:
            read_pages.read_pages = original
        self.assertEqual(called["pages"], 0)
        self.assertEqual(called["writer"], 0)
        pages = self._pages()
        for row in urgent_rows:
            self.assertEqual(
                answer_reply.write_answer(row["question"], pages),
                self._callback(),
                row["question"],
            )

    def test_an_unpublished_price_is_swapped(self):
        """An answer with an unpublished price is swapped for the callback reply."""
        published = price_reply.published_amounts(self.site.base)
        callback = self._callback()
        self.assertGreaterEqual(len(published), 1)
        invented = "$1,200"
        self.assertNotIn(invented, published)
        seen = {"pages": 0}

        def writer(question, instructions, pages):
            seen["pages"] = len(pages)
            self.assertIn(callback, instructions)
            return f"A water heater replacement is {invented}."

        got = front_desk.reply_to(
            "How much is a water heater replacement?",
            base_url=self.site.base,
            writer=writer,
        )
        self.assertEqual(seen["pages"], 6)
        self.assertEqual(got, callback)
        self.assertNotIn(invented, got)
        kept = f"The price is {published[0]}."

        def keep_writer(question, instructions, pages):
            return kept

        self.assertEqual(
            front_desk.reply_to(
                "How much is a drain cleaning?",
                base_url=self.site.base,
                writer=keep_writer,
            ),
            kept,
        )

    def test_the_instructions_include_every_page_and_the_callback(self):
        """The instructions sent to the writer include every page and the callback reply."""
        pages = self._pages()
        self.assertEqual(len(pages), 6)
        callback = self._callback()
        question = "Are you open Saturdays?"
        sent = {}

        def writer(question_arg, instructions, pages_arg):
            sent["question"] = question_arg
            sent["instructions"] = instructions
            sent["pages"] = pages_arg
            return answer_reply.stand_in_writer(question_arg, instructions, pages_arg)

        got = answer_reply.write_answer(question, pages, writer=writer)
        self.assertEqual(sent["question"], question)
        self.assertIs(sent["pages"], pages)
        instructions = sent["instructions"]
        self.assertEqual(instructions, answer_reply.build_instructions(question, pages))
        self.assertIn("Answer the customer's question only from these pages.", instructions)
        self.assertIn("Keep the answer short.", instructions)
        self.assertIn("Name the page the answer came from.", instructions)
        self.assertIn(callback, instructions)
        self.assertIn(question, instructions)
        for page in pages:
            self.assertEqual(page["status"], "read", page["name"])
            self.assertTrue(page["text"], page["name"])
            self.assertIn(f"Page: {page['name']}", instructions)
            self.assertIn(page["text"], instructions)
        self.assertIn("Hours & FAQ", got)
        self.assertNotEqual(got, callback)
        self.assertEqual(
            answer_reply.stand_in_writer(question, "No pages here.", pages),
            callback,
        )
        self.assertIn("not a real AI", answer_reply.stand_in_writer.__doc__)

        def custom(question_arg, instructions, pages_arg):
            return "CUSTOM"

        self.assertEqual(answer_reply.write_answer("Hello", pages, writer=custom), "CUSTOM")
        for name in ("answer_reply.py", "front_desk.py"):
            source = (SCRIPTS / name).read_text(encoding="utf-8")
            self.assertNotIn(callback, source)
            self.assertNotIn(urgent_reply.fixed_urgent_reply(), source)
            for banned in ("openai", "anthropic", "grok", "api_key", "API_KEY"):
                self.assertNotIn(banned, source.lower() if banned == "api_key" else source)

    def test_checking_a_message_prints_the_reply(self):
        """Checking a message prints the answer, the callback reply, or the urgent reply."""
        rows = question_rows()
        callback = self._callback()
        urgent = urgent_reply.fixed_urgent_reply()
        answered = next(row for row in rows if row["group"] == "Answered by your pages")
        uncovered = next(
            row
            for row in rows
            if row["group"] != "Answered by your pages"
            and urgent_reply.reply_if_urgent(row["question"]) is None
        )
        urgent_row = next(row for row in rows if urgent_reply.reply_if_urgent(row["question"]))
        expected = front_desk.reply_to(answered["question"], base_url=self.site.base)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = answer_reply.main(answered["question"].split() + [self.site.base])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), expected + "\n")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = front_desk.main(uncovered["question"].split() + [self.site.base])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), callback + "\n")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = front_desk.main(urgent_row["question"].split())
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), urgent + "\n")
        for command in (answer_reply.main, front_desk.main):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(command(["--help"]), 2)
            self.assertIn("Usage:", stderr.getvalue())
            self.assertNotIn(callback, stderr.getvalue())
            self.assertNotIn(urgent, stderr.getvalue())
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(command([]), 2)

    def test_you_see_this_check_on_the_pull_request(self):
        """You see this check on the pull request as Answers come from your pages."""
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("name: Answers come from your pages\n", workflow)
        self.assertIn("tests/test_answers.py:AnswerChecks", workflow)
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        self.assertIn("**Answers come from your pages**", behaviour)
        self.assertIn("names the page it came from", behaviour)
        self.assertIn("include the text of your pages", behaviour)
        self.assertIn(
            "You see this check on the pull request as Answers come from your pages.",
            behaviour,
        )
        how = (ROOT / "docs" / "how-it-works.md").read_text(encoding="utf-8")
        self.assertNotIn("Write the answer (coming next)", how)
        self.assertNotIn("not written yet", how)
        self.assertNotIn("coming next", how)
        self.assertIn("`scripts/answer_reply.py`", how)
        self.assertIn("`scripts/front_desk.py`", how)
        section = how.split("## 3 · Write the answer", 1)[1].split("## 4 ·", 1)[0]
        self.assertIn("real AI call", section)
        self.assertIn("not a real AI", section)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("- ⏳ **Writes the answer:** a short reply from your pages.", readme)
        self.assertNotIn("answer_reply.py", readme)
        self.assertNotIn("front_desk.py", readme)
        for name in ("answer_reply.py", "front_desk.py", "tests/test_answers.py"):
            self.assertIn(name, (ROOT / "tests" / "test_checks.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
