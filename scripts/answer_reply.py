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
another one. If that call fails, the outage reply is used instead of
an error, and a short note records when it happened and what kind of
error it was. The customer's message and the key are not in that note.
The outage reply is a different sentence from the callback reply.
A page that can't be read is written to those same notes: the time,
the page name, and the kind of error. The customer's message is not
included. The same page is noted once an hour.

With no key, a stand-in answers the agreed test questions. When a
service has a price on the pages, that price is enough: the stand-in
says yes, includes the price, and names the page. When someone
states a price that differs from the pages, the stand-in speaks to them
directly with the sentence on the pages and does not repeat their amount.
A small misspelling of a service the pages list still finds that service.
When they write a price without a dollar sign and it matches the pages,
the reply is a short yes spoken to them. The stand-in is not a real AI,
and it does not call one. The checks use that path, so they do not show
what a live call would write.
Quotes or markdown around the whole question are set aside before that
comparison, so the same words get the same answer. A dollar sign, a
decimal point, and a hyphen in the question stay as written.

Usage: python3 scripts/answer_reply.py "customer question" [site address]

With no address, reads http://127.0.0.1:8000, the address the sample
site prints by default.
"""

import json
import logging
import os
import re
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import agreed
import price_reply
import read_pages

ROOT = Path(__file__).resolve().parents[1]
ANSWERED_GROUP = agreed.ANSWERED_GROUP
_CLOCK = re.compile(r"\d{1,2}:\d{2} am to \d{1,2}:\d{2} pm", re.IGNORECASE)
# A comma counts only as a thousands separator, so "$149," stays "$149".
_MONEY = re.compile(r"\$(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")
# A number the customer typed without a dollar sign, such as "200".
# A time such as 8:00 is not a price. A number already inside $200 is
# read by the price check instead.
_BARE_NUMBER = re.compile(r"(?<![\d,.])\d{2,}(?:\.\d+)?(?![\d,.])")
# The rule Claude is given. Speak to the person, and leave their amount out.
# The example is the sentence on the Pricing page.
CORRECT_A_WRONG_PRICE = (
    "If they state a price that differs from the pages, speak to them directly "
    "and give the price from the pages, for example: A drain cleaning is $149. "
    "Do not mention the customer, and do not repeat their price."
)
# A listed price is enough. The pages do not have to say "we do" as well.
PRICED_SERVICE_IS_OFFERED = (
    "If a service has a price on these pages, that service is offered. "
    "Say yes, include that price, and name the page."
)
# A small slip in a service name still means that service.
MISSPELLED_SERVICE = (
    "A small misspelling of a service on these pages still means that service. "
    "Answer as you would for the right spelling, in plain words."
)
# The price may be written without a dollar sign. Speak to the person.
PLAIN_PRICE = (
    "If they write a price without a dollar sign and it matches these pages, "
    "answer with a short yes that includes the price as the pages write it. "
    "Speak to them directly, and do not mention the customer."
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
# part of the repo. A failed call records the time and the kind of error.
# A page that can't be read records the time, the page name, and the kind
# of error. The customer's message is not written here.
FAILURE_LOG = ROOT / "logs" / "error-notes.log"
# One note per page per hour. The notes file is the record, so a later
# question, even from a new command, does not write the page again while
# that hour still has a line for it.
PAGE_NOTE_WINDOW = timedelta(hours=1)
_NOTE_LOCK = threading.RLock()
_STAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_strptime = datetime.strptime
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


def callback_reply(text=None):
    """Return the callback sentence from your agreements."""
    return agreed.callback_reply(text)


def outage_reply(text=None):
    """Return the outage sentence from your agreements.

    This is the reply when a call fails. It is a different sentence
    from the callback reply.
    """
    return agreed.outage_reply(text)


def off_topic_reply(text=None):
    """Return the off-topic sentence from your agreements."""
    return agreed.off_topic_reply(text)


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


# Marks that only wrap a question. A dollar sign, a decimal point, and a
# hyphen are not in this list, so a price and a hyphenated word stay.
_SURROUNDING_PAIRS = {
    '"': '"',
    "'": "'",
    "`": "`",
    "*": "*",
    "_": "_",
    "(": ")",
    "[": "]",
    "“": "”",
    "‘": "’",
}


def _without_surrounding_marks(value):
    """Return the question without marks that only wrap it.

    Quotes, markdown, and a question mark come off the outside, one
    layer at a time. The words inside stay, including a dollar sign, a
    decimal point, and a hyphen.
    """
    text = " ".join(value.split())
    while text:
        if text.endswith("?"):
            text = text.rstrip("?").rstrip()
            continue
        if len(text) >= 2 and _SURROUNDING_PAIRS.get(text[0]) == text[-1]:
            text = text[1:-1].strip()
            continue
        if text.startswith(">"):
            text = text[1:].strip()
            continue
        if text.startswith("#"):
            rest = text.lstrip("#")
            if rest != text and (not rest or rest[:1].isspace()):
                text = rest.strip()
                continue
        break
    return text


def _same_question(left, right):
    def norm(value):
        bare = _without_surrounding_marks(value)
        return " ".join(bare.casefold().split()).rstrip("?")

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
    for start, end, written in price_reply.amount_spans(question):
        covered.append((start, end))
        number = _price_number(written)
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
    """Return the page price when the question states a different one.

    The sentence is the one on the page, beside that service, spoken
    to the person. Their amount is not copied into it. Returns None
    when there is nothing to correct.
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


# Words that can sit in a note about the person and do not add a fact.
# A sentence is dropped only when every other word is already in the
# rest of the reply, so a separate fact is kept.
_NARRATION_WORDS = frozenset(
    {
        "about",
        "amount",
        "amounts",
        "been",
        "figure",
        "gave",
        "given",
        "had",
        "has",
        "price",
        "prices",
        "quoted",
        "said",
        "says",
        "stated",
        "their",
        "them",
        "they",
        "was",
        "were",
        "wrong",
    }
)


def _folded(text):
    return " ".join(text.casefold().split())


def _sentences(text):
    """Return the sentences in text, with the end mark kept."""
    parts = []
    start = 0
    for end in price_reply.sentence_ends(text):
        piece = text[start:end].strip()
        if piece:
            parts.append(piece)
        start = end
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _content_words(sentence):
    """Return words that could be a fact, ignoring a note about the person."""
    words = []
    for match in _WORD.finditer(sentence.casefold()):
        word = match.group(0)
        if word in _STOP or word in price_reply.NOT_A_SERVICE or word == "customer":
            continue
        if word in _NARRATION_WORDS:
            continue
        words.append(word)
    return words


def _mentions_the_customer(text):
    return "the customer" in _folded(text)


def _same_number(left, right):
    return left is not None and right is not None and left == right


def _page_price_number(direct):
    amounts = price_reply.find_amounts(direct)
    if len(amounts) != 1:
        return None
    return _price_number(amounts[0])


def _draft_passes_price_check(question, reply, pages):
    """True when the price check would let this exact draft through."""
    checked = price_reply.checked_answer(reply, pages=pages, message=question)
    return checked == reply


def _agrees_without_the_page_price(reply, page_number):
    """True when a draft agrees with the stated price and never gives the page price."""
    numbers = _stated_price_numbers(reply)
    if any(_same_number(number, page_number) for number in numbers):
        return False
    folded = _folded(reply)
    if re.search(r"\byes\b", folded):
        return True
    if re.search(r"\b(is|are|was|were)\s+right\b", folded):
        return True
    return False


def _repeats_stated_price(question, reply, page_number):
    """True when the draft repeats the price from the question.

    A bare number such as 200 counts. The price check does not see that
    form, so it has to be caught here. The price on the page does not count.
    """
    stated = _stated_price_numbers(question)
    for number in _stated_price_numbers(reply):
        if _same_number(number, page_number):
            continue
        if any(_same_number(number, item) for item in stated):
            return True
    return False


def _anchored_sentence(sentence):
    """True when this sentence stays, whatever the other sentences say.

    A note about the customer can be removed. A sentence with an amount,
    or one that does not mention the customer, cannot. Another note is
    not an anchor, so two copies of the same fact cannot delete each other.
    """
    if not _mentions_the_customer(sentence):
        return True
    if price_reply.find_amounts(sentence) or _stated_price_numbers(sentence):
        return True
    return False


def _narration_sentence(sentence, kept_text):
    """True when this sentence is only a note and its facts are already kept."""
    if not _anchored_sentence(sentence) and _mentions_the_customer(sentence):
        kept_words = set(_WORD.findall(kept_text.casefold()))
        return all(word in kept_words for word in _content_words(sentence))
    return False


def _without_narration(reply, page_number):
    """Drop a note about the customer when an anchored sentence already has its facts.

    The page sentence is not written in its place. A fact is anchored when
    it sits in a sentence that will stay. A repeated note is not that
    anchor, so at least one copy of the fact remains. Returns the original
    reply when shortening would drop a fact or the page price.
    """
    sentences = _sentences(reply)
    if len(sentences) < 2:
        return reply
    anchored = " ".join(sentence for sentence in sentences if _anchored_sentence(sentence))
    kept = []
    dropped = False
    for sentence in sentences:
        if _narration_sentence(sentence, anchored):
            dropped = True
            continue
        kept.append(sentence)
    if not dropped or not kept:
        return reply
    cleaned = " ".join(kept).strip()
    if not any(_same_number(number, page_number) for number in _stated_price_numbers(cleaned)):
        return reply
    kept_words = set(_WORD.findall(cleaned.casefold()))
    if any(word not in kept_words for word in _content_words(reply)):
        return reply
    return cleaned


def _direct_price_reply(question, reply, pages, instructions, callback):
    """Shorten a note about the customer only when the draft is already safe.

    The price check is applied to the original draft before anything is
    removed. A draft that names another amount is left as it is, so that
    check can reject it. A draft that agrees with the stated price, or
    repeats that price without a dollar sign, becomes the callback reply.
    It is not replaced with the price on the page. A draft that already
    states only that price may lose a note that says "the customer", and
    every other sentence stays.
    """
    if not isinstance(reply, str) or not _mentions_the_customer(reply):
        return reply
    direct = _correct_stated_price(question, pages, instructions)
    if not isinstance(direct, str):
        return reply
    page_number = _page_price_number(direct)
    if page_number is None:
        return reply
    if not _draft_passes_price_check(question, reply, pages):
        return reply
    if _repeats_stated_price(question, reply, page_number):
        return callback
    if _agrees_without_the_page_price(reply, page_number):
        return callback
    if not any(_same_number(number, page_number) for number in _stated_price_numbers(reply)):
        return reply
    cleaned = _without_narration(reply, page_number)
    if cleaned == reply or not _draft_passes_price_check(question, cleaned, pages):
        return reply
    return cleaned


def build_instructions(question, pages, text=None):
    """Build the instructions an AI would be given for this question.

    The instructions say to answer only from these pages, keep it short,
    name the page, end with From and that page name, and use the callback
    sentence when the pages don't cover the question. When someone states
    a price that differs from the pages, they say to speak to that person
    directly, give the price from the pages, and not mention the customer
    or repeat their price. When a service has a price on the pages, they
    say to treat that service as offered, say yes, include the price, and
    name the page. A small misspelling of a service still means that
    service. A price written without a dollar sign, when it matches the
    pages, gets a short yes spoken to the person. The text of every page
    is included.
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
        PRICED_SERVICE_IS_OFFERED,
        MISSPELLED_SERVICE,
        PLAIN_PRICE,
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


def _asks_whether_offered(question):
    """True when the customer is asking if a service is offered."""
    if not isinstance(question, str):
        return False
    bare = _without_surrounding_marks(question)
    return re.match(r"(?:do you|can you|will you)\b", bare.casefold()) is not None


def _service_name(snippet, amount):
    """Return the service words in a price sentence, without the amount."""
    text = snippet.replace(amount, " ")
    text = re.sub(r"[.!?]", " ", text)
    text = " ".join(text.split())
    text = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+\b(?:is|are|costs|cost)\b.*$", "", text, flags=re.IGNORECASE)
    name = text.strip()
    if not name or not re.search(r"[a-z]", name, re.IGNORECASE):
        return None
    return name


def _states_yes_or_no(sentences):
    """True when these lines already say yes or no."""
    text = " ".join(sentences).casefold()
    return re.search(r"\b(yes|no)\b", text) is not None


def _priced_service_reply(question, pages, instructions):
    """Say yes when a page lists a price for the service asked about.

    The pages do not have to say "we do" that job in other words. The
    price has to sit in one sentence, near the service. Returns None
    when this is not a "do you" question, or when no page lists a price
    for it.
    """
    if not _asks_whether_offered(question) or not isinstance(instructions, str):
        return None
    words = price_reply.service_words(question)
    if not words:
        return None
    best = None
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
            amount = amounts[0]
            if not price_reply.price_is_near_service(snippet, amount, words):
                continue
            service = _service_name(snippet, amount)
            if not service:
                continue
            score = (len(words), len(service))
            if best is not None and score <= best[0]:
                continue
            reply = _with_source([f"Yes, we do {service}. It's {amount}."], name)
            best = (score, reply)
    if best is None:
        return None
    return best[1]


def _priced_snippet(question, pages, instructions):
    """Return the price sentence, the page name, and the amount, or None.

    The price has to sit in one sentence, near the service. A small
    misspelling of a service word still counts.
    """
    words = price_reply.service_words(question)
    if not words or not isinstance(instructions, str):
        return None
    best = None
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
            amount = amounts[0]
            if not price_reply.price_is_near_service(snippet, amount, words):
                continue
            score = (len(words), len(snippet))
            if best is not None and score <= best[0]:
                continue
            best = (score, snippet, name, amount)
    if best is None:
        return None
    return best[1], best[2], best[3]


def _yes_sentence(snippet, name):
    """Turn a page price sentence into a short yes to the customer."""
    sentence = snippet.strip()
    if sentence.endswith("."):
        sentence = sentence[:-1]
    if sentence[:1].isupper():
        sentence = sentence[:1].lower() + sentence[1:]
    return _with_source([f"Yes, {sentence}."], name)


def _yes_matching_price(question, pages, instructions):
    """Return a short yes when the stated price matches the page.

    The customer may write the amount without a dollar sign. The reply
    uses the price as the page writes it, and it speaks to them.
    Returns None when the stated price differs, or when none was stated.
    """
    stated = _stated_price_numbers(question)
    if not stated:
        return None
    found = _priced_snippet(question, pages, instructions)
    if found is None:
        return None
    snippet, name, amount = found
    page_number = _price_number(amount)
    if page_number is None:
        return None
    if not all(_same_number(number, page_number) for number in stated):
        return None
    return _yes_sentence(snippet, name)


def _has_small_misspelling(words, snippet, amount):
    """True when a service word is only a small misspelling of the sentence."""
    nearby = price_reply.words_near_amount(snippet, amount)
    if not nearby:
        return False
    for word in words:
        exact = any(
            word == near or price_reply.service_stem(word) == price_reply.service_stem(near)
            for near in nearby
        )
        if exact:
            continue
        slipped = any(
            price_reply.one_edit(word, near)
            or price_reply.one_edit(
                price_reply.service_stem(word),
                price_reply.service_stem(near),
            )
            for near in nearby
        )
        if slipped:
            return True
    return False


def _misspelled_price(question, pages, instructions):
    """Return the page price when the service is only slightly misspelled.

    The sentence is the one on the page. Returns None when every service
    word is already exact, or when no priced sentence matches.
    """
    words = price_reply.service_words(question)
    found = _priced_snippet(question, pages, instructions)
    if found is None or not words:
        return None
    snippet, name, amount = found
    if not _has_small_misspelling(words, snippet, amount):
        return None
    return _with_source([snippet], name)


def stand_in_writer(question, instructions, pages, text=None):
    """Answer the agreed test questions. This is not a real AI.

    It reads those questions from your agreements and answers one only
    when the named page's text is in the instructions and supports the
    answer. Quotes or markdown around that question count as the same
    question. A plain question about opening hours is answered from the
    Hours page the same way. When someone states a price that differs
    from the pages, the answer is the sentence beside that service,
    spoken to them, and their amount is not repeated. When they state
    the price the pages already show, even without a dollar sign, the
    answer is a short yes that uses the page's price. A small misspelling
    of a service still gets that service's price. When a question asks
    whether a service is offered, and a page lists a price for it, the
    answer says yes, includes that price, and names the page. The pages
    do not have to say "we do" that job in other words. A service the
    pages never mention gets the callback sentence.
    """
    callback = callback_reply(text)
    if not isinstance(question, str) or not question.strip():
        return callback
    if not isinstance(instructions, str):
        return callback
    row = None
    for item in agreed.question_rows(text):
        if _same_question(item["question"], question):
            row = item
            break
    if row is not None and row["group"] != ANSWERED_GROUP:
        return callback
    offered = _priced_service_reply(question, pages, instructions)
    if row is None:
        return (
            _hours_answer(question, pages, instructions)
            or _correct_stated_price(question, pages, instructions)
            or _yes_matching_price(question, pages, instructions)
            or offered
            or _misspelled_price(question, pages, instructions)
            or callback
        )
    name = _source_page(row["detail"])
    if not name:
        return offered or callback
    page = None
    for item in pages or []:
        if item.get("name") == name:
            page = item
            break
    if page is None or page.get("status") != "read":
        return offered or callback
    page_text = page.get("text") or ""
    if not page_text or page_text not in instructions:
        return offered or callback
    sentences = _supporting(page_text, question, row["detail"])
    if sentences and _states_yes_or_no(sentences):
        return _with_source(sentences, name)
    matching = _yes_matching_price(question, pages, instructions)
    if matching:
        return matching
    if offered:
        return offered
    if not sentences:
        return _misspelled_price(question, pages, instructions) or callback
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


def _write_owner_note(detail):
    """Append one line to the owner's error notes.

    The line starts with the time. detail is the rest: the kind of
    error, or the page name and the kind of error. The customer's
    message is not added. A problem saving the note returns False.
    """
    when = datetime.now(timezone.utc).strftime(_STAMP_FORMAT)
    line = f"{when} {detail}\n"
    try:
        with _NOTE_LOCK:
            FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
            with FAILURE_LOG.open("a", encoding="utf-8") as handle:
                handle.write(line)
    except OSError:
        logging.warning("The failure note could not be saved.")
        return False
    return True


def _page_noted_recently(name, now):
    """True when this page already has a note inside the hour."""
    try:
        text = FAILURE_LOG.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    prefix = f"{name}: "
    for line in text.splitlines():
        stamp, _, rest = line.partition(" ")
        if not rest.startswith(prefix):
            continue
        try:
            seen = _strptime(stamp, _STAMP_FORMAT).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if now - seen < PAGE_NOTE_WINDOW:
            return True
    return False


def _note_unreadable_pages(pages):
    """Note each page that could not be read, at most once an hour.

    The note is the time, the page name, and the kind of error. The
    customer's message is not included. A later question about the same
    page, inside that hour, does not add another line. A different page
    is noted on its own.
    """
    now = datetime.now(timezone.utc)
    with _NOTE_LOCK:
        for page in pages or []:
            if not isinstance(page, dict) or page.get("status") != "unreadable":
                continue
            name = " ".join(str(page.get("name", "")).split())
            if not name:
                continue
            if _page_noted_recently(name, now):
                continue
            reason = " ".join(str(page.get("reason") or "unreadable").split())
            if not reason:
                reason = "unreadable"
            if not _write_owner_note(f"{name}: {reason}"):
                continue
            logging.warning("A page could not be read (%s: %s).", name, reason)


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
    _write_owner_note(kind)
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


def _plain_customer_price(question, reply, pages, instructions):
    """Replace a note about the customer when their price matches the page.

    The short yes uses the price as the page writes it. A reply that
    names a different amount is left as it is, so the price check can
    reject it. A reply that does not mention the customer is left as it is.
    """
    if not isinstance(reply, str) or not _mentions_the_customer(reply):
        return reply
    plain = _yes_matching_price(question, pages, instructions)
    if not isinstance(plain, str):
        return reply
    page_number = _page_price_number(plain)
    if page_number is None:
        return reply
    numbers = _stated_price_numbers(reply)
    if not numbers or any(not _same_number(number, page_number) for number in numbers):
        return reply
    if not _draft_passes_price_check(question, plain, pages):
        return reply
    return plain


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
    used by the checks. If the call fails, the outage reply is returned
    and a short note records when it happened and what kind of error it
    was. The customer's message and the key are not in that note. The
    outage reply is not the callback sentence.
    With no key and no client, the stand-in answers the agreed test questions.
    A service with a price on the pages is offered: the reply says yes,
    includes that price, and names the page. A plumbing question the
    pages don't cover still gets the callback reply.

    A page-based answer is rewritten so it ends with exactly
    'From <Page name>.'. The callback reply and the outage reply are
    left as they are. A wrong-price note that already states only the
    page price may lose the words "the customer", and the other sentences
    stay. A note that agrees with the stated price, or names another
    amount, is not replaced with the page price. When the price they
    wrote matches the pages, even without a dollar sign, a note about
    the customer becomes a short yes spoken to them.

    A page that can't be read is noted for the owner before the reply
    is chosen. The note does not change the reply. The customer's
    message is not part of the note.
    """
    try:
        _note_unreadable_pages(pages)
    except Exception:
        logging.warning("The failure note could not be saved.")
    if _is_off_topic(question):
        return off_topic_reply(text)
    instructions = build_instructions(question, pages, text=text)
    callback = callback_reply(text)
    outage = outage_reply(text)
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
            return outage
    if isinstance(reply, str) and reply.strip() == outage:
        return outage
    reply = normalize_source_line(reply, pages, callback)
    reply = _plain_customer_price(question, reply, pages, instructions)
    return _direct_price_reply(question, reply, pages, instructions, callback)


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
