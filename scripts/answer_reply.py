"""Write a short answer from the business's pages.

This is part 3 of the path. It takes a customer question and the page
text from the page reader, and it builds the instructions for the answer:
answer only from these pages, keep it short, and end with From and the
page name. It uses the callback sentence from the agreements when the
pages don't cover a plumbing question. A question that is clearly about
something else gets the off-topic reply from the agreements, and neither
Claude nor the stand-in is called. Anything we do not recognize stays
on the answer path. The text of every page is included.

When ANTHROPIC_API_KEY is set, Claude writes the answer through the
Messages API. A small, fast model is used unless CLAUDE_MODEL names
another one. If that call fails, the callback reply is used instead of
an error, and a short note records when it happened and what kind of
error it was. The customer's message and the key are not in that note.

With no key, a stand-in answers the agreed test questions. When the
customer states a price that differs from the pages, the stand-in gives
the price from the pages and does not repeat the customer's amount.
The stand-in is not a real AI, and it does not call one. The checks use
that path.

Usage: python3 scripts/answer_reply.py "customer question" [site address]

With no address, reads http://127.0.0.1:8000, the address the sample
site prints by default.
"""

import json
import logging
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import price_reply
import read_pages

ROOT = Path(__file__).resolve().parents[1]
AGREEMENTS = ROOT / "docs" / "agreements.md"
CALLBACK_HEADING = "When the pages don't say"
OFF_TOPIC_HEADING = "Off-topic questions"
QUESTIONS_HEADING = "The 15 test questions"
ANSWERED_GROUP = "Answered by your pages"
_CLOCK = re.compile(r"\d{1,2}:\d{2} am to \d{1,2}:\d{2} pm", re.IGNORECASE)
# A comma counts only as a thousands separator, so "$149," stays "$149".
_MONEY = re.compile(r"\$(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")
# A number the customer typed without a dollar sign, such as "200".
# A time such as 8:00 is not a price. A number already inside $200 is
# read by the price check instead.
_BARE_NUMBER = re.compile(r"(?<![\d,.])\d{2,}(?:\.\d+)?(?![\d,.])")
# The rule Claude is given. The customer's own amount stays out of the reply.
CORRECT_A_WRONG_PRICE = (
    "When the customer states a price that differs from the pages, "
    "correct them by giving the price from the pages, and do not repeat "
    "the customer's amount."
)
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
# The friendly reply is only for a request that is clearly about one of
# these subjects. Anything else, including a word we have not listed,
# stays on the answer path. The pages are not consulted.
_UNRELATED = frozenset(
    {
        "pizza",
        "burger",
        "taco",
        "sushi",
        "coffee",
        "weather",
        "forecast",
        "movie",
        "film",
        "cinema",
        "joke",
        "song",
        "football",
        "basketball",
        "soccer",
        "recipe",
        "homework",
        "tax",
        "taxes",
    }
)
# Words that can sit next to an unrelated subject without being a second
# request. A weekday, "open", or "hours" must not send "pizza on Saturday"
# to the model. This list is not read from the pages.
_ASIDE = frozenset(
    {
        "saturday",
        "saturdays",
        "sunday",
        "sundays",
        "monday",
        "mondays",
        "tuesday",
        "tuesdays",
        "wednesday",
        "wednesdays",
        "thursday",
        "thursdays",
        "friday",
        "fridays",
        "today",
        "tomorrow",
        "tonight",
        "weekend",
        "morning",
        "afternoon",
        "evening",
        "open",
        "opened",
        "closed",
        "hour",
        "hours",
        "service",
        "services",
        "business",
        "maple",
        "street",
        "local",
        "here",
        "there",
        "sell",
        "selling",
        "sold",
        "buy",
        "buying",
        "order",
        "ordering",
        "deliver",
        "delivery",
        "recommend",
        "watch",
        "watching",
        "want",
        "wanted",
        "like",
        "love",
        "need",
        "needed",
        "make",
        "making",
        "serve",
        "serving",
        "eat",
        "eating",
        "some",
        "any",
        "good",
        "best",
        "hot",
        "cold",
        "large",
        "small",
        "please",
        "thanks",
        "thank",
        "during",
        "while",
        "after",
        "before",
        "about",
        "just",
        "also",
        "really",
        "very",
    }
)
KEY_ENV = "ANTHROPIC_API_KEY"
MODEL_ENV = "CLAUDE_MODEL"
DEFAULT_MODEL = "claude-haiku-5-5"
MESSAGES_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
# Short on purpose: a failed or hung call must not leave the customer waiting.
TIMEOUT_SECONDS = 15
# The owner reads this on the computer that runs the assistant. It is not
# part of the repo. The line is the time and the kind of error only.
FAILURE_LOG = ROOT / "logs" / "claude-failures.log"
MAX_TOKENS = 1024
USAGE = (
    'Usage: python3 scripts/answer_reply.py "customer question" [site address]\n'
    "Prints a short answer from your pages, ending with the page it used.\n"
    "When a plumbing question is not on the pages, prints the callback reply.\n"
    "When the question is clearly about something else, prints the off-topic reply.\n"
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


def off_topic_reply(text=None):
    """Return the off-topic sentence from your agreements."""
    parts = []
    for line in _section(_agreements(text), OFF_TOPIC_HEADING):
        stripped = line.strip()
        if not stripped.startswith(">"):
            continue
        part = stripped[1:].strip()
        if part:
            parts.append(part)
    if not parts:
        raise ValueError("The off-topic reply is missing from your agreements.")
    return " ".join(parts)


def _singular(word):
    """Return word without a trailing s, so pizzas matches pizza.

    This is not a prefix match. "business" does not become a shorter word
    that then matches something else.
    """
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _unrelated_subject(word):
    """True when this word is one of the clearly unrelated subjects."""
    return word in _UNRELATED or _singular(word) in _UNRELATED


def _is_off_topic(question):
    """True only when the question is clearly about something else.

    A dripping tap, a payment question, or a plumbing job we have not
    named stays on the answer path. The business's pages are not read
    for this decision, so a change in their wording cannot move it.
    A weekday, "open", or "hours" beside pizza does not send that
    question to the model. Another unrecognized word does: pizza plus
    a dripping tap stays on the answer path.
    """
    if not isinstance(question, str) or not question.strip():
        return False
    words = []
    for word in _WORD.findall(question.casefold()):
        if word in _STOP or len(word) < 3:
            continue
        words.append(word)
    if not any(_unrelated_subject(word) for word in words):
        return False
    for word in words:
        if _unrelated_subject(word) or word in _ASIDE or _singular(word) in _ASIDE:
            continue
        return False
    return True


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


def _price_number(amount):
    """Return the number in a written price, or None when it isn't one."""
    cleaned = re.sub(r"[^\d.]", "", amount)
    if not cleaned or cleaned == "." or cleaned.count(".") > 1:
        return None
    return float(cleaned)


def _stated_price_numbers(question):
    """Return the prices the customer stated, as numbers.

    A dollar amount counts, and so does a bare number such as 200.
    A time such as 8:00 does not.
    """
    if not isinstance(question, str) or not question:
        return []
    numbers = []
    covered = []
    for match in price_reply._AMOUNT.finditer(question):
        covered.append(match.span())
        number = _price_number(match.group(0))
        if number is not None:
            numbers.append(number)
    for match in _BARE_NUMBER.finditer(question):
        start, end = match.span()
        if any(span_start <= start and end <= span_end for span_start, span_end in covered):
            continue
        if start > 0 and question[start - 1] == ":":
            continue
        if end < len(question) and question[end] == ":":
            continue
        number = _price_number(match.group(0))
        if number is not None:
            numbers.append(number)
    return numbers


def _correct_stated_price(question, pages, instructions):
    """Return the page price when the customer stated a different one.

    The sentence is the one on the page, beside that service. The
    customer's amount is not copied into it. Returns None when there
    is nothing to correct.
    """
    stated = _stated_price_numbers(question)
    if not stated or not isinstance(instructions, str):
        return None
    words = price_reply.service_words(question)
    if not words:
        return None
    for page in pages or []:
        if not isinstance(page, dict) or page.get("status") != "read":
            continue
        name = page.get("name")
        page_text = page.get("text") or ""
        if not isinstance(name, str) or not name.strip():
            continue
        if not page_text or page_text not in instructions:
            continue
        for snippet in _snippets(page_text):
            amounts = price_reply.find_amounts(snippet)
            if len(amounts) != 1:
                continue
            if not price_reply.price_is_near_service(snippet, amounts[0], words):
                continue
            page_number = _price_number(amounts[0])
            if page_number is None or any(number == page_number for number in stated):
                continue
            return _with_source([snippet], name)
    return None


def build_instructions(question, pages, text=None):
    """Build the instructions an AI would be given for this question.

    The instructions say to answer only from these pages, keep it short,
    name the page, end with From and that page name, and use the callback
    sentence when the pages don't cover the question. When the customer
    states a price that differs from the pages, they say to give the price
    from the pages and not repeat the customer's amount. The text of every
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
        CORRECT_A_WRONG_PRICE,
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
    Hours page the same way. When the customer states a price that
    differs from the pages, the answer is the price written beside that
    service, and the customer's amount is not repeated. Anything the
    pages don't cover gets the callback sentence.
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
        return (
            _hours_answer(question, pages, instructions)
            or _correct_stated_price(question, pages, instructions)
            or callback
        )
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


def _failure_kind(error):
    """Return a fixed label for a failed Claude call.

    The label is chosen from the kind of failure. The customer message
    and the key are not read, and they are not part of the label.
    """
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, urllib.error.HTTPError):
        code = error.code
        if code in (401, 403):
            return "key missing or expired"
        if code == 408:
            return "timeout"
        if isinstance(code, int) and code >= 500:
            return "Claude is down"
        return "call failed"
    if isinstance(error, urllib.error.URLError):
        if isinstance(error.reason, TimeoutError):
            return "timeout"
        return "Claude is down"
    if isinstance(error, ConnectionError):
        return "Claude is down"
    if type(error) is RuntimeError and error.args == ("missing key",):
        return "key missing or expired"
    if type(error) is ValueError and error.args == ("empty reply",):
        return "empty reply"
    return "call failed"


def _note_call_failure(error):
    """Record a failed Claude call for the owner.

    The note is one line: when it happened, and what kind of error it
    was. The same note is logged as a warning. The customer message and
    the key are left out. A problem saving the note does not change the
    reply the customer gets.
    """
    kind = _failure_kind(error)
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with FAILURE_LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"{when} {kind}\n")
    except OSError:
        logging.warning("The failure note could not be saved.")
    logging.warning("Claude could not answer (%s).", kind)


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

    A question that is clearly about something else returns the off-topic
    reply from your agreements. Claude, the stand-in, and a supplied
    writer are not called for it. Anything else is written as usual, and
    a plumbing or payment question the pages don't cover still gets the
    callback reply.

    With no writer, Claude writes the answer when ANTHROPIC_API_KEY is
    set, or when client is given. client is a stand-in for the HTTP call,
    used by the checks. If the call fails, the callback reply is returned
    and a short note records when it happened and what kind of error it
    was. The customer's message and the key are not in that note.
    With no key and no client, the stand-in answers the agreed test questions.
    A plumbing question the pages don't cover still gets the callback reply.

    A page-based answer is rewritten so it ends with exactly
    'From <Page name>.'. The callback reply is left as it is.
    """
    if _is_off_topic(question):
        return off_topic_reply(text)
    instructions = build_instructions(question, pages, text=text)
    callback = callback_reply(text)
    if writer is not None:
        reply = writer(question, instructions, pages)
    elif client is None and not _api_key():
        reply = stand_in_writer(question, instructions, pages, text=text)
    else:
        try:
            reply = _claude_reply(instructions, client=client)
        except Exception as error:
            try:
                _note_call_failure(error)
            except Exception:
                logging.warning("Claude could not answer.")
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
