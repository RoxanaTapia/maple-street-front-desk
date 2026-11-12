"""Read the agreed sentences and the test questions.

The urgent reply, the two call-us sentences, the off-topic reply, and
the 18 test questions all live in docs/agreements.md. This module is
the one reader, so the other scripts do not keep their own copy.

Usage is through the other scripts. There is nothing to run here.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGREEMENTS = ROOT / "docs" / "agreements.md"
QUESTIONS_HEADING = "The 18 test questions"
ANSWERED_GROUP = "Answered by your pages"
_FROM_PAGE = re.compile(r"\bfrom\s+(.+?)\.?$", re.IGNORECASE)


def body(text=None):
    """Return the agreements page, or text when a caller already has it."""
    if text is None:
        return AGREEMENTS.read_text(encoding="utf-8")
    return text


def section_lines(heading, text=None, missing=None):
    """Return the lines under a heading. The next heading ends the section."""
    found = False
    lines = []
    for line in body(text).splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            if found:
                break
            found = title == heading
            continue
        if found:
            lines.append(line)
    if not found:
        if missing is None:
            missing = f"Your agreements have no section {heading}."
        raise ValueError(missing)
    return lines


def blockquote(heading, text=None, missing=None):
    """Return the quoted lines under heading, joined into one sentence.

    An empty quote is returned as an empty string. A missing heading
    raises ValueError.
    """
    parts = []
    for line in section_lines(heading, text, missing=missing):
        stripped = line.strip()
        if not stripped.startswith(">"):
            continue
        part = stripped[1:].strip()
        if part:
            parts.append(part)
    return " ".join(parts)


def require_blockquote(heading, text=None, missing="The reply is missing from your agreements."):
    """Return the quoted sentence, or raise when it is missing."""
    quote = blockquote(heading, text)
    if not quote:
        raise ValueError(missing)
    return quote


def callback_reply(text=None):
    """Return the call-us sentence used when the pages don't cover a question."""
    return require_blockquote(
        "When the pages don't say",
        text,
        "The callback reply is missing from your agreements.",
    )


def outage_reply(text=None):
    """Return the call-us sentence used when a lookup fails."""
    return require_blockquote(
        "When the assistant can't look it up",
        text,
        "The outage reply is missing from your agreements.",
    )


def off_topic_reply(text=None):
    """Return the off-topic sentence from your agreements."""
    return require_blockquote(
        "Off-topic questions",
        text,
        "The off-topic reply is missing from your agreements.",
    )


def fixed_urgent_reply(text=None):
    """Return the fixed urgent reply from your agreements."""
    return require_blockquote(
        "Urgent messages",
        text,
        "The fixed urgent reply is missing from your agreements.",
    )


def question_rows(text=None):
    """Return each agreed test question, in the order it is written.

    A bold line is the group name. The question ends at the question
    mark, and the rest of the line is the detail. number is the
    number written on the line.
    """
    rows = []
    group = None
    for line in section_lines(QUESTIONS_HEADING, text):
        bold = re.fullmatch(r"\*\*(.+?)\*\*", line.strip())
        if bold:
            group = bold.group(1).strip()
            continue
        match = re.match(r"^(\d+)\.\s+(.+)$", line.strip())
        if not match or not group:
            continue
        raw = match.group(2).strip()
        mark = raw.find("?")
        if mark == -1:
            question, detail = raw, ""
        else:
            question = raw[: mark + 1].strip()
            detail = raw[mark + 1 :].strip()
        rows.append(
            {
                "number": int(match.group(1)),
                "question": question,
                "detail": detail,
                "group": group,
            }
        )
    if not rows:
        raise ValueError("No test questions are listed in your agreements.")
    return rows


def page_named(detail):
    """Return the page name after 'from' in a question's detail, or None."""
    if not isinstance(detail, str):
        return None
    match = _FROM_PAGE.search(detail.strip())
    if not match:
        return None
    return match.group(1).strip()
