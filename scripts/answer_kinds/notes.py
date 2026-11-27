"""Write a short note when a call or a page fails."""

import logging
import threading
import urllib.error
from datetime import datetime, timedelta, timezone


def _clock():
    """Return the clock on the answer writer, so a test can replace it."""
    import answer_reply

    return answer_reply.datetime


def _log():
    """Return the notes file on the answer writer, so a test can replace it."""
    import answer_reply

    return answer_reply.FAILURE_LOG

# One note per page per hour. The notes file is the record, so a later
# question, even from a new command, does not write the page again while
# that hour still has a line for it.
PAGE_NOTE_WINDOW = timedelta(hours=1)


_NOTE_LOCK = threading.RLock()


_STAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


_strptime = datetime.strptime


def _write_owner_note(detail):
    """Append one line to the owner's error notes."""
    when = _clock().now(timezone.utc).strftime(_STAMP_FORMAT)
    line = f"{when} {detail}\n"
    try:
        with _NOTE_LOCK:
            _log().parent.mkdir(parents=True, exist_ok=True)
            with _log().open("a", encoding="utf-8") as handle:
                handle.write(line)
    except OSError:
        logging.warning("The failure note could not be saved.")
        return False
    return True


def _page_noted_recently(name, now):
    """True when this page already has a note inside the hour."""
    try:
        text = _log().read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    prefix = f"{name}: "
    for line in text.splitlines():
        stamp, _, rest = line.partition(" ")
        if not rest.startswith(prefix):
            continue
        try:
            seen = _strptime(stamp, _STAMP_FORMAT).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if now - seen < PAGE_NOTE_WINDOW:
            return True
    return False


def _note_unreadable_pages(pages):
    """Note each page that could not be read, at most once an hour."""
    now = _clock().now(timezone.utc)
    with _NOTE_LOCK:
        for page in pages or []:
            if not isinstance(page, dict) or page.get("status") != "unreadable":
                continue
            name = " ".join(str(page.get("name", "")).split())
            if not name:
                continue
            if _page_noted_recently(name, now):
                continue
            reason = " ".join(str(page.get("reason") or "unreadable").split())
            if not reason:
                reason = "unreadable"
            if not _write_owner_note(f"{name}: {reason}"):
                continue
            logging.warning("A page could not be read (%s: %s).", name, reason)


def _failure_kind(error):
    """Return a fixed label for a failed Claude call."""
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, urllib.error.HTTPError):
        code = error.code
        if code in (401, 403):
            return "key missing or expired"
        if code == 408:
            return "timeout"
        if isinstance(code, int) and code >= 500:
            return "Claude is down"
        return "call failed"
    if isinstance(error, urllib.error.URLError):
        if isinstance(error.reason, TimeoutError):
            return "timeout"
        return "Claude is down"
    if isinstance(error, ConnectionError):
        return "Claude is down"
    if type(error) is RuntimeError and error.args == ("missing key",):
        return "key missing or expired"
    if type(error) is ValueError and error.args == ("empty reply",):
        return "empty reply"
    return "call failed"


def _note_call_failure(error):
    """Record a failed Claude call for the owner."""
    kind = _failure_kind(error)
    _write_owner_note(kind)
    logging.warning("Claude could not answer (%s).", kind)
