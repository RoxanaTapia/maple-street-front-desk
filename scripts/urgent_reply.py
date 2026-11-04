"""Check a customer message for urgent words before any answer.

Reads the urgent words and the fixed urgent reply from your agreements.
A spelling named beside a word, written as (also ...), counts as that word.
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
URGENT_HEADING = "Urgent messages"
NOT_URGENT = "This message is not urgent."
_BESIDE = re.compile(
    r"\*\*([^*]+)\*\*\s*\(also\s+([^)]+)\)",
    re.IGNORECASE,
)
USAGE = (
    'Usage: python3 scripts/urgent_reply.py "customer message"\n'
    "Prints the fixed urgent reply when the message contains an urgent word.\n"
    "A spelling named beside that word counts too.\n"
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
    for line in _section(_body(text), URGENT_HEADING):
        for word in re.findall(r"\*\*([^*]+)\*\*", line):
            word = word.strip()
            if word:
                words.append(word)
    if not words:
        raise ValueError("No urgent words are listed in your agreements.")
    return words


def fixed_urgent_reply(text=None):
    """Return the fixed urgent reply from your agreements."""
    parts = []
    for line in _section(_body(text), URGENT_HEADING):
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


def _spellings(body, word):
    """Return this urgent word and any spelling named beside it.

    Your agreements write that as (also ...) right after the word.
    """
    forms = [word]
    seen = {word.casefold()}
    for line in _section(body, URGENT_HEADING):
        for match in _BESIDE.finditer(line):
            if match.group(1).strip().casefold() != word.casefold():
                continue
            for part in match.group(2).split(","):
                spelling = part.strip()
                folded = spelling.casefold()
                if spelling and folded not in seen:
                    seen.add(folded)
                    forms.append(spelling)
    return forms


def reply_if_urgent(message, text=None):
    """Return the fixed urgent reply, or None when the message is not urgent.

    Call this before any answer. It does not read your pages.
    A spelling named beside an urgent word counts as that word.
    """
    if not isinstance(message, str) or not message.strip():
        return None
    body = _body(text)
    for word in urgent_words(body):
        if any(_contains_word(message, form) for form in _spellings(body, word)):
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
