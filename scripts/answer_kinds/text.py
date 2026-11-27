"""Shared helpers for a question, a word, and a short line from a page."""

import re

import price_reply

_CLOCK = re.compile(r"\d{1,2}:\d{2} am to \d{1,2}:\d{2} pm", re.IGNORECASE)


# A comma counts only as a thousands separator, so "$149," stays "$149".
_MONEY = re.compile(r"\$(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")


# A number the customer typed without a dollar sign, such as "200".
# A time such as 8:00 is not a price. A number already inside $200 is
# read by the price check instead.
_BARE_NUMBER = re.compile(r"(?<![\d,.])\d{2,}(?:\.\d+)?(?![\d,.])")


# An address such as owner@shop.test. The contact page does not have one.
_EMAIL_ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


# The main line, as the contact page writes it, such as 030 0000 0000.
_PHONE = re.compile(r"\(\d{3}\) \d{3}-\d{4}|\d{3} \d{4} \d{4}")


_WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


# The page reader keeps the navigation in the visible text, glued to the
# first sentence. These openings are the short lines a customer can read.
# A following "Just ..." sentence stays with that line, so the after-hours
# answer keeps the phone number written beside it.
_SNIPPET = re.compile(
    r"\b(?:Yes|No|The|A|An|To|We|Sunday|Saturday|Monday|"
    r"Tuesday|Wednesday|Thursday|Friday|Main line)\b"
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
    """Return the question without marks that only wrap it."""
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


def _same_number(left, right):
    return left is not None and right is not None and left == right


def _asks_whether_offered(question):
    """True when the customer is asking if a service is offered."""
    if not isinstance(question, str):
        return False
    bare = _without_surrounding_marks(question)
    return re.match(r"(?:do you|can you|will you)\b", bare.casefold()) is not None


def _asks_how_much(question):
    """True when the customer asks how much, which is not a yes or no question."""
    if not isinstance(question, str):
        return False
    bare = _without_surrounding_marks(question)
    return re.search(r"\bhow\s+much\b", bare, re.IGNORECASE) is not None


def _asks_for_a_fact(question):
    """True when the question is how, what, when, or where."""
    if not isinstance(question, str):
        return False
    bare = _without_surrounding_marks(question)
    return re.match(r"(?:how|what|when|where)\b", bare, re.IGNORECASE) is not None


def _fact_first(question, reply):
    """Drop a leading Yes when the question asks how, what, when, or where."""
    if not isinstance(reply, str) or not _asks_for_a_fact(question):
        return reply
    text = reply.strip()
    rest = re.sub(r"^yes\b\s*,?\s*", "", text, count=1, flags=re.IGNORECASE)
    if not rest or rest == text:
        return reply
    if rest[0].islower():
        rest = rest[0].upper() + rest[1:]
    return rest
