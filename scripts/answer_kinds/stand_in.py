"""Answer the agreed test questions without calling an AI."""

import agreed

from answer_kinds.fixed import callback_reply
from answer_kinds.hours import _hours_answer, _saturday_booking_reply, _saturday_hours_question
from answer_kinds.pages import _source_page, _with_source
from answer_kinds.prices import (
    _correct_stated_price,
    _how_much_reply,
    _misspelled_price,
    _priced_service_reply,
    _states_yes_or_no,
    _yes_matching_price,
)
from answer_kinds.text import _same_question, _supporting

ANSWERED_GROUP = agreed.ANSWERED_GROUP


def _matched_question(question, text):
    """Return the agreed question this message asks, or None."""
    rows = list(agreed.question_rows(text))
    if isinstance(question, str):
        for item in rows:
            if _same_question(item["question"], question):
                return item
    if _saturday_hours_question(question):
        for item in rows:
            if _same_question(item["question"], "Are you open Saturdays?"):
                return item
    return None


def stand_in_writer(question, instructions, pages, text=None):
    """Answer the agreed test questions. This is not a real AI."""
    callback = callback_reply(text)
    if not isinstance(question, str) or not question.strip():
        return callback
    if not isinstance(instructions, str):
        return callback
    row = _matched_question(question, text)
    if row is not None and row["group"] != ANSWERED_GROUP:
        return callback
    offered = _priced_service_reply(question, pages, instructions)
    if row is None:
        return (
            _hours_answer(question, pages, instructions)
            or _saturday_booking_reply(question, pages, instructions)
            or _correct_stated_price(question, pages, instructions)
            or _yes_matching_price(question, pages, instructions)
            or offered
            or _misspelled_price(question, pages, instructions)
            or _how_much_reply(question, pages, instructions)
            or callback
        )
    name = _source_page(row["detail"])
    if not name:
        return offered or callback
    page = None
    for item in pages or []:
        if item.get("name") == name:
            page = item
            break
    if page is None or page.get("status") != "read":
        return offered or callback
    page_text = page.get("text") or ""
    if not page_text or page_text not in instructions:
        return offered or callback
    sentences = _supporting(page_text, question, row["detail"])
    if sentences and _states_yes_or_no(sentences):
        return _with_source(sentences, name)
    matching = _yes_matching_price(question, pages, instructions)
    if matching:
        return matching
    if offered:
        return offered
    if not sentences:
        return (
            _how_much_reply(question, pages, instructions)
            or _misspelled_price(question, pages, instructions)
            or callback
        )
    return _with_source(sentences, name)
