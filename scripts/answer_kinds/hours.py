"""Answer an hours question or a Saturday booking."""

import re

from answer_kinds.pages import _ordered_names, _read_named, _with_pages, _with_source
from answer_kinds.text import _CLOCK, _PHONE, _same_question, _snippets, _without_surrounding_marks


def _saturday_hours_question(question):
    """True when this is a yes or no question about being open on Saturday."""
    if not isinstance(question, str):
        return False
    bare = _without_surrounding_marks(question)
    if re.match(r"^are you open\b", bare, re.IGNORECASE) is None:
        return False
    return re.search(r"\bsaturdays?\b", bare, re.IGNORECASE) is not None


def _hours_answer(question, pages, instructions):
    """Answer a plain hours question from the Hours page, or return None."""
    if not _same_question(question, "What are your hours?"):
        return None
    page = None
    for item in pages or []:
        name = item.get("name") if isinstance(item, dict) else None
        if isinstance(name, str) and "hours" in name.casefold():
            page = item
            break
    if page is None or page.get("status") != "read":
        return None
    page_text = page.get("text") or ""
    if not page_text or page_text not in instructions:
        return None
    lines = []
    for snippet in _snippets(page_text):
        if _CLOCK.search(snippet) or re.search(r"\bclosed\b", snippet, re.IGNORECASE):
            lines.append(snippet)
    if not lines:
        return None
    return _with_source(lines, page.get("name"))


def _saturday_booking_reply(question, pages, instructions):
    """Answer a Saturday booking from the hours page and the contact page."""
    if not isinstance(question, str) or not isinstance(instructions, str):
        return None
    bare = _without_surrounding_marks(question)
    if not re.search(r"\bbook\b", bare, re.IGNORECASE):
        return None
    if not re.search(r"\bsaturdays?\b", bare, re.IGNORECASE):
        return None
    hours = _read_named(pages, "hours")
    contact = _read_named(pages, "contact")
    if hours is None or contact is None:
        return None
    hours_text = hours.get("text") or ""
    contact_text = contact.get("text") or ""
    if not hours_text or hours_text not in instructions:
        return None
    if not contact_text or contact_text not in instructions:
        return None
    if not re.search(r"\bopen\s+saturdays?\b", hours_text, re.IGNORECASE):
        return None
    if not re.search(r"\bbook\b", contact_text, re.IGNORECASE):
        return None
    clock = None
    for snippet in _snippets(hours_text):
        if not re.search(r"\bsaturday\b", snippet, re.IGNORECASE):
            continue
        found = _CLOCK.search(snippet)
        if found:
            clock = found.group(0)
            break
    phone = _PHONE.search(contact_text)
    if not clock or not phone:
        return None
    hours_name = " ".join(str(hours.get("name", "")).split())
    contact_name = " ".join(str(contact.get("name", "")).split())
    if not hours_name or not contact_name:
        return None
    body = f"We're open Saturdays from {clock}. To book, call our main line at {phone.group(0)}."
    names = [name for name in _ordered_names(pages) if name in {hours_name, contact_name}]
    if names != [hours_name, contact_name]:
        names = [hours_name, contact_name]
    return _with_pages(body, names)
