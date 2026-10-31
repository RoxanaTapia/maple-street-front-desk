"""Check a customer message for urgent words before any answer.

Reads the urgent words and the fixed urgent reply from your agreements.
When the message contains one of those words, that reply is used on its
own and your pages are not read. Anything else is not urgent, and an
answer can come in a later step.

Usage: python3 scripts/urgent_reply.py "customer message"
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGREEMENTS = ROOT / "docs" / "agreements.md"
URGENT_WORDS_HEADING = "Urgent words"
FIXED_REPLY_HEADING = "Fixed urgent reply"
NOT_URGENT = "This message is not urgent."
USAGE = (
    'Usage: python3 scripts/urgent_reply.py "customer message"\n'
    "Prints the fixed urgent reply when the message contains an urgent word.\n"
    "Otherwise prints that the message is not urgent."
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


def urgent_words(text=None):
    """Return the urgent words from your agreements."""
    words = []
    for line in _section(_body(text), URGENT_WORDS_HEADING):
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        for word in re.findall(r'"([^"]+)"', stripped):
            word = word.strip()
            if word:
                words.append(word)
    if not words:
        raise ValueError("No urgent words are listed in your agreements.")
    return words


def fixed_urgent_reply(text=None):
    """Return the fixed urgent reply from your agreements."""
    parts = []
    for line in _section(_body(text), FIXED_REPLY_HEADING):
        stripped = line.strip()
        if not stripped.startswith(">"):
            continue
        part = stripped[1:].strip()
        if part:
            parts.append(part)
    if not parts:
        raise ValueError("The fixed urgent reply is missing from your agreements.")
    return " ".join(parts)


def _contains_word(message, word):
    pattern = r"(?<!\w)" + re.escape(word.casefold()) + r"(?!\w)"
    return re.search(pattern, message.casefold()) is not None


def reply_if_urgent(message, text=None):
    """Return the fixed urgent reply, or None when the message is not urgent.

    Call this before any answer. It does not read your pages.
    """
    if not isinstance(message, str) or not message.strip():
        return None
    body = _body(text)
    if any(_contains_word(message, word) for word in urgent_words(body)):
        return fixed_urgent_reply(body)
    return None


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or any(arg in {"-h", "--help"} for arg in args):
        print(USAGE, file=sys.stderr)
        return 2
    try:
        reply = reply_if_urgent(" ".join(args))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(NOT_URGENT if reply is None else reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
