"""Read the agreed pages and print a page list.

1. Which pages: agreed_pages reads the names under "Your pages".
2. Fetching: fetch requests each page over HTTP. A page that cannot be fetched is marked unreadable with the reason and stays on the list.
3. Reading: TitleTextParser takes the title and the visible text. Script and style elements are ignored.
4. Page list: format_page_list prints each page's name, title, address, and status.

Usage: python3 scripts/read_pages.py [site address]

With no address, reads http://127.0.0.1:8000, the address the sample site prints by default.
"""

import re
import sys
import urllib.error
import urllib.request
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGREEMENTS = ROOT / "docs" / "agreements.md"
PAGES_HEADING = "Your pages"
DEFAULT_SITE = "http://127.0.0.1:8000"
_NAV_LINK = re.compile(r'<a href="([^"]+)">([^<]+)</a>')
_PAGE_LIST = re.compile(r"pages of your website:\s*(.+?)\.")


class TitleTextParser(HTMLParser):
    """Collect the title and the visible text of a page."""

    def __init__(self):
        super().__init__()
        self._in_title = False
        self._skip = 0
        self._title_parts = []
        self._text_parts = []

    def handle_starttag(self, tag, attrs):
        name = tag.lower()
        if name == "title":
            self._in_title = True
        if name in {"script", "style"}:
            self._skip += 1

    def handle_endtag(self, tag):
        name = tag.lower()
        if name == "title":
            self._in_title = False
        if name in {"script", "style"} and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)
            return
        if self._skip:
            return
        self._text_parts.append(data)

    @property
    def title(self):
        return _collapse(self._title_parts)

    @property
    def text(self):
        return _collapse(self._text_parts)


def _collapse(parts):
    return " ".join("".join(parts).split())


def _section(body, heading):
    found = False
    lines = []
    for line in body.splitlines():
        if line.startswith("## "):
            title = line[3:].strip().strip("#").strip()
            if found:
                break
            found = title == heading
            continue
        if found:
            lines.append(line)
    if not found:
        raise ValueError(f"No pages found under {heading}")
    return lines


def _page_names(section_lines):
    text = " ".join(line.strip() for line in section_lines)
    match = _PAGE_LIST.search(text)
    if not match:
        raise ValueError(f"No pages found under {PAGES_HEADING}")
    raw = re.sub(r"\band\b", ",", match.group(1))
    names = [part.strip() for part in raw.split(",") if part.strip()]
    if not names:
        raise ValueError(f"No pages found under {PAGES_HEADING}")
    return names


def _paths_on_the_sample_site():
    index = (ROOT / "sample-site" / "index.html").read_text(encoding="utf-8")
    paths = {}
    for href, label in _NAV_LINK.findall(index):
        name = unescape(label).strip()
        if href in {"index.html", "/"}:
            path = "/"
        elif href.startswith("/"):
            path = href
        else:
            path = "/" + href
        paths[name] = path
    return paths


def agreed_pages(text=None):
    """Return each page's name and path from Your pages."""
    body = AGREEMENTS.read_text(encoding="utf-8") if text is None else text
    paths = _paths_on_the_sample_site()
    pages = []
    for name in _page_names(_section(body, PAGES_HEADING)):
        path = paths.get(name, "")
        if not path.startswith("/"):
            raise ValueError(f"{name} is missing a path in the page list")
        pages.append({"name": name, "path": path})
    return pages


def page_address(base_url, path):
    if not path.startswith("/"):
        path = "/" + path
    return base_url.rstrip("/") + path


def _unreadable(reason):
    return {"title": "", "text": "", "status": "unreadable", "reason": reason}


def _read_html(html):
    parser = TitleTextParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as error:
        return _unreadable(f"Could not read the page: {error}")
    if not parser.title:
        return _unreadable("The page has no title")
    return {
        "title": parser.title,
        "text": parser.text,
        "status": "read",
        "reason": "",
    }


def fetch(url):
    """Fetch one page. A failure is returned, not raised."""
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            html = response.read().decode(charset, errors="replace")
            if response.status != 200:
                return _unreadable(f"HTTP {response.status}")
            return _read_html(html)
    except urllib.error.HTTPError as error:
        phrase = error.reason if isinstance(error.reason, str) else ""
        reason = f"HTTP {error.code} {phrase}".strip()
        try:
            body = error.read().decode("utf-8", errors="replace").strip()
        except Exception:
            body = ""
        if body and "<" not in body and len(body) <= 200:
            reason = f"{reason}: {body}"
        return _unreadable(reason)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        detail = getattr(error, "reason", error)
        text = detail if isinstance(detail, str) else str(detail)
        return _unreadable(text)


def read_pages(base_url):
    """Fetch every agreed page and return the page list."""
    pages = []
    for agreed in agreed_pages():
        address = page_address(base_url, agreed["path"])
        fetched = fetch(address)
        pages.append(
            {
                "name": agreed["name"],
                "title": fetched["title"],
                "text": fetched["text"],
                "address": address,
                "status": fetched["status"],
                "reason": fetched["reason"],
            }
        )
    return pages


def format_page_list(pages):
    lines = ["Page list", ""]
    for page in pages:
        title = page["title"] if page["title"] else "(no title)"
        if page["status"] == "read":
            status = "read"
        else:
            status = f"unreadable ({page['reason']})"
        lines.extend(
            [
                page["name"],
                f"  Title: {title}",
                f"  Address: {page['address']}",
                f"  Status: {status}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if any(arg in {"-h", "--help"} for arg in args) or len(args) > 1:
        print(
            "Usage: python3 scripts/read_pages.py [site address]\n"
            f"With no address, reads {DEFAULT_SITE}.",
            file=sys.stderr,
        )
        return 2
    base = args[0] if args else DEFAULT_SITE
    try:
        pages = read_pages(base)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    sys.stdout.write(format_page_list(pages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
