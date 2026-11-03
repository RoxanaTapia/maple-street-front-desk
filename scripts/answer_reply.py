"""Write a short answer from the business's pages.

This is part 3 of the path. It takes a customer question and the page
text from the page reader, and it builds the instructions for the answer:
answer only from these pages, keep it short, and end with From and the
page name. It uses the callback sentence from the agreements when the
pages don't cover the question. The text of every page is included.

When ANTHROPIC_API_KEY is set, Claude writes the answer through the
Messages API. A small, fast model is used unless CLAUDE_MODEL names
another one. If that call fails, the callback reply is used instead of
an error.

With no key, a stand-in answers the agreed test questions. The stand-in
is not a real AI, and it does not call one. The checks use that path.

Usage: python3 scripts/answer_reply.py "customer question" [site address]

With no address, reads http://127.0.0.1:8000, the address the sample
site prints by default.
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import read_pages

ROOT = Path(__file__).resolve().parents[1]
AGREEMENTS = ROOT / "docs" / "agreements.md"
CALLBACK_HEADING = "When the pages don't say"
QUESTIONS_HEADING = "The 15 test questions"
ANSWERED_GROUP = "Answered by your pages"
_CLOCK = re.compile(r"\d{1,2}:\d{2} am to \d{1,2}:\d{2} pm", re.IGNORECASE)
# A comma counts only as a thousands separator, so "$149," stays "$149".
_MONEY = re.compile(r"\$(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")
_WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# The page reader keeps the navigation in the visible text, glued to the
# first sentence. These openings are the short lines a customer can read.
# A following "Just ..." sentence stays with that line, so the after-hours
# answer keeps the phone number written beside it.
_SNIPPET = re.compile(
    r"\b(?:Yes|No|The|A|An|To|We|Sunday|Saturday|Monday|Tuesday|Wednesday|Thursday|Friday|Main line)\b"
    r"[^.!?]*(?:[.!?]|$)"
    r"(?:\s+Just [^.!?]*[.!?])?"
)
_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "do",
        "does",
        "did",
        "you",
        "your",
        "our",
        "are",
        "can",
        "could",
        "get",
        "how",
        "much",
        "what",
        "when",
        "where",
        "who",
        "for",
        "from",
        "with",
        "and",
        "that",
        "this",
        "have",
        "should",
        "please",
    }
)
KEY_ENV = "ANTHROPIC_API_KEY"
MODEL_ENV = "CLAUDE_MODEL"
DEFAULT_MODEL = "claude-haiku-5-5"
MESSAGES_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
# Short on purpose: a failed or hung call must not leave the customer waiting.
TIMEOUT_SECONDS = 15
MAX_TOKENS = 1024
USAGE = (
    'Usage: python3 scripts/answer_reply.py "customer question" [site address]\n'
    "Prints a short answer from your pages, naming the page it came from.\n"
    "When the pages don't cover the question, prints the callback reply.\n"
    "With ANTHROPIC_API_KEY set, Claude writes the answer. With no key, a stand-in answers.\n"
    f"With no address, reads {read_pages.DEFAULT_SITE}."
)


def _agreements(text):
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


def callback_reply(text=None):
    """Return the callback sentence from your agreements."""
    parts = []
    for line in _section(_agreements(text), CALLBACK_HEADING):
        stripped = line.strip()
        if not stripped.startswith(">"):
            continue
        part = stripped[1:].strip()
        if part:
            parts.append(part)
    if not parts:
        raise ValueError("The callback reply is missing from your agreements.")
    return " ".join(parts)


def _question_rows(body):
    rows = []
    group = None
    for line in _section(body, QUESTIONS_HEADING):
        bold = re.fullmatch(r"\*\*(.+?)\*\*", line.strip())
        if bold:
            group = bold.group(1).strip()
            continue
        match = re.match(r"^\d+\.\s+(.+)$", line.strip())
        if not match or not group:
            continue
        text = match.group(1).strip()
        mark = text.find("?")
        if mark == -1:
            question, detail = text, ""
        else:
            question = text[: mark + 1].strip()
            detail = text[mark + 1 :].strip()
        rows.append({"question": question, "detail": detail, "group": group})
    if not rows:
        raise ValueError("No test questions are listed in your agreements.")
    return rows


def _same_question(left, right):
    def norm(value):
        return " ".join(value.casefold().split()).rstrip("?")

    return norm(left) == norm(right)


def _source_page(detail):
    match = re.search(r"\bfrom\s+(.+?)\.?$", detail.strip(), re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _tokens(text):
    words = []
    for word in _WORD.findall(text.casefold()):
        if word in _STOP or len(word) < 4:
            continue
        words.append(word)
    return words


def _overlaps(word, tokens):
    for token in tokens:
        if word == token:
            return True
        short, long = (word, token) if len(word) <= len(token) else (token, word)
        if len(short) >= 4 and long.startswith(short):
            return True
    return False


def _snippets(text):
    found = []
    for match in _SNIPPET.finditer(text or ""):
        snippet = " ".join(match.group(0).split()).strip()
        if snippet and snippet not in found:
            found.append(snippet)
    return found


def _supporting(page_text, question, detail):
    """Return short lines from the page that answer the question."""
    snippets = _snippets(page_text)
    wanted = _tokens(question)
    scored = []
    for index, snippet in enumerate(snippets):
        matched = [word for word in wanted if _overlaps(word, _tokens(snippet))]
        if matched:
            scored.append((len(matched), sum(len(word) for word in matched), index, snippet))
    if not scored:
        return []
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_count, best_length = scored[0][0], scored[0][1]
    chosen = []
    for count, length, index, snippet in scored:
        if count == best_count and length == best_length:
            chosen.append((index, snippet))
    facts = _CLOCK.findall(detail) + _MONEY.findall(detail)
    for fact in facts:
        if fact not in page_text:
            return []
        for index, snippet in enumerate(snippets):
            if fact in snippet and not any(index == item[0] for item in chosen):
                chosen.append((index, snippet))
    chosen.sort(key=lambda item: item[0])
    result = [snippet for _index, snippet in chosen]
    joined = " ".join(result)
    for fact in facts:
        if fact not in joined:
            return []
    return result


def _with_source(sentences, name):
    body = " ".join(sentences).strip()
    tag = f"From {name}."
    if not body:
        return tag
    if body.endswith((".", "!", "?")):
        return f"{body} {tag}"
    return f"{body}. {tag}"


def _page_names(pages):
    names = []
    seen = set()
    for page in pages or []:
        if not isinstance(page, dict):
            continue
        name = page.get("name")
        if not isinstance(name, str):
            continue
        name = " ".join(name.split())
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        names.append(name)
    names.sort(key=len, reverse=True)
    return names


def _canonical_name(raw, names):
    folded = " ".join(raw.split()).casefold()
    for name in names:
        if name.casefold() == folded:
            return name
    return None


def _source_example(pages):
    names = _page_names(pages)
    for name in names:
        if name.casefold() == "hours & faq":
            return name
    if names:
        return names[0]
    return "Hours & FAQ"


def normalize_source_line(answer, pages, callback=None):
    """End a page-based answer with exactly 'From <Page name>.'

    A citation such as '(Source: Services page)', a 'Source:' line, or
    '(Hours & FAQ page)' is rewritten to that form. An answer that
    already ends correctly is left as it is. The callback reply is
    returned unchanged, including when a citation was added after it.
    """
    if not isinstance(answer, str):
        return answer
    text = answer.strip()
    if not text:
        return text
    if isinstance(callback, str) and text == callback.strip():
        return callback
    names = _page_names(pages)
    if not names:
        return text
    alternation = "|".join(re.escape(name) for name in names)
    pattern = re.compile(
        rf"""
        ^
        (?P<body>.*?)
        (?:
            \s*
            \(\s*
                (?:source\s*:\s*)?
                (?:from\s+)?
                (?:the\s+)?
                (?P<paren>{alternation})
                (?:\s+page)?
                \s*\.?
            \s*\)
            \s*\.?
          |
            \s+
            (?:source\s*:\s*|from\s+)
            (?:the\s+)?
            (?P<marked>{alternation})
            (?:\s+page)?
            \s*\.?
        )
        \s*$
        """,
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    )
    match = pattern.search(text)
    if not match:
        return text
    raw = match.group("paren") or match.group("marked")
    name = _canonical_name(raw, names)
    if not name:
        return text
    body = (match.group("body") or "").strip()
    if isinstance(callback, str) and body == callback.strip():
        return callback
    return _with_source([body] if body else [], name)


def build_instructions(question, pages, text=None):
    """Build the instructions an AI would be given for this question.

    The instructions say to answer only from these pages, keep it short,
    name the page, end with From and that page name, and use the callback
    sentence when the pages don't cover the question. The text of every
    page is included.
    """
    callback = callback_reply(text)
    example = _source_example(pages)
    lines = [
        "Answer the customer's question only from these pages.",
        "Keep the answer short.",
        "Name the page the answer came from.",
        "End the answer with exactly From <Page name>.",
        f"For example, From {example}.",
        "When the pages don't cover the question, reply with exactly this sentence:",
        callback,
        "",
        f"Customer question: {question}",
        "",
        "Pages:",
    ]
    for page in pages or []:
        name = page.get("name", "")
        if page.get("status") == "read":
            body = page.get("text") or ""
        else:
            reason = page.get("reason") or "unreadable"
            body = f"(unreadable: {reason})"
        lines.append(f"Page: {name}")
        lines.append(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _hours_answer(question, pages, instructions):
    """Answer a plain hours question from the Hours page, or return None."""
    if not _same_question(question, "What are your hours?"):
        return None
    page = None
    for item in pages or []:
        name = item.get("name") if isinstance(item, dict) else None
        if isinstance(name, str) and "hours" in name.casefold():
            page = item
            break
    if page is None or page.get("status") != "read":
        return None
    page_text = page.get("text") or ""
    if not page_text or page_text not in instructions:
        return None
    lines = []
    for snippet in _snippets(page_text):
        if _CLOCK.search(snippet) or re.search(r"\bclosed\b", snippet, re.IGNORECASE):
            lines.append(snippet)
    if not lines:
        return None
    return _with_source(lines, page.get("name"))


def stand_in_writer(question, instructions, pages, text=None):
    """Answer the agreed test questions. This is not a real AI.

    It reads those questions from your agreements and answers one only
    when the named page's text is in the instructions and supports the
    answer. A plain question about opening hours is answered from the
    Hours page the same way. Anything the pages don't cover gets the
    callback sentence.
    """
    callback = callback_reply(text)
    if not isinstance(question, str) or not question.strip():
        return callback
    if not isinstance(instructions, str):
        return callback
    row = None
    for item in _question_rows(_agreements(text)):
        if _same_question(item["question"], question):
            row = item
            break
    if row is not None and row["group"] != ANSWERED_GROUP:
        return callback
    if row is None:
        return _hours_answer(question, pages, instructions) or callback
    name = _source_page(row["detail"])
    if not name:
        return callback
    page = None
    for item in pages or []:
        if item.get("name") == name:
            page = item
            break
    if page is None or page.get("status") != "read":
        return callback
    page_text = page.get("text") or ""
    if not page_text or page_text not in instructions:
        return callback
    sentences = _supporting(page_text, question, row["detail"])
    if not sentences:
        return callback
    return _with_source(sentences, name)


def _api_key():
    return os.environ.get(KEY_ENV, "").strip()


def _model_name():
    chosen = os.environ.get(MODEL_ENV, "").strip()
    return chosen or DEFAULT_MODEL


def _message_text(body):
    """Return the text blocks from a Messages API response.

    Thinking blocks are left out. An empty or unexpected body returns "".
    """
    if not isinstance(body, dict):
        return ""
    content = body.get("content")
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return "\n".join(parts).strip()


def _post_message(payload, key, timeout):
    """POST one Messages API request. The key travels in the header only."""
    request = urllib.request.Request(
        MESSAGES_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": API_VERSION,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def _claude_reply(instructions, client=None):
    """Ask Claude with the instructions already built for this question.

    client, when given, is called as client(payload) and stands in for
    the HTTP call. The payload does not include the key. An empty reply
    is a failure.
    """
    payload = {
        "model": _model_name(),
        "max_tokens": MAX_TOKENS,
        "output_config": {"effort": "low"},
        "messages": [{"role": "user", "content": instructions}],
    }
    if client is not None:
        body = client(payload)
    else:
        key = _api_key()
        if not key:
            raise RuntimeError("missing key")
        body = _post_message(payload, key, TIMEOUT_SECONDS)
    text = _message_text(body)
    if not text:
        raise ValueError("empty reply")
    return text


def write_answer(question, pages, writer=None, text=None, client=None):
    """Write an answer for question from the page text.

    writer, when given, is called as writer(question, instructions, pages)
    and replaces both Claude and the stand-in. The instructions are what
    Claude is given: every page, plus the callback sentence.

    With no writer, Claude writes the answer when ANTHROPIC_API_KEY is
    set, or when client is given. client is a stand-in for the HTTP call,
    used by the checks. If the call fails, the callback reply is returned.
    With no key and no client, the stand-in answers the agreed test questions.

    A page-based answer is rewritten so it ends with exactly
    'From <Page name>.'. The callback reply is left as it is.
    """
    instructions = build_instructions(question, pages, text=text)
    callback = callback_reply(text)
    if writer is not None:
        reply = writer(question, instructions, pages)
    elif client is None and not _api_key():
        reply = stand_in_writer(question, instructions, pages, text=text)
    else:
        try:
            reply = _claude_reply(instructions, client=client)
        except Exception:
            return callback
    return normalize_source_line(reply, pages, callback)


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
        site = read_pages.DEFAULT_SITE if base is None else base
        reply = write_answer(" ".join(words), read_pages.read_pages(site))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
