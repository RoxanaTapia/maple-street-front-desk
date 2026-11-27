"""Reply when the pages don't list the email, the job, or the price."""

import re

import price_reply
import urgent_reply

from answer_kinds.fixed import callback_reply
from answer_kinds.prices import _priced_service_reply, _priced_snippet
from answer_kinds.text import (
    _EMAIL_ADDRESS,
    _STOP,
    _WORD,
    _asks_how_much,
    _asks_whether_offered,
    _snippets,
    _without_surrounding_marks,
)

# "Do you clean drains and fix water heaters?" is two jobs.
_TWO_JOBS = re.compile(
    r"^(?:do|can|will)\s+you\s+(.+?)\s+and\s+(.+)$",
    re.IGNORECASE,
)


# Fix and repair name the same missing job. Service does not.
_REPAIR_VERBS = frozenset(
    {
        "fix",
        "fixes",
        "fixing",
        "repair",
        "repairs",
        "repairing",
    }
)


# Verbs that ask whether a service is offered. The words after them name it.
_SERVICE_VERBS = frozenset(
    {
        "fix",
        "fixes",
        "fixing",
        "repair",
        "repairs",
        "repairing",
        "install",
        "installs",
        "installing",
        "replace",
        "replaces",
        "replacing",
        "service",
        "services",
        "servicing",
        "clean",
        "cleans",
        "cleaning",
    }
)


def _is_service_verb(word):
    """True when this word asks us to do a job, such as fix or install."""
    stem = price_reply.service_stem(word)
    return word in _SERVICE_VERBS or stem in _SERVICE_VERBS


def _listed_word(word, page_words):
    """True when this word, or a small slip of it, is written on the pages."""
    for other in page_words:
        if word == other or price_reply.service_stem(word) == price_reply.service_stem(other):
            return True
        if price_reply.one_edit(word, other) or price_reply.one_edit(
            price_reply.service_stem(word),
            price_reply.service_stem(other),
        ):
            return True
    return False


def _service_is_unlisted(question, pages):
    """True when they ask us to do a job the pages never name."""
    if not _asks_whether_offered(question):
        return False
    # A page we could not read might be the one that lists the service.
    # Don't claim it is missing until every page has been read.
    for page in pages or []:
        if isinstance(page, dict) and page.get("status") != "read":
            return False
    bare = _without_surrounding_marks(question).casefold()
    names = []
    verbs = False
    for word in _WORD.findall(bare):
        if word in _STOP or len(word) < 3:
            continue
        if _is_service_verb(word):
            verbs = True
            continue
        names.append(word)
    if not verbs or not names:
        return False
    page_words = []
    seen = set()
    for page in pages or []:
        if not isinstance(page, dict) or page.get("status") != "read":
            continue
        blob = f"{page.get('name', '')} {page.get('title', '')} {page.get('text', '')}"
        for match in _WORD.finditer(blob.casefold()):
            word = match.group(0)
            if word in seen:
                continue
            seen.add(word)
            page_words.append(word)
    return any(not _listed_word(word, page_words) for word in names)


def _every_page_was_read(pages):
    """True when every page was read, and at least one page was given."""
    saw_one = False
    for page in pages or []:
        if not isinstance(page, dict):
            continue
        saw_one = True
        if page.get("status") != "read":
            return False
    return saw_one


def _asks_for_email(question):
    """True when the customer asks for an email address."""
    if not isinstance(question, str):
        return False
    return re.search(r"\be-?mails?\b", question, re.IGNORECASE) is not None


def _email_reply_for(question, pages, text=None):
    """Return the email reply when the pages don't list an email address."""
    if not _asks_for_email(question) or not _every_page_was_read(pages):
        return None
    for page in pages or []:
        if not isinstance(page, dict):
            continue
        blob = f"{page.get('name', '')} {page.get('title', '')} {page.get('text', '')}"
        if _EMAIL_ADDRESS.search(blob):
            return None
    return f"The pages don't list an email address. {callback_reply(text)}"


def _two_jobs(question):
    """Return the two jobs in a do-you question, or None."""
    if not isinstance(question, str):
        return None
    bare = _without_surrounding_marks(question).rstrip("?").strip()
    match = _TWO_JOBS.match(bare)
    if not match:
        return None
    left = match.group(1).strip(" ,")
    right = match.group(2).strip(" ,")
    if not left or not right:
        return None
    return left, right


def _repair_verb(word):
    """True when this word means fix or repair."""
    stem = price_reply.service_stem(word)
    return word in _REPAIR_VERBS or stem in _REPAIR_VERBS or stem in {"fix", "repair"}


def _job_verbs_and_nouns(question):
    """Return the job verbs and the nouns that name the service."""
    verbs = []
    nouns = []
    bare = _without_surrounding_marks(question).casefold()
    for word in _WORD.findall(bare):
        if word in _STOP or len(word) < 3:
            continue
        if _is_service_verb(word):
            verbs.append(word)
            continue
        nouns.append(word)
    return verbs, nouns


def _same_job_word(wanted, words):
    """True when wanted, or its simpler form, is one of words."""
    stem = price_reply.service_stem(wanted)
    for word in words:
        if word == wanted or price_reply.service_stem(word) == stem:
            return True
    return False


def _pages_address_the_job(question, pages):
    """True when a page sentence names this job, verb and nouns together."""
    verbs, nouns = _job_verbs_and_nouns(question)
    if not verbs or not nouns:
        return False
    for page in pages or []:
        if not isinstance(page, dict) or page.get("status") != "read":
            continue
        for snippet in _snippets(page.get("text") or ""):
            words = [match.group(0) for match in _WORD.finditer(snippet.casefold())]
            if not any(_same_job_word(verb, words) for verb in verbs):
                continue
            if all(_same_job_word(noun, words) for noun in nouns):
                return True
    return False


def _missing_service_name(part):
    """Return a plain name for a job the pages don't list."""
    verbs, nouns = _job_verbs_and_nouns(f"Do you {part}?")
    if not any(_repair_verb(verb) for verb in verbs):
        return None
    stems = {price_reply.service_stem(noun) for noun in nouns}
    if "water" in stems and "heater" in stems:
        return "water heater repair"
    return None


def _two_part_reply(question, pages, instructions, text=None):
    """Answer the covered part, and say the pages don't list the other."""
    jobs = _two_jobs(question)
    if jobs is None or not isinstance(instructions, str) or not _every_page_was_read(pages):
        return None
    covered = []
    missing = None
    for part in jobs:
        part_question = f"Do you {part}?"
        priced = _priced_service_reply(part_question, pages, instructions)
        if priced:
            covered.append(priced)
            continue
        if _pages_address_the_job(part_question, pages):
            return None
        phrase = _missing_service_name(part)
        if not phrase or missing:
            return None
        missing = phrase
    if len(covered) != 1 or not missing:
        return None
    return f"{covered[0]} The pages don't list {missing}. {callback_reply(text)}"


def _normalize_leaky_words(question):
    """Return the question with a leaky slip written as leaky."""
    if not isinstance(question, str) or not question:
        return question

    def swap(match):
        word = match.group(0)
        if urgent_reply._is_leaky_word(word):
            return "leaky"
        return word

    return re.sub(r"[A-Za-z]+", swap, question)


def _asks_about_a_price(question):
    """True when the customer is asking what something costs."""
    if _asks_how_much(question):
        return True
    if not isinstance(question, str):
        return False
    bare = _without_surrounding_marks(question)
    return (
        re.search(
            r"\b(?:charge|charges|cost|costs|price|prices)\b",
            bare,
            re.IGNORECASE,
        )
        is not None
    )


def _mentions_faucet_leak(question):
    """True when the question is about a leaky faucet, including a small slip."""
    if not isinstance(question, str):
        return False
    if re.search(r"\bfaucets?\b", question, re.IGNORECASE) is None:
        return False
    return any(urgent_reply._is_leaky_word(word) for word in re.findall(r"[A-Za-z]+", question))


def _leak_price_reply(question, pages, instructions, text=None):
    """Reply when a faucet leak has no price on the pages."""
    if not _mentions_faucet_leak(question) or not _asks_about_a_price(question):
        return None
    if not isinstance(instructions, str) or not _every_page_was_read(pages):
        return None
    if _priced_snippet(question, pages, instructions):
        return None
    return f"The pages don't list a price for a leak. {callback_reply(text)}"
