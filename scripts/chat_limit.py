"""Count public chat messages that reach the AI, for one Berlin day.

The public chat on the demo can call the AI on every ordinary question.
This count keeps that cost bounded. CHAT_DAILY_LIMIT is the whole chat.
CHAT_VISITOR_DAILY_LIMIT is one visitor. An empty setting uses the
default, 200 for the whole chat and 20 for one visitor. 0 turns that
cap off.

The count is kept in memory. It starts again at midnight in Berlin, and
a restart starts it again too. Nothing is written to disk.

A message is counted only when this request is a public chat message
and it is about to reach the AI. An urgent message is not counted.
A question the assistant answers without the AI is not counted.

One visitor is the address that connected, or the first address in
X-Forwarded-For when a proxy sends that header.

Usage: python3 scripts/chat_limit.py
"""

import contextlib
import os
import sys
import threading
from contextvars import ContextVar
from datetime import datetime
from zoneinfo import ZoneInfo

DAILY_ENV = "CHAT_DAILY_LIMIT"
VISITOR_ENV = "CHAT_VISITOR_DAILY_LIMIT"
DEFAULT_DAILY_LIMIT = 200
DEFAULT_VISITOR_LIMIT = 20
BERLIN = ZoneInfo("Europe/Berlin")
BUSY_REPLY = (
    "The demo has had a busy day. Please come back tomorrow, "
    "or book a call on roxanatapia.dev."
)

# Tests set this to a function that returns a datetime. None means now.
clock = None

_lock = threading.Lock()
_day = None
_total = 0
_visitors = {}
_visitor = ContextVar("maple_chat_visitor", default=None)

USAGE = (
    "Usage: python3 scripts/chat_limit.py\n"
    "Prints the daily caps for the public chat, and the reply a visitor\n"
    "gets when a cap is reached."
)


def busy_reply():
    """Return the note a visitor sees when a daily cap is reached."""
    return BUSY_REPLY


def limits():
    """Return the whole-chat cap and the per-visitor cap.

    An empty setting uses the default. 0 turns that cap off.
    Any other value has to be a whole number.
    """
    return (
        _read_cap(DAILY_ENV, DEFAULT_DAILY_LIMIT),
        _read_cap(VISITOR_ENV, DEFAULT_VISITOR_LIMIT),
    )


def visitor_key(forwarded, connected):
    """Return the visitor used for the per-visitor cap.

    A proxy may send X-Forwarded-For. The first address in that header
    is the visitor. Otherwise the address that connected is used.
    """
    if isinstance(forwarded, str) and forwarded.strip():
        first = forwarded.split(",")[0].strip().strip('"')
        if first:
            return first[:200]
    if isinstance(connected, str) and connected.strip():
        return connected.strip()[:200]
    return ""


@contextlib.contextmanager
def public_chat(visitor):
    """Mark the messages in this block as one public chat visitor.

    Outside this block the caps are not applied, so a local command
    is not limited by the public chat.
    """
    token = _visitor.set(visitor or "")
    try:
        yield
    finally:
        _visitor.reset(token)


def allow_model_call():
    """Return True when this message may reach the AI.

    Outside a public chat request, the cap is not applied.
    Inside one, a message under both caps is counted and allowed.
    A message at either cap is refused, and it is not counted again.
    """
    visitor = _visitor.get()
    if visitor is None:
        return True
    daily_limit, visitor_limit = limits()
    if not daily_limit and not visitor_limit:
        return True
    with _lock:
        return _admit(visitor, daily_limit, visitor_limit)


def reset():
    """Clear the in-memory count.

    A restart does the same. The automated tests use this between cases.
    """
    global _day, _total, _visitors
    with _lock:
        _day = None
        _total = 0
        _visitors = {}


def _read_cap(name, default):
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    text = str(raw).strip()
    if not text.isdigit():
        raise ValueError(f"Set {name} to a whole number, or leave it empty.")
    return int(text)


def _today():
    moment = clock() if clock is not None else datetime.now(BERLIN)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=BERLIN)
    else:
        moment = moment.astimezone(BERLIN)
    return moment.date()


def _roll_forward(today):
    global _day, _total, _visitors
    if _day != today:
        _day = today
        _total = 0
        _visitors = {}


def _admit(visitor, daily_limit, visitor_limit):
    global _total
    _roll_forward(_today())
    if daily_limit and _total >= daily_limit:
        return False
    used = _visitors.get(visitor, 0) if visitor else 0
    if visitor and visitor_limit and used >= visitor_limit:
        return False
    if daily_limit:
        _total += 1
    if visitor and visitor_limit:
        _visitors[visitor] = used + 1
    return True


def _cap_line(label, cap):
    if cap:
        return f"{label}: {cap} messages a day"
    return f"{label}: no cap"


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if any(arg in {"-h", "--help"} for arg in args):
        print(USAGE, file=sys.stderr)
        return 2
    if args:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        daily, visitor = limits()
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(_cap_line("Whole chat", daily))
    print(_cap_line("One visitor", visitor))
    print("The day is midnight to midnight in Berlin.")
    print("The count is kept in memory, and a restart starts it again.")
    print(busy_reply())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
