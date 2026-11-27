"""Answer from a price the pages state."""

import re

import price_reply

from answer_kinds.pages import _with_source
from answer_kinds.text import (
    _BARE_NUMBER,
    _asks_how_much,
    _asks_whether_offered,
    _same_number,
    _snippets,
)


def _price_number(amount):
    """Return the number in a written price, or None when it isn't one."""
    cleaned = re.sub(r"[^\d.]", "", amount)
    if not cleaned or cleaned == "." or cleaned.count(".") > 1:
        return None
    return float(cleaned)


def _stated_price_numbers(question):
    """Return the prices the customer stated, as numbers."""
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
    """Return the page price when the question states a different one."""
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
    """Say yes when a page lists a price for the service asked about."""
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
    """Return the price sentence, the page name, and the amount, or None."""
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
    """Return a short yes when the stated price matches the page."""
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


def _how_much_reply(question, pages, instructions):
    """Return the page price for a how much question, with no leading yes."""
    if not _asks_how_much(question) or _stated_price_numbers(question):
        return None
    found = _priced_snippet(question, pages, instructions)
    if found is None:
        return None
    snippet, name, _amount = found
    return _with_source([snippet], name)


def _misspelled_price(question, pages, instructions):
    """Return the page price when the service is only slightly misspelled."""
    words = price_reply.service_words(question)
    found = _priced_snippet(question, pages, instructions)
    if found is None or not words:
        return None
    snippet, name, amount = found
    if not _has_small_misspelling(words, snippet, amount):
        return None
    return _with_source([snippet], name)
