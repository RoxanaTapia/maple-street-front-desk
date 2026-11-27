"""Name the page an answer came from."""

import re

from answer_kinds.text import _CLOCK, _PHONE


def _source_page(detail):
    match = re.search(r"\bfrom\s+(.+?)\.?$", detail.strip(), re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _with_source(sentences, name):
    body = " ".join(sentences).strip()
    tag = f"From {name}."
    if not body:
        return tag
    if body.endswith((".", "!", "?")):
        return f"{body} {tag}"
    return f"{body}. {tag}"


def _page_names(pages):
    names = []
    seen = set()
    for page in pages or []:
        if not isinstance(page, dict):
            continue
        name = page.get("name")
        if not isinstance(name, str):
            continue
        name = " ".join(name.split())
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        names.append(name)
    names.sort(key=len, reverse=True)
    return names


def _canonical_name(raw, names):
    folded = " ".join(raw.split()).casefold()
    for name in names:
        if name.casefold() == folded:
            return name
    return None


def _source_example(pages):
    names = _page_names(pages)
    for name in names:
        if name.casefold() == "hours & faq":
            return name
    if names:
        return names[0]
    return "Hours & FAQ"


def normalize_source_line(answer, pages, callback=None):
    """End a page-based answer with exactly 'From <Page name>.'"""
    if not isinstance(answer, str):
        return answer
    text = answer.strip()
    if not text:
        return text
    if isinstance(callback, str) and text == callback.strip():
        return callback
    names = _page_names(pages)
    if not names:
        return text
    alternation = "|".join(re.escape(name) for name in names)
    pattern = re.compile(
        rf"""
        ^
        (?P<body>.*?)
        (?:
            \s*
            \(\s*
                (?:source\s*:\s*)?
                (?:from\s+)?
                (?:the\s+)?
                (?P<paren>{alternation})
                (?:\s+page)?
                \s*\.?
            \s*\)
            \s*\.?
          |
            \s+
            (?:source\s*:\s*|from\s+)
            (?:the\s+)?
            (?P<marked>{alternation})
            (?:\s+page)?
            \s*\.?
        )
        \s*$
        """,
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    )
    match = pattern.search(text)
    if not match:
        return text
    raw = match.group("paren") or match.group("marked")
    name = _canonical_name(raw, names)
    if not name:
        return text
    body = (match.group("body") or "").strip()
    if isinstance(callback, str) and body == callback.strip():
        return callback
    return _with_source([body] if body else [], name)


def _ordered_names(pages):
    """Return page names in the order the pages were given."""
    names = []
    seen = set()
    for page in pages or []:
        if not isinstance(page, dict):
            continue
        name = page.get("name")
        if not isinstance(name, str):
            continue
        name = " ".join(name.split())
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        names.append(name)
    return names


def _read_named(pages, needle):
    """Return the read page whose name contains needle, or None."""
    for page in pages or []:
        if not isinstance(page, dict) or page.get("status") != "read":
            continue
        name = page.get("name")
        if isinstance(name, str) and needle in name.casefold():
            return page
    return None


def _flexible_name_pattern(name):
    """Match a page name with loose spacing, and 'and' for '&'."""
    tokens = name.split()
    parts = []
    for index, token in enumerate(tokens):
        if token == "&":
            parts.append(r"\s*(?:&|and)\s*")
            continue
        if index and tokens[index - 1] != "&":
            parts.append(r"\s+")
        parts.append(re.escape(token))
    return "".join(parts)


def _compiled_page_names(names):
    compiled = []
    for name in sorted(names, key=len, reverse=True):
        compiled.append((name, re.compile(_flexible_name_pattern(name), re.IGNORECASE)))
    return compiled


def _page_at(text, compiled):
    """Return the page name and the end index when text starts with one."""
    the = re.match(r"(?i)the\s+", text)
    start = the.end() if the else 0
    hit = None
    for name, pattern in compiled:
        got = pattern.match(text, start)
        if got and (hit is None or got.end() > hit[0]):
            hit = (got.end(), name)
    if hit is None:
        return None
    end, name = hit
    page_word = re.match(r"(?i)\s+pages?\b", text[end:])
    if page_word:
        end += page_word.end()
    return name, end


def _match_citation(text, compiled):
    """Return the end index and page names when text starts with a source sentence."""
    opener = re.match(r"(?i)from\s+", text)
    if not opener or not compiled:
        return None
    pos = opener.end()
    found = []
    while pos <= len(text):
        hit = _page_at(text[pos:], compiled)
        if hit is None:
            return None
        name, end = hit
        found.append(name)
        pos += end
        tail = text[pos:]
        sep = re.match(r"(?i)\s*(?:,|&|\band\b)\s*", tail)
        if sep and _page_at(text[pos + sep.end() :], compiled):
            pos += sep.end()
            continue
        period = re.match(r"\s*\.", tail)
        if period:
            return pos + period.end(), found
        spaces = re.match(r"[ \t]*", tail)
        rest = tail[spaces.end() :]
        if rest == "" or rest.startswith("\n"):
            return pos + spaces.end(), found
        return None


def _source_spans(text, names):
    """Return each source sentence as start, end, and the pages it names."""
    compiled = _compiled_page_names(names)
    opener = re.compile(r"(?i)(?<!\S)from\s+")
    spans = []
    cursor = 0
    while cursor < len(text):
        match = opener.search(text, cursor)
        if not match:
            break
        parsed = _match_citation(text[match.start() :], compiled)
        if not parsed:
            cursor = match.end()
            continue
        end, found = parsed
        spans.append((match.start(), match.start() + end, found))
        cursor = match.start() + end
    return spans


def _without_source_lines(text, names):
    """Drop every source sentence and return the page names it used."""
    found = []
    cleaned = text
    for start, end, pages in reversed(_source_spans(text, names)):
        found[0:0] = pages
        cleaned = cleaned[:start] + " " + cleaned[end:]
    kept = []
    for paragraph in re.split(r"\n\s*\n", cleaned.strip()):
        lines = []
        for line in paragraph.split("\n"):
            line = re.sub(r"[^\S\n]{2,}", " ", line).strip()
            if line:
                lines.append(line)
        if lines:
            kept.append("\n".join(lines))
    return "\n\n".join(kept).strip(), found


def _source_tag(names):
    """Return 'From A.' or 'From A and B.' for these page names."""
    if len(names) == 1:
        return f"From {names[0]}."
    if len(names) == 2:
        return f"From {names[0]} and {names[1]}."
    return "From " + ", ".join(names[:-1]) + f", and {names[-1]}."


def _with_pages(body, names):
    """End body with a citation that names every given page."""
    tag = _source_tag(names)
    body = body.strip()
    if not body:
        return tag
    if body.endswith((".", "!", "?")):
        return f"{body} {tag}"
    return f"{body}. {tag}"


def _uses_opening_hours(body, page):
    """True when body uses an opening-hours fact written on this page."""
    text = page.get("text") or ""
    folded = body.casefold()
    for clock in _CLOCK.findall(text):
        if clock.casefold() in folded:
            return True
    if re.search(r"\bopen\s+saturdays?\b", folded) and re.search(
        r"\bopen\s+saturdays?\b", text, re.IGNORECASE
    ):
        return True
    if re.search(r"\bclosed\b", folded) and re.search(r"\bsundays?\b", folded):
        if re.search(r"\bclosed\b", text, re.IGNORECASE):
            return True
    return False


def _uses_booking(body, page):
    """True when body uses the booking line written on this page."""
    text = page.get("text") or ""
    if not re.search(r"\bbook\b", text, re.IGNORECASE):
        return False
    if not re.search(r"\b(?:book|cancel)\b", body, re.IGNORECASE):
        return False
    phone = _PHONE.search(text)
    if phone and phone.group(0) in body:
        return True
    if re.search(r"\bmain line\b", body, re.IGNORECASE) and re.search(
        r"\bmain line\b", text, re.IGNORECASE
    ):
        return True
    return False


def _name_every_page_used(reply, pages):
    """Name every page whose facts the reply uses, once."""
    if not isinstance(reply, str):
        return reply
    text = reply.strip()
    if not text:
        return text
    names = _ordered_names(pages)
    if not names:
        return text
    body, cited = _without_source_lines(text, names)
    used = []
    for name in cited:
        if name not in used:
            used.append(name)
    hours = _read_named(pages, "hours")
    contact = _read_named(pages, "contact")
    if hours is not None and _uses_opening_hours(body, hours):
        name = " ".join(str(hours.get("name", "")).split())
        if name and name not in used:
            used.append(name)
    if contact is not None and _uses_booking(body, contact):
        name = " ".join(str(contact.get("name", "")).split())
        if name and name not in used:
            used.append(name)
    ordered = [name for name in names if name in used]
    if not ordered:
        return reply
    rebuilt = _with_pages(body, ordered)
    if rebuilt == text:
        return reply
    return rebuilt
