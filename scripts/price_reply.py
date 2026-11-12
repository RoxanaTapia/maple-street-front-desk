"""Check an answer for prices before it is shown.

Reads your pages with the page reader and keeps an amount only when it
is written there, exactly as written. When the customer's question is
given, the amount also has to be on the same page, near the service
they asked about. A plural or an -ing form of a service word still
counts, so drains matches drain and clean matches cleaning. A small
misspelling still counts, so drane matches drain. A price written
without a dollar sign, such as 150, or as 150 dollars, is still a
price. If an answer contains any other amount, the whole answer is
replaced with the callback reply from your agreements. An address, a
phone number, and a time are not prices. An answer with no amount is
left as it is. An urgent message is handled first, and your pages are
not read for it.

Usage: python3 scripts/price_reply.py "answer" [site address]
       python3 scripts/price_reply.py --asked "question" "answer" [site address]

With no address, reads http://127.0.0.1:8000, the address the sample
site prints by default. With --asked, the price has to sit near the
service in the question.
"""

import re
import sys

import agreed
import read_pages
import urgent_reply

# A dollar amount, or a number of dollars.
# A comma is part of the amount only when it separates thousands.
# A dollar amount is read whole: the match cannot end in the middle of a number,
# and a full stop after it stays outside the amount.
_AMOUNT = re.compile(
    r"\$\s?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?!,?\d)"
    r"|(?<![\d,.])\d{1,3}(?:,\d{3})+(?:\.\d+)?\s+dollars?(?!\w)"
    r"|(?<![\d,.])\d+(?:\.\d+)?\s+dollars?(?!\w)",
    re.IGNORECASE,
)
# A price with no dollar sign, such as 150. A time, a phone number,
# and the digits already inside a dollar amount are left out here.
# A full stop after the number stays outside it.
_BARE_PRICE = re.compile(r"(?<![\d,.$:(/-])\d{2,}(?:\.\d+)?(?!,?\d)(?![:)/-])")
# A word of the service name. A hyphen stays inside the word, so a
# two-part name is kept together.
_WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*", re.IGNORECASE)
# A full stop ends a sentence. A full stop inside a decimal amount does not.
_SENTENCE_END = re.compile(r"[!?]|\.(?=\s|$)")
# Words that don't name a service. "How much does a drain cleaning cost?"
# leaves the service name.
_NOT_A_SERVICE = frozenset(
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
        "we",
        "are",
        "is",
        "be",
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
        "or",
        "that",
        "this",
        "have",
        "should",
        "please",
        "it",
        "to",
        "of",
        "in",
        "on",
        "my",
        "me",
        "price",
        "prices",
        "cost",
        "costs",
        "charge",
        "charges",
        "fee",
        "fees",
        "pay",
        "paid",
        "rate",
        "rates",
        "dollar",
        "dollars",
    }
)
NOT_A_SERVICE = _NOT_A_SERVICE
# Words that follow a street number. "149 Maple Street" is an address,
# so that 149 is not a price.
_STREET_WORDS = frozenset(
    {
        "street",
        "st",
        "road",
        "rd",
        "avenue",
        "ave",
        "lane",
        "ln",
        "drive",
        "dr",
        "boulevard",
        "blvd",
        "court",
        "ct",
        "way",
        "place",
        "pl",
    }
)
# A service is near a price when its words sit within this many words
# of the amount, in the same sentence. The menu at the top of a page
# is farther away than this, so it is not treated as the service.
NEAR_WORDS = 8
USAGE = (
    'Usage: python3 scripts/price_reply.py "answer" [site address]\n'
    '       python3 scripts/price_reply.py --asked "question" "answer" [site address]\n'
    "Prints the answer when every amount in it is written on your pages.\n"
    "With --asked, the amount also has to be near the service in the question.\n"
    "Otherwise prints the callback reply.\n"
    f"With no address, reads {read_pages.DEFAULT_SITE}."
)


def _looks_like_a_street_number(text, end):
    """True when this number sits in front of a street name."""
    window = text[end : end + 48]
    words = [match.group(0).casefold() for match in _WORD.finditer(window)]
    return any(word in _STREET_WORDS for word in words[:3])


def _amount_matches(text):
    """Return each price as (start, end, text), in the order written.

    A dollar amount and a number of dollars are included. A bare number
    such as 150 is a price too, unless it is a time, a phone number,
    or a street number.
    """
    if not isinstance(text, str) or not text:
        return []
    matches = []
    for match in _AMOUNT.finditer(text):
        matches.append((match.start(), match.end(), match.group(0)))
    covered = [(start, end) for start, end, _amount in matches]
    for match in _BARE_PRICE.finditer(text):
        start, end = match.span()
        if any(start < span_end and end > span_start for span_start, span_end in covered):
            continue
        if _looks_like_a_street_number(text, end):
            continue
        if re.match(r"\s*(?:am|pm)\b", text[end : end + 8], re.IGNORECASE):
            continue
        matches.append((start, end, match.group(0)))
    matches.sort(key=lambda item: item[0])
    return matches


def find_amounts(text):
    """Return each money amount in text, exactly as written, in order."""
    return [amount for _start, _end, amount in _amount_matches(text)]


def callback_reply(text=None):
    """Return the callback reply from your agreements."""
    return agreed.callback_reply(text)


def amount_spans(text):
    """Return (start, end, written) for each dollar amount or number of dollars.

    A bare number such as 150 is not included here.
    """
    if not isinstance(text, str) or not text:
        return []
    return [(match.start(), match.end(), match.group(0)) for match in _AMOUNT.finditer(text)]


def sentence_ends(text):
    """Return the index just after each sentence-ending mark."""
    if not isinstance(text, str) or not text:
        return []
    return [match.end() for match in _SENTENCE_END.finditer(text)]


def _page_blobs(base_url=None, page_text=None, pages=None):
    """Return each page's words, kept apart so a price stays on its own page.

    page_text, when given, is one page and is used instead of fetching.
    pages, when given, is the page list already read. Otherwise the pages
    are read with the page reader. An unreadable page contributes nothing.
    """
    if page_text is not None:
        return [page_text]
    if pages is not None:
        source = pages
    else:
        base = read_pages.DEFAULT_SITE if base_url is None else base_url
        source = read_pages.read_pages(base)
    blobs = []
    for page in source:
        if not isinstance(page, dict) or page.get("status") != "read":
            continue
        blobs.append(f"{page.get('title', '')} {page.get('text', '')}")
    return blobs


def published_amounts(base_url=None, page_text=None):
    """Return amounts written on your pages, in the order they are read.

    page_text, when given, is used instead of fetching. Otherwise the
    pages are read with the page reader. An unreadable page contributes
    nothing. Each amount is kept exactly as written.
    """
    found = []
    seen = set()
    for blob in _page_blobs(base_url, page_text):
        for amount in find_amounts(blob):
            if amount not in seen:
                seen.add(amount)
                found.append(amount)
    return found


def service_words(message):
    """Return the words that name the service in the customer's question.

    "How much is a drain cleaning?" gives drain and cleaning. Small words,
    and words such as price and cost, are left out. With no service to
    name, the list is empty.
    """
    if not isinstance(message, str):
        return []
    words = []
    for match in _WORD.finditer(message.casefold()):
        word = match.group(0)
        if word in _NOT_A_SERVICE or len(word) < 3 or word.isdigit():
            continue
        if word not in words:
            words.append(word)
    return words


def _sentence_bounds(text, index):
    """Return the start and end of the sentence that contains index."""
    start = 0
    end = len(text)
    for mark in _SENTENCE_END.finditer(text):
        if mark.end() <= index:
            start = mark.end()
        elif mark.start() >= index:
            end = mark.end()
            break
    return start, end


def _words_near(text, start, end):
    """Return the words just before and after a price, in that sentence."""
    sentence_start, sentence_end = _sentence_bounds(text, start)
    before = text[sentence_start:start]
    after = text[end:sentence_end]
    left = [match.group(0).casefold() for match in _WORD.finditer(before)]
    right = [match.group(0).casefold() for match in _WORD.finditer(after)]
    return left[-NEAR_WORDS:] + right[:NEAR_WORDS]


def _service_stem(word):
    """Return a simpler form so a plural or an -ing word matches.

    drains and drain match. clean and cleaning match. A short leftover
    is not stripped, so a tiny word stays whole.
    """
    stem = word
    if len(stem) > 4 and stem.endswith("s") and not stem.endswith("ss"):
        stem = stem[:-1]
    if len(stem) > 5 and stem.endswith("ing"):
        shorter = stem[:-3]
        if len(shorter) >= 4:
            stem = shorter
    return stem


def _edit_distance(left, right, limit):
    """Return the edit distance, or limit + 1 when it is larger than limit.

    A substitution, a missing or extra letter, and two neighbouring
    letters swapped each count as one.
    """
    if abs(len(left) - len(right)) > limit:
        return limit + 1
    rows = len(left) + 1
    cols = len(right) + 1
    distance = [[0] * cols for _ in range(rows)]
    for index in range(rows):
        distance[index][0] = index
    for index in range(cols):
        distance[0][index] = index
    for row in range(1, rows):
        smallest = distance[row][0]
        for col in range(1, cols):
            cost = 0 if left[row - 1] == right[col - 1] else 1
            value = min(
                distance[row - 1][col] + 1,
                distance[row][col - 1] + 1,
                distance[row - 1][col - 1] + cost,
            )
            if (
                row > 1
                and col > 1
                and left[row - 1] == right[col - 2]
                and left[row - 2] == right[col - 1]
            ):
                value = min(value, distance[row - 2][col - 2] + 1)
            distance[row][col] = value
            smallest = min(smallest, value)
        if smallest > limit:
            return limit + 1
    return distance[-1][-1]


def _one_edit(left, right):
    """True when left and right are a small slip apart.

    One changed, missing, extra, or swapped letter counts. Two count
    only when the words start the same way, so drane matches drain.
    A very short word is left out, so it cannot match a different word
    by accident.
    """
    if min(len(left), len(right)) < 4 or max(len(left), len(right)) < 5:
        return False
    distance = _edit_distance(left, right, 2)
    if distance == 1:
        return True
    if distance == 2 and len(left) >= 5 and len(right) >= 5 and left[:3] == right[:3]:
        return True
    return False


def _same_service_word(left, right):
    """True when two words name the same service.

    A plural or an -ing form still matches. A small misspelling does
    too, so drane matches drain.
    """
    if left == right:
        return True
    if _service_stem(left) == _service_stem(right):
        return True
    return _one_edit(left, right) or _one_edit(_service_stem(left), _service_stem(right))


def _words_near_amount(text, amount):
    """Return the words just beside this amount, in its sentence."""
    for start, end, found in _amount_matches(text):
        if found != amount:
            continue
        return _words_near(text, start, end)
    return []


def words_near_amount(text, amount):
    """Return the words just beside this amount, in its sentence."""
    return _words_near_amount(text, amount)


def service_stem(word):
    """Return a simpler form so a plural or an -ing word matches."""
    return _service_stem(word)


def one_edit(left, right):
    """True when two words are a small slip apart, so drane matches drain."""
    return _one_edit(left, right)


def price_is_near_service(page_text, amount, words):
    """True when this amount is on the page, near every service word.

    A plural or an -ing form still matches, so drains matches drain
    and clean matches cleaning. A small misspelling still matches,
    so drane matches drain.
    """
    if not words or not isinstance(page_text, str) or not amount:
        return False
    for start, end, found in _amount_matches(page_text):
        if found != amount:
            continue
        nearby = _words_near(page_text, start, end)
        if all(any(_same_service_word(word, near) for near in nearby) for word in words):
            return True
    return False


def checked_answer(answer, base_url=None, page_text=None, text=None, message=None, pages=None):
    """Return the answer, or the callback reply when a price cannot be confirmed.

    An answer with no amount is returned unchanged. A published amount
    must match the pages character for character. When message is the
    customer's question, the amount also has to be on the same page,
    near the service they asked about.
    """
    if not isinstance(answer, str):
        return answer
    amounts = find_amounts(answer)
    if not amounts:
        return answer
    blobs = _page_blobs(base_url, page_text, pages)
    allowed = set()
    for blob in blobs:
        allowed.update(find_amounts(blob))
    if not all(amount in allowed for amount in amounts):
        return callback_reply(text)
    words = service_words(message)
    if not words:
        return answer
    for amount in amounts:
        if not any(price_is_near_service(blob, amount, words) for blob in blobs):
            return callback_reply(text)
    return answer


def answer_for(message, answer, base_url=None, page_text=None, text=None, pages=None):
    """Handle an urgent message first, then check prices before showing an answer.

    When the message is urgent, the fixed urgent reply is returned and
    your pages are not read. Otherwise a price is kept only when it is
    on the same page, near the service in the message.
    """
    urgent = urgent_reply.reply_if_urgent(message)
    if urgent is not None:
        return urgent
    return checked_answer(
        answer,
        base_url=base_url,
        page_text=page_text,
        text=text,
        message=message,
        pages=pages,
    )


def _split_site(args):
    if args and (args[-1].startswith("http://") or args[-1].startswith("https://")):
        return args[:-1], args[-1]
    return args, None


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or any(arg in {"-h", "--help"} for arg in args):
        print(USAGE, file=sys.stderr)
        return 2
    message = None
    if "--asked" in args:
        index = args.index("--asked")
        if index + 1 >= len(args):
            print(USAGE, file=sys.stderr)
            return 2
        message = args.pop(index + 1)
        del args[index]
    words, base = _split_site(args)
    if not words:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        reply = checked_answer(" ".join(words), base_url=base, message=message)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
