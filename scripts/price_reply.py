"""Check an answer for prices before it is shown.

Reads your pages with the page reader and keeps an amount only when it
is written there, exactly as written. If an answer contains any other
amount, the whole answer is replaced with the callback reply from your
agreements. An answer with no amount is left as it is. An urgent
message is handled first, and your pages are not read for it.

Usage: python3 scripts/price_reply.py "answer" [site address]

With no address, reads http://127.0.0.1:8000, the address the sample
site prints by default.
"""

import re
import sys
from pathlib import Path

import read_pages
import urgent_reply

ROOT = Path(__file__).resolve().parents[1]
AGREEMENTS = ROOT / "docs" / "agreements.md"
CALLBACK_HEADING = "When the pages don't say"
# A dollar amount, or a number of dollars.
# A comma is part of the amount only when it separates thousands.
_AMOUNT = re.compile(
    r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?"
    r"|(?<![\d,.])\d{1,3}(?:,\d{3})+(?:\.\d+)?\s+dollars?(?!\w)"
    r"|(?<![\d,.])\d+(?:\.\d+)?\s+dollars?(?!\w)",
    re.IGNORECASE,
)
USAGE = (
    'Usage: python3 scripts/price_reply.py "answer" [site address]\n'
    "Prints the answer when every amount in it is written on your pages.\n"
    "Otherwise prints the callback reply.\n"
    f"With no address, reads {read_pages.DEFAULT_SITE}."
)


def _body(text):
    if text is None:
        return AGREEMENTS.read_text(encoding="utf-8")
    return text


def _section(body, heading):
    found = False
    lines = []
    for line in body.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            if found:
                break
            found = title == heading
            continue
        if found:
            lines.append(line)
    if not found:
        raise ValueError(f"Your agreements have no section {heading}.")
    return lines


def find_amounts(text):
    """Return each money amount in text, exactly as written, in order."""
    if not isinstance(text, str) or not text:
        return []
    return [match.group(0) for match in _AMOUNT.finditer(text)]


def callback_reply(text=None):
    """Return the callback reply from your agreements."""
    parts = []
    for line in _section(_body(text), CALLBACK_HEADING):
        stripped = line.strip()
        if not stripped.startswith(">"):
            continue
        part = stripped[1:].strip()
        if part:
            parts.append(part)
    if not parts:
        raise ValueError("The callback reply is missing from your agreements.")
    return " ".join(parts)


def published_amounts(base_url=None, page_text=None):
    """Return amounts written on your pages, in the order they are read.

    page_text, when given, is used instead of fetching. Otherwise the
    pages are read with the page reader. An unreadable page contributes
    nothing. Each amount is kept exactly as written.
    """
    if page_text is not None:
        blobs = [page_text]
    else:
        base = read_pages.DEFAULT_SITE if base_url is None else base_url
        blobs = []
        for page in read_pages.read_pages(base):
            if page.get("status") != "read":
                continue
            blobs.append(f"{page.get('title', '')} {page.get('text', '')}")
    found = []
    seen = set()
    for blob in blobs:
        for amount in find_amounts(blob):
            if amount not in seen:
                seen.add(amount)
                found.append(amount)
    return found


def checked_answer(answer, base_url=None, page_text=None, text=None):
    """Return the answer, or the callback reply when a price is not published.

    An answer with no amount is returned unchanged. A published amount
    must match the pages character for character.
    """
    if not isinstance(answer, str):
        return answer
    amounts = find_amounts(answer)
    if not amounts:
        return answer
    allowed = set(published_amounts(base_url, page_text))
    if all(amount in allowed for amount in amounts):
        return answer
    return callback_reply(text)


def answer_for(message, answer, base_url=None, page_text=None, text=None):
    """Handle an urgent message first, then check prices before showing an answer.

    When the message is urgent, the fixed urgent reply is returned and
    your pages are not read.
    """
    urgent = urgent_reply.reply_if_urgent(message)
    if urgent is not None:
        return urgent
    return checked_answer(answer, base_url=base_url, page_text=page_text, text=text)


def _split_site(args):
    if args and (args[-1].startswith("http://") or args[-1].startswith("https://")):
        return args[:-1], args[-1]
    return args, None


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or any(arg in {"-h", "--help"} for arg in args):
        print(USAGE, file=sys.stderr)
        return 2
    words, base = _split_site(args)
    if not words:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        reply = checked_answer(" ".join(words), base_url=base)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
