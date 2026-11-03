"""Checks for the sample site and the page list.

PageListChecks is the "Your pages are read" area: the page list, Pricing
live, a page that can't be fetched, the fictional banner, and the words
on the pages.
QuestionCoverageChecks is the "Every test question has an answer plan"
area: every test question is answered from a page or handled by a set
reply, and an answered question names one of your pages.

The docstring of each test is what the CI checklist prints.

Run every check with python3 scripts/run_checks.py.
Run one area, as the CI jobs do, with
python3 scripts/run_checks.py tests/test_pages.py:PageListChecks
or python3 scripts/run_checks.py tests/test_pages.py:QuestionCoverageChecks.
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

import read_pages
import serve_sample_site

BANNER = "This is a fictional business made for this demo."
AGREED_NAMES = [
    "Home",
    "Services",
    "Pricing",
    "Service Area",
    "Hours & FAQ",
    "Contact",
]
PHONE = re.compile(r"(?:\(\d{3}\)\s*|\b\d{3}[-.])\d{3}[-.]\d{4}")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PRICE = re.compile(r"\$\d+(?:\.\d{2})?")


def visible_text(html):
    parser = read_pages.TitleTextParser()
    parser.feed(html)
    parser.close()
    return parser.text, parser.title


def fetch_page(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        html = response.read().decode(charset)
        status = response.status
    text, title = visible_text(html)
    return status, html, text, title


class RunningSite:
    def __init__(self):
        self.httpd = serve_sample_site.make_server("127.0.0.1", 0)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self._wait()

    def _wait(self):
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


class PageListChecks(unittest.TestCase):
    def setUp(self):
        serve_sample_site.pricing_live = True
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = True

    def test_pricing_is_live_and_all_six_pages_are_read(self):
        """Pricing is live, so all six pages are read. Each title matches the page and includes the page's name."""
        source = (SCRIPTS / "serve_sample_site.py").read_text(encoding="utf-8")
        self.assertRegex(source, r"(?m)^pricing_live = True\b")
        pages = read_pages.read_pages(self.site.base)
        self.assertEqual(len(pages), 6)
        for page in pages:
            self.assertEqual(page["status"], "read", page["name"])
            self.assertEqual(page["reason"], "")
            status, _html, _text, title = fetch_page(page["address"])
            self.assertEqual(status, 200)
            self.assertEqual(page["title"], title)
            self.assertTrue(page["title"])
            self.assertIn(page["name"], page["title"])

    def test_unreadable_page_stays_on_the_list(self):
        """A page that can't be fetched stays on the list as unreadable, with the reason, and with no title. The other pages are still read."""
        serve_sample_site.pricing_live = False
        pages = read_pages.read_pages(self.site.base)
        read = [page for page in pages if page["status"] == "read"]
        unread = [page for page in pages if page["status"] != "read"]
        self.assertEqual([page["name"] for page in read], [
            "Home",
            "Services",
            "Service Area",
            "Hours & FAQ",
            "Contact",
        ])
        self.assertEqual(len(unread), 1)
        pricing = unread[0]
        self.assertEqual(pricing["name"], "Pricing")
        self.assertEqual(pricing["status"], "unreadable")
        self.assertIn("503", pricing["reason"])
        self.assertEqual(pricing["title"], "")
        text = read_pages.format_page_list(pages)
        self.assertIn("Pricing", text)
        self.assertIn("unreadable", text)
        self.assertIn(pricing["address"], text)
        self.assertIn("Status: read", text)

    def test_scripts_and_styling_are_left_out(self):
        """Scripts and styling are left out of the title and the visible text."""
        html = (
            "<html><head><title>Home | Maple Street</title>"
            "<style>.secret { color: red; }</style>"
            "<script>var hidden = 'not for customers';</script></head>"
            "<body><p>Visible line</p>"
            "<script>alert('also hidden')</script></body></html>"
        )
        parser = read_pages.TitleTextParser()
        parser.feed(html)
        parser.close()
        self.assertEqual(parser.title, "Home | Maple Street")
        self.assertIn("Visible line", parser.text)
        for hidden in ("secret", "not for customers", "also hidden", "alert"):
            self.assertNotIn(hidden, parser.text)
            self.assertNotIn(hidden, parser.title)

    def test_every_page_shows_the_fictional_banner(self):
        """Every page shows the banner that this business is fictional."""
        css = (ROOT / "sample-site" / "style.css").read_text(encoding="utf-8")
        self.assertIn(".banner", css)
        banner_rule = css.split(".banner", 1)[1].split("}", 1)[0]
        self.assertNotIn("display: none", banner_rule)
        self.assertNotIn("visibility: hidden", banner_rule)
        for agreed in read_pages.agreed_pages():
            url = read_pages.page_address(self.site.base, agreed["path"])
            _status, html, text, _title = fetch_page(url)
            self.assertIn(BANNER, text, agreed["name"])
            self.assertIn('class="banner"', html, agreed["name"])

    def test_every_agreed_page_appears_on_the_page_list(self):
        """Every agreed page appears on the page list with its title, address, and status."""
        agreed = read_pages.agreed_pages()
        self.assertEqual([page["name"] for page in agreed], AGREED_NAMES)
        for item in agreed:
            self.assertTrue(item["path"].startswith("/"), item["name"])
            self.assertTrue(_sample_file(item["path"]).is_file(), item["name"])
        sample = (
            "## Your pages\n\n"
            "The assistant answers only from these six pages of your website: "
            "Home and Contact.\n"
        )
        named = read_pages.agreed_pages(sample)
        self.assertEqual([page["name"] for page in named], ["Home", "Contact"])
        self.assertEqual([page["path"] for page in named], ["/", "/contact.html"])
        with self.assertRaises(ValueError):
            read_pages.agreed_pages("## Something else\n\nNo pages here.\n")
        pages = read_pages.read_pages(self.site.base)
        self.assertEqual([page["name"] for page in pages], [page["name"] for page in agreed])
        for item, page in zip(agreed, pages):
            self.assertEqual(page["address"], read_pages.page_address(self.site.base, item["path"]))
            self.assertIn("Title:", read_pages.format_page_list([page]))
            self.assertIn("Address:", read_pages.format_page_list([page]))
            self.assertIn("Status:", read_pages.format_page_list([page]))

    def test_pages_contain_the_shared_answers(self):
        """This only checks that the answer text is on the pages, not that the assistant answers."""
        text_by_name = {}
        for agreed in read_pages.agreed_pages():
            url = read_pages.page_address(self.site.base, agreed["path"])
            _status, _html, text, _title = fetch_page(url)
            text_by_name[agreed["name"]] = text
        self.assertIn("tankless water heaters", text_by_name["Services"].lower())
        self.assertIn("same-day service", text_by_name["Services"].lower())
        self.assertIn("call-out fee", text_by_name["Services"].lower())
        self.assertIn("saturday", text_by_name["Hours & FAQ"].lower())
        self.assertIn("financing", text_by_name["Hours & FAQ"].lower())
        self.assertIn("don't install or service septic systems", text_by_name["Hours & FAQ"].lower())
        self.assertIn("fully licensed and insured in new jersey", text_by_name["Hours & FAQ"].lower())
        self.assertIn("emergencies after hours too", text_by_name["Hours & FAQ"].lower())
        self.assertIn("(856) 555-0142", text_by_name["Hours & FAQ"])
        self.assertIn("cherry hill", text_by_name["Service Area"].lower())
        self.assertIn("drain cleaning", text_by_name["Pricing"].lower())
        for name, text in text_by_name.items():
            amounts = PRICE.findall(text)
            if name == "Pricing":
                self.assertEqual(len(amounts), 1)
            elif name == "Services":
                self.assertEqual(amounts, ["$99"])
            else:
                self.assertEqual(amounts, [], name)

    def test_sample_site_uses_only_the_agreed_contact(self):
        """The sample pages use only the agreed phone number and name Carla."""
        agreements = (ROOT / "docs" / "agreements.md").read_text(encoding="utf-8")
        self.assertIn("(856) 555-0142", agreements)
        blobs = []
        for path in sorted((ROOT / "sample-site").iterdir()):
            if path.suffix in {".html", ".css"}:
                blobs.append(path.read_text(encoding="utf-8"))
        combined = "\n".join(blobs)
        self.assertEqual(PHONE.findall(combined), ["(856) 555-0142", "(856) 555-0142"])
        self.assertEqual(EMAIL.findall(combined), [])
        self.assertIn("Carla", combined)
        _status, _html, text, _title = fetch_page(read_pages.page_address(self.site.base, "/contact.html"))
        self.assertIn("(856) 555-0142", text)
        self.assertIn("Carla", text)

    def test_command_prints_a_page_list(self):
        """Reading the pages prints a page list, and uses the local sample site when no address is given."""
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = read_pages.main([self.site.base])
        self.assertEqual(code, 0)
        text = stdout.getvalue()
        self.assertTrue(text.startswith("Page list\n"))
        for agreed in read_pages.agreed_pages():
            self.assertIn(agreed["name"], text)
            self.assertIn(read_pages.page_address(self.site.base, agreed["path"]), text)
        self.assertEqual(text.count("Status: read"), len(read_pages.agreed_pages()))
        self.assertNotIn("unreadable", text)
        self.assertEqual(
            read_pages.DEFAULT_SITE,
            f"http://{serve_sample_site.DEFAULT_HOST}:{serve_sample_site.DEFAULT_PORT}",
        )
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = read_pages.main([])
        self.assertEqual(code, 0)
        text = stdout.getvalue()
        self.assertTrue(text.startswith("Page list\n"))
        for agreed in read_pages.agreed_pages():
            self.assertIn(read_pages.page_address(read_pages.DEFAULT_SITE, agreed["path"]), text)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(read_pages.main(["--help"]), 2)
        self.assertIn("Usage:", stderr.getvalue())
        self.assertIn(read_pages.DEFAULT_SITE, stderr.getvalue())

    def test_a_busy_port_prints_a_friendly_message(self):
        """When the port is already in use, you get a short message and the script stops."""
        held = serve_sample_site.make_server("127.0.0.1", 0)
        try:
            port = held.server_address[1]
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = serve_sample_site.main(["--port", str(port)])
        finally:
            held.server_close()
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue().strip(),
            f"The sample site is already running on port {port}. "
            "Stop it with Ctrl+C, or start on another port with --port.",
        )
        self.assertNotIn("Traceback", stderr.getvalue())


FIRST_QUESTIONS = [
    "Do you service tankless water heaters?",
    "Are you open Saturdays?",
    "How much is a drain cleaning?",
    "Do you cover Cherry Hill?",
    "Can I get same-day service?",
    "Do you offer financing?",
]
GROUP_HEADING = re.compile(r"^\*\*(.+?)\*\*$")
QUESTION_LINE = re.compile(r"^(\d+)\.\s+(.+)$")
FROM_PAGE = re.compile(r"\bfrom\s+(.+?)\.?$")
AGREEMENTS = ROOT / "docs" / "agreements.md"


def _agreements_text():
    return AGREEMENTS.read_text(encoding="utf-8")


def _section_lines(heading):
    found = False
    lines = []
    for line in _agreements_text().splitlines():
        if line.startswith("## "):
            if found:
                break
            found = line[3:].strip() == heading
            continue
        if found:
            lines.append(line)
    if not found:
        raise AssertionError(f"missing section {heading}")
    return lines


def blockquote(heading):
    parts = []
    for line in _section_lines(heading):
        stripped = line.strip()
        if not stripped.startswith(">"):
            continue
        part = stripped[1:].strip()
        if part:
            parts.append(part)
    return " ".join(parts)


def question_rows():
    rows = []
    group = None
    for line in _section_lines("The 15 test questions"):
        bold = GROUP_HEADING.match(line.strip())
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


class QuestionCoverageChecks(unittest.TestCase):
    def test_every_question_has_an_answer_plan(self):
        """Every test question has an answer plan, an answered question names one of your pages, and the drain-cleaning question is answered from Pricing."""
        rows = question_rows()
        agreed = {page["name"]: page["path"] for page in read_pages.agreed_pages()}
        self.assertEqual(len(rows), 15)
        self.assertEqual([row["number"] for row in rows], list(range(1, 16)))
        self.assertEqual([row["question"] for row in rows[:6]], FIRST_QUESTIONS)
        groups = []
        for row in rows:
            if not groups or groups[-1] != row["group"]:
                groups.append(row["group"])
        self.assertEqual(
            groups,
            [
                "Answered by your pages",
                "Handled by a set reply",
                "Answered by your pages",
            ],
        )
        by_group = {}
        for row in rows:
            by_group.setdefault(row["group"], []).append(row)
        self.assertEqual(
            [row["number"] for row in by_group["Answered by your pages"]],
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14, 15],
        )
        self.assertEqual(len(by_group["Handled by a set reply"]), 3)
        self.assertNotIn("Yours to decide", _agreements_text())

        for row in by_group["Answered by your pages"]:
            name = page_named(row["detail"])
            self.assertIn(name, agreed, row["question"])
            self.assertTrue(_sample_file(agreed[name]).is_file(), row["question"])
        for row in rows:
            if row["group"] != "Answered by your pages":
                self.assertIsNone(page_named(row["detail"]), row["question"])

        handled = by_group["Handled by a set reply"]
        urgent_rows = [row for row in handled if "urgent reply" in row["detail"].lower()]
        callback_rows = [row for row in handled if "callback" in row["detail"].lower()]
        self.assertEqual(len(urgent_rows), 1)
        self.assertEqual(len(callback_rows), 2)
        handled_questions = {row["question"] for row in handled}
        covered = {row["question"] for row in urgent_rows + callback_rows}
        self.assertEqual(covered, handled_questions)

        urgent_quote = blockquote("Urgent messages")
        callback_quote = blockquote("When the pages don't say")
        self.assertTrue(urgent_quote)
        self.assertTrue(callback_quote)
        self.assertNotEqual(urgent_quote, callback_quote)
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        how = (ROOT / "docs" / "how-it-works.md").read_text(encoding="utf-8")
        for quote in (urgent_quote, callback_quote):
            self.assertNotIn(quote, behaviour)
            self.assertNotIn(quote, readme)
            self.assertNotIn(quote, how)

        drain = next(row for row in rows if row["question"] == "How much is a drain cleaning?")
        self.assertEqual(page_named(drain["detail"]), "Pricing")
        amount = PRICE.search(drain["detail"])
        self.assertIsNotNone(amount)
        pricing_page = (ROOT / "sample-site" / "pricing.html").read_text(encoding="utf-8")
        self.assertIn("drain cleaning", pricing_page.lower())
        self.assertIn(amount.group(0), pricing_page)

        saturday = next(row for row in rows if row["question"] == "Are you open Saturdays?")
        hours = (ROOT / "sample-site" / "hours.html").read_text(encoding="utf-8")
        stamps = re.findall(r"\d{1,2}:\d{2} am to \d{1,2}:\d{2} pm", saturday["detail"])
        self.assertTrue(stamps, saturday["detail"])
        for stamp in stamps:
            self.assertIn(stamp, hours)
        self.assertIn("sunday: closed", hours.lower())

        contact = (ROOT / "sample-site" / "contact.html").read_text(encoding="utf-8").lower()
        self.assertIn("book or cancel", contact)

        call_out = next(row for row in rows if row["question"] == "How much is a call-out?")
        self.assertEqual(page_named(call_out["detail"]), "Services")
        fee = PRICE.search(call_out["detail"])
        self.assertIsNotNone(fee)
        services = (ROOT / "sample-site" / "services.html").read_text(encoding="utf-8")
        self.assertIn(fee.group(0), services)
        self.assertIn("The call-out fee is $99.", services)

        area = (ROOT / "sample-site" / "service-area.html").read_text(encoding="utf-8").lower()
        self.assertNotIn("moorestown", area)
        self.assertNotIn("water heater", pricing_page.lower())
        self.assertNotIn("How long is your warranty?", [row["question"] for row in rows])
        faq_answers = {
            13: "No, we don't install or service septic systems.",
            14: "Yes, we're fully licensed and insured in New Jersey.",
            15: "Yes, we handle emergencies after hours too. Just call our main line at (856) 555-0142.",
        }
        self.assertNotIn("Waiting for the Hours & FAQ page", _agreements_text())
        for number, sentence in faq_answers.items():
            row = next(item for item in rows if item["number"] == number)
            self.assertEqual(row["group"], "Answered by your pages", number)
            self.assertEqual(page_named(row["detail"]), "Hours & FAQ", number)
            self.assertIn(sentence, hours, number)
        questions = {item["number"]: item["question"].lower() for item in rows}
        self.assertIn("septic", questions[13])
        self.assertIn("licensed", questions[14])
        self.assertIn("after-hours", questions[15])


def _sample_file(path):
    relative = "index.html" if path == "/" else path.lstrip("/")
    return ROOT / "sample-site" / relative


if __name__ == "__main__":
    unittest.main()
