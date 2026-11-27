"""Say a price to the customer, with no note about them."""

import re

import price_reply

from answer_kinds.prices import (
    _correct_stated_price,
    _price_number,
    _stated_price_numbers,
    _yes_matching_price,
)
from answer_kinds.text import _STOP, _WORD, _folded, _same_number, _sentences

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
    """True when the draft repeats the price from the question."""
    stated = _stated_price_numbers(question)
    for number in _stated_price_numbers(reply):
        if _same_number(number, page_number):
            continue
        if any(_same_number(number, item) for item in stated):
            return True
    return False


def _anchored_sentence(sentence):
    """True when this sentence stays, whatever the other sentences say."""
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
    """Drop a note about the customer when an anchored sentence already has its facts."""
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
    """Shorten a note about the customer only when the draft is already safe."""
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


def _plain_customer_price(question, reply, pages, instructions):
    """Replace a note about the customer when their price matches the page."""
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
