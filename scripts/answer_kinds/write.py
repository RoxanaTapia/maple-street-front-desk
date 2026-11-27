"""Choose one reply and return it."""

import logging
import re

import chat_limit
import price_reply

from answer_kinds.callback import (
    _email_reply_for,
    _leak_price_reply,
    _normalize_leaky_words,
    _service_is_unlisted,
    _two_part_reply,
)
from answer_kinds.claude import _api_key, _claude_reply
from answer_kinds.fixed import (
    callback_reply,
    discount_reply,
    off_topic_reply,
    unlisted_service_reply,
)
from answer_kinds.instructions import build_instructions
from answer_kinds.notes import _note_call_failure, _note_unreadable_pages
from answer_kinds.off_topic import _asks_for_discount, _is_off_topic
from answer_kinds.pages import _name_every_page_used, normalize_source_line
from answer_kinds.spoken import _direct_price_reply, _plain_customer_price
from answer_kinds.stand_in import stand_in_writer
from answer_kinds.text import _fact_first


def _entry():
    """Return the answer writer module the rest of the project imports."""
    import answer_reply

    return answer_reply


def without_internal_notes(reply):
    """Drop an internal note so the customer never sees it."""
    if not isinstance(reply, str) or not re.search(r"\bnote\s*:", reply, re.IGNORECASE):
        return reply
    kept = []
    for paragraph in re.split(r"\n\s*\n", reply.strip()):
        lines = []
        for line in paragraph.splitlines():
            if re.match(r"\s*note\s*:", line, re.IGNORECASE):
                break
            lines.append(line)
        text = "\n".join(lines).strip()
        if not text:
            continue
        match = re.search(r"\bnote\s*:", text, re.IGNORECASE)
        if match:
            text = text[: match.start()].rstrip()
        text = text.strip()
        if text:
            kept.append(text)
    return "\n\n".join(kept).strip()


def write_answer(question, pages, writer=None, text=None, client=None):
    """Write an answer for question from the page text."""
    try:
        _note_unreadable_pages(pages)
    except Exception:
        logging.warning("The failure note could not be saved.")
    question = _normalize_leaky_words(question)
    if _is_off_topic(question):
        return off_topic_reply(text)
    if _asks_for_discount(question):
        return discount_reply(text)
    if _service_is_unlisted(question, pages):
        return unlisted_service_reply(text)
    email = _email_reply_for(question, pages, text)
    if email:
        return email
    instructions = build_instructions(question, pages, text=text)
    combined = _two_part_reply(question, pages, instructions, text)
    if combined:
        return combined
    leak = _leak_price_reply(question, pages, instructions, text)
    if leak:
        return leak
    callback = callback_reply(text)
    outage = _entry().outage_reply(text)
    if writer is not None:
        reply = writer(question, instructions, pages)
    elif client is None and not _api_key():
        reply = stand_in_writer(question, instructions, pages, text=text)
    else:
        if not chat_limit.allow_model_call():
            return chat_limit.busy_reply()
        try:
            reply = _claude_reply(instructions, client=client)
        except Exception as error:
            try:
                _note_call_failure(error)
            except Exception:
                logging.warning("Claude could not answer.")
            return outage
    reply = without_internal_notes(reply)
    if isinstance(reply, str) and reply.strip() == outage:
        return outage
    if not isinstance(reply, str) or not reply.strip():
        return callback
    reply = normalize_source_line(reply, pages, callback)
    reply = _plain_customer_price(question, reply, pages, instructions)
    reply = _direct_price_reply(question, reply, pages, instructions, callback)
    reply = price_reply.adjust_stated_price(reply, question, pages=pages)
    reply = without_internal_notes(reply)
    if not isinstance(reply, str) or not reply.strip():
        return callback
    if reply.strip() == callback:
        return callback
    if reply.strip() == outage:
        return outage
    return _fact_first(question, _name_every_page_used(reply, pages))
