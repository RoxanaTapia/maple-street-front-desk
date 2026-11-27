"""Spot a question that is clearly about something else, or a discount ask."""

import re

from answer_kinds.text import _STOP, _WORD

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


def _singular(word):
    """Return word without a trailing s, so pizzas matches pizza."""
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _unrelated_subject(word):
    """True when this word is one of the clearly unrelated subjects."""
    return word in _UNRELATED or _singular(word) in _UNRELATED


def _asks_for_discount(question):
    """True when someone asks to ignore the rules, or for a discount."""
    if not isinstance(question, str) or not question.strip():
        return False
    folded = " ".join(question.casefold().split())
    if re.search(r"\bdiscounts?\b", folded):
        return True
    if re.search(r"\bignore\b(?:\s+\w+){0,6}\s+rules\b", folded):
        return True
    return False


def _is_off_topic(question):
    """True only when the question is clearly about something else."""
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
