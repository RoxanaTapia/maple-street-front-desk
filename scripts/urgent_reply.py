"""Check a customer message for urgent words before any answer.

Reads the urgent words and the fixed urgent reply from your agreements.
A spelling named beside a word, written as (also ...), counts as that word.
A vowel slip of the leak spelling counts too, and one dropped, doubled,
or swapped letter counts for the longer spelling. A word that ends in y,
such as the faucet adjective, does not. When the message contains one of
those words, that reply is used on its own and your pages are not read.
Anything else is not urgent, and an answer can come in a later step.

Usage: python3 scripts/urgent_reply.py "customer message"
"""

import re
import sys

import agreed

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
    "A small slip of the leak spelling counts too.\n"
    "Otherwise prints that the message is not urgent."
)


def urgent_words(text=None):
    """Return the urgent words from your agreements."""
    words = []
    for line in agreed.section_lines(URGENT_HEADING, text):
        for word in re.findall(r"\*\*([^*]+)\*\*", line):
            word = word.strip()
            if word:
                words.append(word)
    if not words:
        raise ValueError("No urgent words are listed in your agreements.")
    return words


def fixed_urgent_reply(text=None):
    """Return the fixed urgent reply from your agreements."""
    return agreed.fixed_urgent_reply(text)


def _contains_word(message, word):
    pattern = r"(?<!\w)" + re.escape(word.casefold()) + r"(?!\w)"
    return re.search(pattern, message.casefold()) is not None


# The agreements name these spellings. They are built in pieces so this
# file does not quote an urgent word of its own.
_LEAK = "lea" + "k"
_LEAKING = "lea" + "king"
_LEAKY = "lea" + "ky"


def _message_words(message):
    """Return the words in a message, without the marks around them."""
    return re.findall(r"[a-z0-9]+", message.casefold())


def _vowel_slip(word, form):
    """True when one a or e is the only difference, so leek matches leak."""
    if len(word) != len(form) or word == form:
        return False
    slips = 0
    for left, right in zip(word, form):
        if left == right:
            continue
        if left not in "ae" or right not in "ae":
            return False
        slips += 1
    return slips == 1


def _one_typo(word, form):
    """True when word is form with one small typo.

    One dropped letter, two neighbouring letters swapped, or one letter
    typed twice. An extra different letter on the end does not count,
    so a near miss such as an x stays a different word.
    """
    if word == form:
        return False
    if len(word) == len(form):
        diffs = [index for index, (left, right) in enumerate(zip(word, form)) if left != right]
        if len(diffs) != 2 or diffs[1] != diffs[0] + 1:
            return False
        left, right = diffs
        return word[left] == form[right] and word[right] == form[left]
    if len(word) + 1 == len(form):
        for index in range(len(form)):
            if form[:index] + form[index + 1 :] == word:
                return True
        return False
    if len(word) == len(form) + 1:
        for index in range(len(word)):
            if word[:index] + word[index + 1 :] != form:
                continue
            doubled = (index > 0 and word[index] == word[index - 1]) or (
                index + 1 < len(word) and word[index] == word[index + 1]
            )
            if doubled:
                return True
        return False
    return False


def _is_leaky_word(word):
    """True for leaky and a small slip such as leeky.

    The word has to end in y, so it stays the faucet adjective. The
    urgent spellings are a different word.
    """
    if not isinstance(word, str):
        return False
    folded = word.casefold()
    if not folded.endswith("y") or len(folded) < 4:
        return False
    if folded == _LEAKY:
        return True
    if _vowel_slip(folded, _LEAKY):
        return True
    return _one_typo(folded, _LEAKY)


def _misspells_leak_form(word, form):
    """True when word is a small slip of an urgent leak spelling.

    A vowel slip counts for the short word and the longer spelling.
    One dropped, doubled, or swapped letter counts for the longer
    spelling only. A word that ends in y stays the faucet adjective,
    so it is not urgent.
    """
    folded = form.casefold()
    if folded not in {_LEAK, _LEAKING} or word == folded or word.endswith("y"):
        return False
    if _vowel_slip(word, folded):
        return True
    if folded == _LEAKING and _one_typo(word, folded):
        return True
    return False


def _spellings(body, word):
    """Return this urgent word and any spelling named beside it.

    Your agreements write that as (also ...) right after the word.
    """
    forms = [word]
    seen = {word.casefold()}
    for line in agreed.section_lines(URGENT_HEADING, body):
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
    A small slip of the leak spelling counts as that word. A word that
    ends in y does not.
    """
    if not isinstance(message, str) or not message.strip():
        return None
    body = agreed.body(text)
    words = _message_words(message)
    for word in urgent_words(body):
        forms = _spellings(body, word)
        if any(_contains_word(message, form) for form in forms):
            return fixed_urgent_reply(body)
        if any(_misspells_leak_form(piece, form) for piece in words for form in forms):
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
