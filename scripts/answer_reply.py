"""Write a short answer from the business's pages."""

import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import read_pages
from answer_kinds.claude import _message_text, _post_message
from answer_kinds.fixed import (
    callback_reply,
    discount_reply,
    off_topic_reply,
    outage_reply,
    unlisted_service_reply,
)
from answer_kinds.instructions import (
    CORRECT_A_WRONG_PRICE,
    FACT_FIRST,
    HOW_MUCH_IS_NOT_YES,
    MISSPELLED_SERVICE,
    NAME_EVERY_PAGE,
    NO_INTERNAL_NOTE,
    PLAIN_PRICE,
    PRICED_SERVICE_IS_OFFERED,
    WRONG_AMOUNT_GETS_A_NO,
    build_instructions,
)
from answer_kinds.notes import PAGE_NOTE_WINDOW
from answer_kinds.pages import normalize_source_line
from answer_kinds.stand_in import ANSWERED_GROUP, stand_in_writer
from answer_kinds.write import without_internal_notes, write_answer

ROOT = Path(__file__).resolve().parents[1]
KEY_ENV = "ANTHROPIC_API_KEY"
MODEL_ENV = "CLAUDE_MODEL"
DEFAULT_MODEL = "claude-haiku-5-5"
MESSAGES_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
# A failed or hung call should not leave the customer waiting.
TIMEOUT_SECONDS = 15
# The owner reads this on the computer that runs the assistant.
# A failed call records the time and the kind of error.
# A page that can't be read records the time, the page name, and the kind of error.
FAILURE_LOG = ROOT / "logs" / "error-notes.log"
MAX_TOKENS = 1024
USAGE = (
    'Usage: python3 scripts/answer_reply.py "customer question" [site address]\n'
    "Prints a short answer from your pages, ending with the page it used.\n"
    "When the pages don't cover the question, prints the callback reply.\n"
    "When the question is clearly about something else, prints the off-topic reply.\n"
    "When the call fails, prints the outage reply.\n"
    "With ANTHROPIC_API_KEY set, Claude writes the answer. With no key, a stand-in answers.\n"
    f"With no address, reads {read_pages.DEFAULT_SITE}."
)


def _split_site(args):
    if args and (args[-1].startswith("http://") or args[-1].startswith("https://")):
        return args[:-1], args[-1]
    return args, None


def main(argv=None):
    """Print one answer for a customer question."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or any(arg in {"-h", "--help"} for arg in args):
        print(USAGE, file=sys.stderr)
        return 2
    words, base = _split_site(args)
    if not words:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        site = read_pages.DEFAULT_SITE if base is None else base
        reply = write_answer(" ".join(words), read_pages.read_pages(site))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
