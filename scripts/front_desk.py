"""Run one customer message through the front desk, in order.

1. Urgent reply. If the message is urgent, that fixed reply is the whole
   answer, and nothing else runs.
2. Read your pages.
3. Write the answer. A question that is clearly about something else
   gets the off-topic reply. Anything else is answered as usual, and a
   question the pages don't cover gets the callback reply.
4. Check every price. An amount that isn't on your pages, or that isn't
   near the service the customer asked about, is replaced with the
   callback reply. The outage reply is left as it is.

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
    "A question that is clearly about something else gets the off-topic reply.\n"
    f"With no address, reads {read_pages.DEFAULT_SITE}."
)


def reply_to(message, base_url=None, writer=None, client=None):
    """Return the reply a customer would see.

    An urgent message stops at the first part. Your pages are not read
    for it, and the answer writer is not called. Otherwise the pages are
    read, the answer is written, and every price is checked last. A price
    is kept only when it is on the same page, near the service asked about.
    A question that is clearly about something else gets the off-topic
    reply. A question the pages don't cover still gets the callback reply.
    The outage reply is returned as written, so a failed call is not
    replaced with the callback reply.

    client, when given, stands in for the Claude call inside the answer
    step. writer, when given, stands in for the whole answer step, so a
    check can try a reply without a live call. The price check still runs
    on whatever comes back, except the outage reply.
    """
    urgent = urgent_reply.reply_if_urgent(message)
    if urgent is not None:
        return urgent
    base = read_pages.DEFAULT_SITE if base_url is None else base_url
    pages = read_pages.read_pages(base)
    answer = answer_reply.write_answer(message, pages, writer=writer, client=client)
    if answer == answer_reply.outage_reply():
        return answer
    return price_reply.checked_answer(answer, pages=pages, message=message)


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
