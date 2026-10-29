"""Checks for the sample site and the page list."""

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
        serve_sample_site.pricing_live = False
        self.site = RunningSite()

    def tearDown(self):
        self.site.close()
        serve_sample_site.pricing_live = False

    def test_pricing_switch_defaults_to_off(self):
        """Pricing stays switched off until you turn it on."""
        source = (SCRIPTS / "serve_sample_site.py").read_text(encoding="utf-8")
        self.assertRegex(source, r"(?m)^pricing_live = False\b")

    def test_pricing_off_reads_five_and_flags_pricing(self):
        """While Pricing is down, the other five pages are read and Pricing is marked unreadable."""
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

    def test_pricing_on_reads_all_six(self):
        """When Pricing is live, all six pages are read and each title matches."""
        serve_sample_site.pricing_live = True
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

    def test_every_page_shows_the_fictional_banner(self):
        """Every page shows the banner that this business is fictional."""
        serve_sample_site.pricing_live = True
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
        statuses = {page["name"]: page["status"] for page in agreed}
        self.assertEqual(statuses["Pricing"], "pending")
        for name in AGREED_NAMES:
            if name != "Pricing":
                self.assertEqual(statuses[name], "agreed", name)
        pages = read_pages.read_pages(self.site.base)
        self.assertEqual([page["name"] for page in pages], [page["name"] for page in agreed])
        for item, page in zip(agreed, pages):
            self.assertEqual(page["address"], read_pages.page_address(self.site.base, item["path"]))
            self.assertIn("Title:", read_pages.format_page_list([page]))
            self.assertIn("Address:", read_pages.format_page_list([page]))
            self.assertIn("Status:", read_pages.format_page_list([page]))

    def test_pages_contain_the_shared_answers(self):
        """This only checks that the answer text is on the pages, not that the assistant answers."""
        serve_sample_site.pricing_live = True
        text_by_name = {}
        for agreed in read_pages.agreed_pages():
            url = read_pages.page_address(self.site.base, agreed["path"])
            _status, _html, text, _title = fetch_page(url)
            text_by_name[agreed["name"]] = text
        self.assertIn("tankless water heaters", text_by_name["Services"].lower())
        self.assertIn("same-day service", text_by_name["Services"].lower())
        self.assertIn("saturday", text_by_name["Hours & FAQ"].lower())
        self.assertIn("financing", text_by_name["Hours & FAQ"].lower())
        self.assertIn("cherry hill", text_by_name["Service Area"].lower())
        self.assertIn("drain cleaning", text_by_name["Pricing"].lower())
        for name, text in text_by_name.items():
            amounts = PRICE.findall(text)
            if name == "Pricing":
                self.assertEqual(len(amounts), 1)
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
        self.assertEqual(PHONE.findall(combined), ["(856) 555-0142"])
        self.assertEqual(EMAIL.findall(combined), [])
        self.assertIn("Carla", combined)
        _status, _html, text, _title = fetch_page(read_pages.page_address(self.site.base, "/contact.html"))
        self.assertIn("(856) 555-0142", text)
        self.assertIn("Carla", text)

    def test_command_prints_a_page_list(self):
        """Reading the pages prints a page list, and asks for the site address when it is missing."""
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = read_pages.main([self.site.base])
        self.assertEqual(code, 0)
        text = stdout.getvalue()
        self.assertTrue(text.startswith("Page list\n"))
        for agreed in read_pages.agreed_pages():
            self.assertIn(agreed["name"], text)
            self.assertIn(read_pages.page_address(self.site.base, agreed["path"]), text)
        self.assertIn("Status: read", text)
        self.assertIn("Status: unreadable (", text)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(read_pages.main([]), 2)
        self.assertIn("Usage:", stderr.getvalue())


DAVE_QUESTIONS = [
    "Do you service tankless water heaters?",
    "Are you open Saturdays?",
    "How much is a drain cleaning?",
    "Do you cover Cherry Hill?",
    "Can I get same-day service?",
    "Do you offer financing?",
]
COVERAGE = (
    "answered by the pages",
    "not on the pages, so the callback reply applies",
    "needs dave",
    "the fixed urgent reply applies",
)
PAGE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def question_rows():
    text = (ROOT / "docs" / "agreements.md").read_text(encoding="utf-8")
    rows = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            if in_section:
                break
            in_section = line[3:].strip() == "Test questions"
            continue
        if not in_section or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] == "Question":
            continue
        if all(not cell.strip(":- ") for cell in cells):
            continue
        rows.append(
            {
                "question": cells[0],
                "page": cells[1],
                "answer": cells[2],
                "status": cells[3],
            }
        )
    return rows


class QuestionCoverageChecks(unittest.TestCase):
    def test_every_question_has_a_status_and_answered_pages_are_agreed(self):
        """Every test question has a status, and an answered question points at an agreed page."""
        rows = question_rows()
        agreed = {page["name"]: page["path"] for page in read_pages.agreed_pages()}
        self.assertEqual(len(rows), 15)
        self.assertEqual([row["question"] for row in rows[:6]], DAVE_QUESTIONS)
        proposed = [row for row in rows if "Proposed, to confirm with Dave." in row["status"]]
        self.assertEqual(len(proposed), 9)
        agreements = (ROOT / "docs" / "agreements.md").read_text(encoding="utf-8")
        dave_list = agreements.split("### Questions for Dave", 1)[1]
        bullets = [line for line in dave_list.splitlines() if line.startswith("- ")]
        self.assertEqual(len(bullets), 9)

        for row in rows:
            self.assertTrue(row["status"], row["question"])
            coverage = [phrase for phrase in COVERAGE if phrase in row["status"].lower()]
            self.assertEqual(len(coverage), 1, row["question"])
            if row["question"] in DAVE_QUESTIONS:
                self.assertTrue(row["status"].startswith("Draft."), row["question"])
            else:
                self.assertTrue(row["status"].startswith("Proposed, to confirm with Dave."), row["question"])
            if "answered by the pages" in row["status"].lower():
                match = PAGE_LINK.search(row["page"])
                self.assertIsNotNone(match, row["question"])
                name, href = match.group(1), match.group(2)
                self.assertIn(name, agreed, row["question"])
                self.assertEqual((ROOT / "docs" / href).resolve(), _sample_file(agreed[name]).resolve())
            else:
                self.assertEqual(row["page"], "None", row["question"])
            if row["question"] == "How much is a drain cleaning?":
                self.assertIn("once Pricing is live", row["answer"])
        hours = (ROOT / "sample-site" / "hours.html").read_text(encoding="utf-8").lower()
        contact = (ROOT / "sample-site" / "contact.html").read_text(encoding="utf-8").lower()
        self.assertIn("sunday: closed", hours)
        self.assertIn("book or cancel", contact)


def _sample_file(path):
    relative = "index.html" if path == "/" else path.lstrip("/")
    return ROOT / "sample-site" / relative


if __name__ == "__main__":
    unittest.main()
