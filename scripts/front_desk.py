"""Run one customer message through the front desk, in order.

1. Urgent reply. If the message is urgent, that fixed reply is the whole
   answer, and nothing else runs.
2. Read your pages.
3. Write the answer.
4. Check every price. An amount that isn't on your pages is replaced
   with the callback reply.

Usage: python3 scripts/front_desk.py "customer message" [site address]

With no address, reads http://127.0.0.1:8000, the address the sample
site prints by default.
"""

import sys

import answer_reply
import price_reply
import read_pages
import urgent_reply

USAGE = (
    'Usage: python3 scripts/front_desk.py "customer message" [site address]\n'
    "Runs the urgent reply, then your pages, then the answer, then the price check.\n"
    "An urgent message stops after the fixed reply.\n"
    f"With no address, reads {read_pages.DEFAULT_SITE}."
)


def _page_text(pages):
    parts = []
    for page in pages:
        if page.get("status") != "read":
            continue
        parts.append(f"{page.get('title', '')} {page.get('text', '')}")
    return "\n".join(parts)


def reply_to(message, base_url=None, writer=None, client=None):
    """Return the reply a customer would see.

    An urgent message stops at the first part. Your pages are not read
    for it, and the answer writer is not called. Otherwise the pages are
    read, the answer is written, and every price is checked last.

    client, when given, stands in for the Claude call inside the answer
    step. The price check still runs on whatever comes back.
    """
    urgent = urgent_reply.reply_if_urgent(message)
    if urgent is not None:
        return urgent
    base = read_pages.DEFAULT_SITE if base_url is None else base_url
    pages = read_pages.read_pages(base)
    answer = answer_reply.write_answer(message, pages, writer=writer, client=client)
    return price_reply.checked_answer(answer, page_text=_page_text(pages))


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
        reply = reply_to(" ".join(words), base_url=base)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
