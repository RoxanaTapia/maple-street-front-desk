"""Checks that an answer comes from your pages.

AnswerChecks is the "Answers come from your pages" area.
ClaudeAnswerChecks is the "Claude writes the answer" area.
FailureNoteChecks is the "A failed call is noted for the owner" area.
OutageReplyChecks is the "A failed call gets the outage reply" area.
HoursFaqAnswerChecks is the "Questions 13 to 15 come from Hours and FAQ" area.
WrappedQuestionChecks is the "A wrapped question matches the plain one" area.
The questions, the page each answer comes from, and the callback reply
are read from your agreements. The page text is what the page reader
returns. The docstring of each test is what the checklist prints.

Run one area with
python3 scripts/run_checks.py tests/test_answers.py:AnswerChecks
or python3 scripts/run_checks.py tests/test_answers.py:ClaudeAnswerChecks
or python3 scripts/run_checks.py tests/test_answers.py:FailureNoteChecks
or python3 scripts/run_checks.py tests/test_answers.py:OutageReplyChecks
or python3 scripts/run_checks.py tests/test_answers.py:HoursFaqAnswerChecks
or python3 scripts/run_checks.py tests/test_answers.py:WrappedQuestionChecks.
"""

import contextlib
import io
import json
import os
import re
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import answer_reply
import demo_chat
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


class AnswerChecks(unittest.TestCase):
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

    def test_every_answered_question_names_the_right_page(self):
        """Every question your pages answer ends with the page it used."""
        rows = question_rows()
        self.assertEqual(len(rows), 15)
        pages = self._pages()
        by_name = {page["name"]: page for page in pages}
        answered = [row for row in rows if row["group"] == "Answered by your pages"]
        self.assertEqual(
            [row["number"] for row in answered],
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14, 15],
        )
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
        self.assertEqual([row["number"] for row in uncovered], [11, 12])
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
        self.assertNotIn(answer_reply.outage_reply(), instructions)
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
            self.assertNotIn(answer_reply.outage_reply(), source)
            self.assertNotIn(urgent_reply.fixed_urgent_reply(), source)
            lowered = source.lower()
            self.assertNotIn("openai", lowered)
            self.assertNotIn("grok", lowered)
            self.assertNotIn("sk-ant-", lowered)
        front = (SCRIPTS / "front_desk.py").read_text(encoding="utf-8")
        self.assertNotIn("anthropic", front.lower())
        self.assertNotIn("API_KEY", front)
        writer = (SCRIPTS / "answer_reply.py").read_text(encoding="utf-8")
        self.assertIn("https://api.anthropic.com/v1/messages", writer)
        self.assertIn("ANTHROPIC_API_KEY", writer)
        self.assertIn("CLAUDE_MODEL", writer)

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


class ClaudeAnswerChecks(unittest.TestCase):
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

    def _pages(self):
        return read_pages.read_pages(self.site.base)

    def _callback(self):
        return answer_reply.callback_reply()

    def _block_network(self):
        def fail(*_args, **_kwargs):
            raise AssertionError("the real API was called")

        answer_reply._post_message = fail

    def test_a_mocked_reply_ends_with_the_page_name(self):
        """A page-based answer ends with From and the page name."""
        pages = self._pages()
        callback = self._callback()
        question = "Are you open Saturdays?"
        cases = (
            (
                "Yes, we service tankless water heaters. (Source: Services page)",
                "Yes, we service tankless water heaters. From Services.",
            ),
            (
                "Yes. (Source: the Services page)",
                "Yes. From Services.",
            ),
            (
                "Monday to Friday: 8:00 am to 5:00 pm.\nSource: Hours & FAQ page",
                "Monday to Friday: 8:00 am to 5:00 pm. From Hours & FAQ.",
            ),
            (
                "Sunday: closed. (Hours & FAQ page)",
                "Sunday: closed. From Hours & FAQ.",
            ),
            (
                "We are open Saturdays. From the Hours & FAQ page.",
                "We are open Saturdays. From Hours & FAQ.",
            ),
            (
                "Yes, open Saturday morning. From Hours & FAQ.",
                "Yes, open Saturday morning. From Hours & FAQ.",
            ),
        )
        seen = {}

        def client(payload):
            seen["instructions"] = payload["messages"][0]["content"]
            return {
                "content": [
                    {"type": "thinking", "thinking": "pick a page"},
                    {"type": "text", "text": seen["reply"]},
                ]
            }

        self._block_network()
        for raw, expected in cases:
            seen["reply"] = raw
            got = front_desk.reply_to(question, base_url=self.site.base, client=client)
            self.assertEqual(got, expected, raw)
            self.assertNotIn("pick a page", got)
        instructions = seen["instructions"]
        self.assertIn("End the answer with exactly From <Page name>.", instructions)
        self.assertIn("For example, From Hours & FAQ.", instructions)
        self.assertIn("Name the page the answer came from.", instructions)
        seen["reply"] = callback
        self.assertEqual(answer_reply.write_answer(question, pages, client=client), callback)
        seen["reply"] = callback + "\n(Source: Home page)"
        self.assertEqual(answer_reply.write_answer(question, pages, client=client), callback)
        called = {"n": 0}

        def client_urgent(_payload):
            called["n"] += 1
            return {"content": [{"type": "text", "text": "No. (Source: Contact page)"}]}

        urgent = front_desk.reply_to("I have a frozen pipe", client=client_urgent)
        self.assertEqual(urgent, urgent_reply.fixed_urgent_reply())
        self.assertEqual(called["n"], 0)

    def test_a_failed_call_gets_the_outage_reply(self):
        """A failed Claude call gets the outage reply, not the missing-information reply."""
        pages = self._pages()
        callback = self._callback()
        outage = answer_reply.outage_reply()
        self.assertNotEqual(outage, callback)
        question = "Are you open Saturdays?"
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        def client(_payload):
            raise TimeoutError("timed out")

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            got = front_desk.reply_to(question, base_url=self.site.base, client=client)
        self.assertEqual(got, outage)
        self.assertNotEqual(got, callback)
        self.assertNotIn("test-key", got)
        self.assertNotIn("Traceback", got)
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertNotIn("timed out", got)

        def client_down(_payload):
            raise urllib.error.URLError("network down")

        down = answer_reply.write_answer(question, pages, client=client_down)
        self.assertEqual(down, outage)
        self.assertNotEqual(down, callback)

        def client_empty(_payload):
            return {"content": [{"type": "thinking", "thinking": "no text"}]}

        empty = answer_reply.write_answer(question, pages, client=client_empty)
        self.assertEqual(empty, outage)
        self.assertNotEqual(empty, callback)

        def boom(payload, key, timeout):
            self.assertEqual(key, "test-key")
            self.assertEqual(timeout, answer_reply.TIMEOUT_SECONDS)
            self.assertNotIn("test-key", json.dumps(payload))
            raise urllib.error.HTTPError(
                "https://api.anthropic.com/v1/messages",
                401,
                "Unauthorized",
                hdrs=None,
                fp=io.BytesIO(b""),
            )

        answer_reply._post_message = boom
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            got = answer_reply.write_answer(question, pages)
        self.assertEqual(got, answer_reply.outage_reply())
        self.assertNotEqual(got, callback)
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertNotIn("Unauthorized", got)
        self.assertNotIn("test-key", got)

    def test_the_call_uses_a_short_timeout(self):
        """The Claude call uses a short timeout and keeps the key out of the message."""
        seen = {}

        class Fake:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"content":[{"type":"text","text":"Yes. From Services."}]}'

        def fake_open(request, timeout=None):
            seen["timeout"] = timeout
            seen["key"] = request.get_header("X-api-key")
            seen["body"] = request.data.decode("utf-8")
            seen["url"] = request.full_url
            return Fake()

        original = urllib.request.urlopen
        answer_reply.urllib.request.urlopen = fake_open
        try:
            body = answer_reply._post_message(
                {"model": answer_reply.DEFAULT_MODEL, "messages": []},
                "test-key",
                answer_reply.TIMEOUT_SECONDS,
            )
        finally:
            answer_reply.urllib.request.urlopen = original
        self.assertGreater(answer_reply.TIMEOUT_SECONDS, 0)
        self.assertLessEqual(answer_reply.TIMEOUT_SECONDS, 20)
        self.assertEqual(seen["timeout"], answer_reply.TIMEOUT_SECONDS)
        self.assertEqual(seen["url"], "https://api.anthropic.com/v1/messages")
        self.assertEqual(seen["key"], "test-key")
        self.assertNotIn("test-key", seen["body"])
        self.assertEqual(answer_reply._message_text(body), "Yes. From Services.")

    def test_no_key_uses_the_stand_in(self):
        """With no key, the stand-in answers and no call is made."""
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        pages = self._pages()
        question = "Are you open Saturdays?"
        called = {"n": 0}

        def boom(*_args, **_kwargs):
            called["n"] += 1
            raise AssertionError("the API was called with no key")

        answer_reply._post_message = boom
        got = front_desk.reply_to(question, base_url=self.site.base)
        written = answer_reply.write_answer(question, pages)
        self.assertEqual(called["n"], 0)
        self.assertEqual(got, written)
        self.assertIn("Hours & FAQ", got)
        self.assertIn("From Hours & FAQ.", got)
        self.assertIn("8:00 am", got)
        self.assertNotEqual(got, self._callback())
        os.environ["ANTHROPIC_API_KEY"] = "   "
        again = answer_reply.write_answer(question, pages)
        self.assertEqual(called["n"], 0)
        self.assertEqual(again, written)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        uncovered = answer_reply.write_answer("How long is your warranty?", pages)
        self.assertEqual(uncovered, self._callback())
        self.assertEqual(called["n"], 0)

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
                "content": [
                    {"type": "text", "text": f"A water heater replacement is {invented}."}
                ]
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

    def test_the_agreements_record_the_simpler_setup(self):
        """The agreements record the simpler setup and Claude as the AI."""
        agreements = AGREEMENTS.read_text(encoding="utf-8")
        self.assertIn("## How answers are written\n", agreements)
        section = agreements.split("## How answers are written", 1)[1]
        self.assertIn("simpler setup", section.lower())
        self.assertIn("Claude", section)
        self.assertIn("six pages", section.lower())
        self.assertIn("document search engine", section.lower())
        for path in docs():
            text = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("ai-doc", text, path.relative_to(ROOT))
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("ANTHROPIC_API_KEY", example)
        self.assertIn("CLAUDE_MODEL", example)
        self.assertNotIn("sk-ant-", example)
        self.assertNotIn("sk-ant-", ignore)
        self.assertTrue(any(line.strip() == ".env" for line in ignore.splitlines()))


class FailureNoteChecks(unittest.TestCase):
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

    def _block_network(self):
        def fail(*_args, **_kwargs):
            raise AssertionError("the real API was called")

        answer_reply._post_message = fail

    def test_a_failed_call_is_noted_and_the_outage_reply_is_used(self):
        """A failed call gets the outage reply, and a note records the time and the kind of error."""
        callback = answer_reply.callback_reply()
        outage = answer_reply.outage_reply()
        self.assertNotEqual(outage, callback)
        key = "test-key"
        token = "maple-street-question-token"
        question = f"Are you open Saturdays? {token}"
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "setup-guide.md").read_text(encoding="utf-8")
        self.assertEqual(self._saved_log, ROOT / "logs" / "claude-failures.log")
        self.assertTrue(any(line.strip() == "logs/" for line in ignore.splitlines()))
        self.assertIn("logs/claude-failures.log", guide)
        self.assertNotIn("sk-ant-", guide)
        self.assertNotIn(key, guide)

        self._block_network()
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
        ordinary = front_desk.reply_to("Are you open Saturdays?", base_url=self.site.base)
        self.assertIn("From Hours & FAQ.", ordinary)
        self.assertNotEqual(ordinary, callback)
        self.assertNotEqual(ordinary, outage)
        self.assertFalse(answer_reply.FAILURE_LOG.exists())

        os.environ["ANTHROPIC_API_KEY"] = key

        def client_down(_payload):
            raise TimeoutError(token)

        urgent = front_desk.reply_to(
            "I have a burst pipe",
            base_url=self.site.base,
            client=client_down,
        )
        self.assertEqual(urgent, urgent_reply.fixed_urgent_reply())
        self.assertFalse(answer_reply.FAILURE_LOG.exists())

        def client_ok(payload):
            self.assertIn("Are you open Saturdays?", payload["messages"][0]["content"])
            self.assertNotIn(key, json.dumps(payload))
            return {
                "content": [
                    {"type": "text", "text": "Yes, we are open Saturdays. From Hours & FAQ."}
                ]
            }

        answered = front_desk.reply_to("Are you open Saturdays?", base_url=self.site.base, client=client_ok)
        self.assertNotEqual(answered, callback)
        self.assertNotEqual(answered, outage)
        self.assertNotIn(key, answered)
        self.assertFalse(answer_reply.FAILURE_LOG.exists())

        unauthorized = urllib.error.HTTPError(
            "https://api.anthropic.com/v1/messages",
            401,
            "Unauthorized",
            hdrs=None,
            fp=io.BytesIO(f"invalid {key} {token}".encode("utf-8")),
        )
        cases = (
            (TimeoutError(f"timed out {token} {key}"), "timeout"),
            (unauthorized, "key missing or expired"),
            (urllib.error.URLError(f"network down {token} {key}"), "Claude is down"),
            (RuntimeError(f"boom {token} {key}"), "call failed"),
        )

        def raising(error):
            def client(payload):
                self.assertIn(token, payload["messages"][0]["content"])
                self.assertNotIn(key, json.dumps(payload))
                raise error

            return client

        def empty(payload):
            self.assertIn(token, payload["messages"][0]["content"])
            self.assertNotIn(key, json.dumps(payload))
            return {"content": [{"type": "thinking", "thinking": f"{token} {key}"}]}

        started = datetime.now(timezone.utc)
        with self.assertLogs(level="WARNING") as logged:
            for error, kind in cases:
                got = front_desk.reply_to(question, base_url=self.site.base, client=raising(error))
                self.assertEqual(got, outage)
                self.assertNotEqual(got, callback)
                self.assertNotIn(token, got)
                self.assertNotIn(key, got)
                self.assertNotIn(kind, got)
            got = front_desk.reply_to(question, base_url=self.site.base, client=empty)
            self.assertEqual(got, outage)
            self.assertNotEqual(got, callback)
            self.assertNotIn(token, got)
            self.assertNotIn(key, got)
        self.assertEqual(
            [record.getMessage() for record in logged.records],
            [
                "Claude could not answer (timeout).",
                "Claude could not answer (key missing or expired).",
                "Claude could not answer (Claude is down).",
                "Claude could not answer (call failed).",
                "Claude could not answer (empty reply).",
            ],
        )
        warning_text = "\n".join(logged.output)
        self.assertNotIn(token, warning_text)
        self.assertNotIn(key, warning_text)
        self.assertNotIn("Traceback", warning_text)

        note = answer_reply.FAILURE_LOG.read_text(encoding="utf-8")
        self.assertTrue(note.endswith("\n"))
        self.assertNotIn("\n\n", note)
        self.assertNotIn(token, note)
        self.assertNotIn(key, note)
        self.assertNotIn(question, note)
        self.assertNotIn("Unauthorized", note)
        self.assertNotIn("timed out", note)
        self.assertNotIn("Traceback", note)
        lines = note.splitlines()
        expected = (
            "timeout",
            "key missing or expired",
            "Claude is down",
            "call failed",
            "empty reply",
        )
        self.assertEqual(len(lines), len(expected))
        for line, kind in zip(lines, expected):
            stamp, found = line.split(" ", 1)
            self.assertEqual(found, kind)
            seen = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            self.assertGreaterEqual(seen, started.replace(microsecond=0))
            self.assertLessEqual((datetime.now(timezone.utc) - seen).total_seconds(), 120)

        again = front_desk.reply_to(
            "Are you open Saturdays?",
            base_url=self.site.base,
            client=client_ok,
        )
        self.assertNotEqual(again, callback)
        self.assertNotEqual(again, outage)
        self.assertEqual(answer_reply.FAILURE_LOG.read_text(encoding="utf-8"), note)


MISSING_REPLY = "Please call us on (856) 555-0142 to confirm that."
OUTAGE_REPLY = (
    "Sorry, I can\u2019t look that up right now. "
    "Please call us on (856) 555-0142."
)


class _FrozenClock:
    """A clock that always reports one instant, so the failure note is exact."""

    when = datetime(2026, 11, 7, 15, 30, 0, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls.when


class OutageReplyChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()
        self._post = answer_reply._post_message
        self._saved_log = answer_reply.FAILURE_LOG
        self._saved_clock = answer_reply.datetime
        self._log_dir = tempfile.TemporaryDirectory()
        answer_reply.FAILURE_LOG = Path(self._log_dir.name) / "claude-failures.log"

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

    def test_the_two_replies_are_separate_sentences(self):
        """The outage reply and the missing-information reply are separate agreed sentences."""
        self._block_network()
        missing = answer_reply.callback_reply()
        outage = answer_reply.outage_reply()
        self.assertEqual(missing, MISSING_REPLY)
        self.assertEqual(price_reply.callback_reply(), MISSING_REPLY)
        self.assertEqual(outage, OUTAGE_REPLY)
        self.assertNotEqual(outage, missing)
        self.assertNotEqual(missing, "I can't confirm that from your pages.")
        agreements = AGREEMENTS.read_text(encoding="utf-8")
        self.assertIn("## When the pages don't say\n", agreements)
        self.assertIn("## When the assistant can't look it up\n", agreements)
        self.assertEqual(agreements.count(MISSING_REPLY), 1)
        self.assertEqual(agreements.count(OUTAGE_REPLY), 1)
        for name in ("answer_reply.py", "price_reply.py", "front_desk.py", "demo_chat.py"):
            source = (SCRIPTS / name).read_text(encoding="utf-8")
            self.assertNotIn(MISSING_REPLY, source, name)
            self.assertNotIn(OUTAGE_REPLY, source, name)
        sample = (
            "## When the pages don't say\n\n> Call the office.\n\n"
            "## When the assistant can't look it up\n\n> The lookup is down.\n"
        )
        self.assertEqual(answer_reply.callback_reply(sample), "Call the office.")
        self.assertEqual(answer_reply.outage_reply(sample), "The lookup is down.")
        pages = self._pages()
        question = "Where is the shop?"

        def client(_payload):
            raise TimeoutError(question)

        with self.assertLogs(level="WARNING"):
            got = answer_reply.write_answer(question, pages, client=client, text=sample)
        self.assertEqual(got, "The lookup is down.")
        self.assertNotEqual(got, "Call the office.")
        note = answer_reply.FAILURE_LOG.read_text(encoding="utf-8")
        self.assertNotIn(question, note)
        self.assertNotIn("The lookup is down.", note)
        self.assertNotIn("Call the office.", note)
        stamp, kind = note.strip().split(" ", 1)
        self.assertEqual(kind, "timeout")
        datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
        self.assertEqual(note, f"{stamp} timeout\n")

    def test_a_failed_call_returns_only_the_outage_reply(self):
        """A failed call returns only the outage reply, and the note keeps the time and the kind of error."""
        self.assertEqual(self._saved_log, ROOT / "logs" / "claude-failures.log")
        answer_reply.datetime = _FrozenClock
        missing = answer_reply.callback_reply()
        outage = answer_reply.outage_reply()
        key = "test-key"
        token = "maple-street-question-token"
        question = f"Are you open Saturdays? {token}"
        os.environ["ANTHROPIC_API_KEY"] = key
        self._block_network()
        pages = self._pages()
        unauthorized = urllib.error.HTTPError(
            "https://api.anthropic.com/v1/messages",
            401,
            "Unauthorized",
            hdrs=None,
            fp=io.BytesIO(f"invalid {key} {token}".encode("utf-8")),
        )
        service_down = urllib.error.HTTPError(
            "https://api.anthropic.com/v1/messages",
            503,
            "unavailable",
            hdrs=None,
            fp=io.BytesIO(token.encode("utf-8")),
        )
        cases = (
            (TimeoutError(f"timed out {token} {key}"), "timeout"),
            (unauthorized, "key missing or expired"),
            (service_down, "Claude is down"),
            (urllib.error.URLError(f"network down {token} {key}"), "Claude is down"),
            (RuntimeError(f"boom {token} {key}"), "call failed"),
        )

        def raising(error):
            def client(payload):
                self.assertIn(token, payload["messages"][0]["content"])
                self.assertNotIn(key, json.dumps(payload))
                raise error

            return client

        def empty(payload):
            self.assertIn(token, payload["messages"][0]["content"])
            self.assertNotIn(key, json.dumps(payload))
            return {"content": [{"type": "thinking", "thinking": f"{token} {key}"}]}

        with self.assertLogs(level="WARNING") as logged:
            for error, kind in cases:
                got = front_desk.reply_to(question, base_url=self.site.base, client=raising(error))
                self.assertEqual(got, outage, kind)
                self.assertNotEqual(got, missing, kind)
                self.assertNotIn(token, got, kind)
                self.assertNotIn(key, got, kind)
                self.assertNotIn(kind, got, kind)
                written = answer_reply.write_answer(question, pages, client=raising(error))
                self.assertEqual(written, outage, kind)
            got = front_desk.reply_to(question, base_url=self.site.base, client=empty)
            self.assertEqual(got, outage)
            self.assertNotEqual(got, missing)

            def boom(payload, header_key, timeout):
                self.assertEqual(header_key, key)
                self.assertIn(token, payload["messages"][0]["content"])
                self.assertNotIn(key, json.dumps(payload))
                raise TimeoutError(token)

            answer_reply._post_message = boom
            shown = demo_chat.safe_reply(question, self.site.base)
            self.assertEqual(shown, outage)
            self.assertNotEqual(shown, missing)
            self.assertNotIn(token, shown)
            self.assertNotIn(key, shown)

        warning_text = "\n".join(logged.output)
        self.assertNotIn(token, warning_text)
        self.assertNotIn(key, warning_text)
        self.assertNotIn("Traceback", warning_text)
        self.assertNotIn("Unauthorized", warning_text)
        note = answer_reply.FAILURE_LOG.read_text(encoding="utf-8")
        self.assertNotIn(token, note)
        self.assertNotIn(key, note)
        self.assertNotIn(question, note)
        self.assertNotIn("Unauthorized", note)
        self.assertNotIn("timed out", note)
        self.assertNotIn(outage, note)
        self.assertNotIn(missing, note)
        lines = note.splitlines()
        expected = (
            "2026-11-07T15:30:00Z timeout",
            "2026-11-07T15:30:00Z timeout",
            "2026-11-07T15:30:00Z key missing or expired",
            "2026-11-07T15:30:00Z key missing or expired",
            "2026-11-07T15:30:00Z Claude is down",
            "2026-11-07T15:30:00Z Claude is down",
            "2026-11-07T15:30:00Z Claude is down",
            "2026-11-07T15:30:00Z Claude is down",
            "2026-11-07T15:30:00Z call failed",
            "2026-11-07T15:30:00Z call failed",
            "2026-11-07T15:30:00Z empty reply",
            "2026-11-07T15:30:00Z timeout",
        )
        self.assertEqual(lines, list(expected))
        urgent = front_desk.reply_to("I have a burst pipe", base_url=self.site.base, client=raising(TimeoutError(token)))
        self.assertEqual(urgent, urgent_reply.fixed_urgent_reply())
        self.assertEqual(answer_reply.FAILURE_LOG.read_text(encoding="utf-8"), note)
        priced = "Sorry, the lookup is down. A visit is $1,200."
        original = answer_reply.outage_reply

        def pricey(text=None):
            return priced

        answer_reply.outage_reply = pricey
        try:
            def client(_payload):
                raise TimeoutError(token)

            with self.assertLogs(level="WARNING"):
                got = front_desk.reply_to(
                    "Are you open Saturdays?",
                    base_url=self.site.base,
                    client=client,
                )
        finally:
            answer_reply.outage_reply = original
        self.assertEqual(got, priced)
        self.assertNotEqual(got, missing)
        self.assertNotIn("$1,200", missing)
        self.assertNotIn(token, got)
        self.assertNotIn(key, got)
        saved = answer_reply.FAILURE_LOG.read_text(encoding="utf-8")
        self.assertNotIn(token, saved)
        self.assertNotIn(key, saved)
        self.assertNotIn(priced, saved)
        self.assertTrue(saved.startswith(note))
        self.assertTrue(saved.endswith("2026-11-07T15:30:00Z timeout\n"))

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
            "Do you sell pizza?",
        ):
            got = front_desk.reply_to(question, base_url=self.site.base)
            self.assertEqual(got, missing, question)
            self.assertNotEqual(got, outage, question)
            self.assertEqual(answer_reply.write_answer(question, pages), missing, question)
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


def docs():
    files = []
    for pattern in ("*.md", "*.mdc"):
        files.extend(ROOT.rglob(pattern))
    return [path for path in files if ".git" not in path.parts]


class HoursFaqAnswerChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def test_questions_13_to_15_come_from_hours_and_faq(self):
        """Questions 13 to 15 are answered from the Hours & FAQ page, and the after-hours question is not urgent."""
        rows = {row["number"]: row for row in question_rows()}
        callback = answer_reply.callback_reply()
        urgent = urgent_reply.fixed_urgent_reply()
        expected = {
            13: "No, we don't install or service septic systems. From Hours & FAQ.",
            14: "Yes, we're fully licensed and insured in New Jersey. From Hours & FAQ.",
            15: (
                "Yes, we handle emergencies after hours too. "
                "Just call our main line at (856) 555-0142. From Hours & FAQ."
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


def _wrapped_forms(message):
    """The same words with quotes, markdown, or a question mark around them."""
    forms = [
        f'"{message}"',
        f"'{message}'",
        f"`{message}`",
        f"**{message}**",
        f"*{message}*",
        f"_{message}_",
        f"“{message}”",
        f"‘{message}’",
        f"> {message}",
        f"# {message}",
        f"({message})",
        f"[{message}]",
        f'`"{message}"`',
        f'"{message}"?',
        message if message.endswith("?") else f"{message}?",
    ]
    return forms


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
            self.assertNotEqual(front_desk.reply_to(message, base_url=self.site.base), urgent, message)
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
