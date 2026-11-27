"""Automated tests for the calm demo chat screen.

CalmScreenChecks is the "The empty chat screen stays calm" area.
The docstring of each test is what the checklist prints.

Run one area with
python3 scripts/run_checks.py tests/test_calm_screen.py:CalmScreenChecks.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import demo_chat

PAGE = ROOT / "demo" / "index.html"
SCRIPT = ROOT / "demo" / "chat.js"
STYLE = ROOT / "demo" / "style.css"

GREETING = "Hi, I'm the Maple Street front desk."
HELP = "How can I help?"
DISCLAIMER = (
    "Demo for a fictional plumbing business. "
    "It only answers from Maple Street Plumbing's pages."
)
CHIPS = (
    "It's Saturday night and my sink is leaking",
    "How much is drain cleaning?",
    "Water heater price?",
    "Do you sell pizza?",
)
FOOTER_LINK = "https://roxanatapia.dev/cases/front-desk"
VOICE_LINES = (
    "A live chat assistant. Voice is the next step.",
    "Next: the same rules on a phone call",
)


class CalmScreenChecks(unittest.TestCase):
    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.style = STYLE.read_text(encoding="utf-8")

    def test_the_voice_lines_are_gone(self):
        """The voice lines are gone from the chat page."""
        for line in VOICE_LINES:
            self.assertNotIn(line, self.page)
        self.assertNotIn("voice", self.page.casefold())
        self.assertNotIn('class="next"', self.page)
        self.assertNotIn('class="next-card"', self.page)

    def test_the_proof_link_is_gone(self):
        """The 15 of 15 link is gone from the chat page."""
        self.assertNotIn("15 of 15", self.page)
        self.assertNotIn("/docs/test-results.md", self.page)
        self.assertNotIn('class="proof"', self.page)

    def test_the_empty_chat_shows_a_greeting_and_the_chips(self):
        """The empty chat shows the greeting and the four chips."""
        thread = self.page.index('id="thread"')
        empty = self.page.index('id="empty"')
        greeting = self.page.index(GREETING)
        help_line = self.page.index(HELP)
        chips = self.page.index('id="chips"')
        composer = self.page.index('id="composer"')
        self.assertLess(thread, empty)
        self.assertLess(empty, greeting)
        self.assertLess(greeting, help_line)
        self.assertLess(help_line, chips)
        self.assertLess(chips, composer)
        self.assertIn(DISCLAIMER, self.page)
        self.assertNotIn('class="scene"', self.page)
        self.assertNotIn("Water everywhere, pipe burst!", self.page)
        for message in CHIPS:
            self.assertIn(f'data-message="{message}"', self.page)
            self.assertLess(chips, self.page.index(f'data-message="{message}"'))
        self.assertIn("justify-content: center", self.style)

    def test_the_greeting_leaves_when_a_conversation_starts(self):
        """The greeting and chips leave when a conversation starts."""
        send = self.script.split("function send", 1)[1]
        self.assertIn('getElementById("empty")', self.script)
        self.assertLess(send.index("clearEmpty"), send.index("addCustomer"))
        self.assertIn("removeChild", self.script.split("function clearEmpty", 1)[1])

    def test_the_footer_matches_the_demo_kit_slot(self):
        """The footer is the shared line, and How it's built opens the case notes."""
        composer = self.page.index('id="composer"')
        footer_at = self.page.index('<footer class="dk-footer">')
        self.assertLess(composer, footer_at)
        footer = self.page.split('<footer class="dk-footer">', 1)[1].split("</footer>", 1)[0]
        self.assertIn('class="dk-footer-slot"', footer)
        self.assertNotIn("Tested with automated tests.", self.page)
        self.assertNotIn('class="tested"', self.page)
        self.assertNotIn(".tested", self.style)
        self.assertNotIn("github.com/RoxanaTapia/maple-street-front-desk", self.page)
        self.assertNotIn("Exit demo", self.page)
        self.assertNotIn("Log out", self.page)
        self.assertNotIn('id="demo-exit"', self.page)
        back = self.page.index('class="dk-back" href="https://roxanatapia.dev/">Back to portfolio</a>')
        self.assertLess(back, self.page.index('class="dk-note"'))
        self.assertNotIn("target=", self.page.split('class="dk-back"', 1)[1].split("</a>", 1)[0])
        built = footer.index('href="https://roxanatapia.dev/">Built by Roxana Tapia</a>')
        case = footer.index(f'href="{FOOTER_LINK}">How it\'s built</a>')
        book = footer.index(
            'href="__BOOKING_URL__" target="_blank" rel="noopener noreferrer">Book a call</a>'
        )
        self.assertLess(built, case)
        self.assertLess(case, book)
        self.assertEqual(footer.count("·"), 2)
        self.assertNotIn('target="_blank"', footer[:case])
        url = demo_chat.booking_page()
        self.assertTrue(url.startswith("https://calendar.google.com/calendar/appointments/"))
        served = demo_chat.chat_page()
        self.assertIn(
            f'href="{url}" target="_blank" rel="noopener noreferrer">Book a call</a>',
            served,
        )
        self.assertNotIn("__BOOKING_URL__", served)
        self.assertIsNone(re.search(r"\bchecks\b", self.page, re.IGNORECASE))
        self.assertIn(".dk-footer-slot a {\n  color: var(--color-muted);\n", self.style)
        self.assertNotIn("Tested with automated tests.", served)
        back_css = self.style.split(".dk-back", 1)[1].split("}", 1)[0]
        self.assertIn("color: var(--color-muted)", back_css)
        self.assertIn(':root[data-theme="dark"] .dk-back', self.style)

    def test_the_chat_page_has_no_em_dash(self):
        """The chat page has no em dash."""
        for text in (self.page, self.script, self.style):
            self.assertNotIn("—", text)
            self.assertNotIn("–", text)
        self.assertIsNone(re.search(r"\bsmall\b", self.page, re.IGNORECASE))
        self.assertIn("fictional", self.page)
        self.assertIn('<label class="visually-hidden" for="message">Message</label>', self.page)
        self.assertIn('aria-describedby="message-hint"', self.page)
        self.assertIn("Press Enter to send. Shift+Enter adds a new line.", self.page)
        self.assertIn("@media (min-width: 800px)", self.style)
        self.assertIn(".composer:focus-within .hint", self.style)


if __name__ == "__main__":
    unittest.main()
