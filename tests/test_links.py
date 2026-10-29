"""Fail when a relative Markdown link points at a missing file or heading.

Heading anchors use GitHub's slug rules: lowercase, punctuation removed,
spaces turned into hyphens, and a repeated slug gets -1, -2, and so on.
"""

import re
import unittest
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

# Same punctuation GitHub drops when it builds a heading anchor.
_PUNCTUATION = re.compile(r"[\u2000-\u206F\u2E00-\u2E7F\\'\"!#$%&()*+,./:;<=>?@\[\]^`{|}~]")
_LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^(```|~~~)")


def github_slug(text):
    slug = _PUNCTUATION.sub("", text.lower().strip())
    return re.sub(r"\s", "-", slug)


def _without_frontmatter(text):
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end == -1:
        return text
    return text[end + 5 :]


def _without_fences(text):
    kept = []
    in_fence = False
    for line in text.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        kept.append("" if in_fence else line)
    return "\n".join(kept)


def heading_slugs(text):
    body = _without_fences(_without_frontmatter(text))
    counts = {}
    slugs = set()
    for line in body.splitlines():
        match = _HEADING.match(line)
        if not match:
            continue
        title = re.sub(r"[*`]", "", match.group(2)).strip()
        base = github_slug(title)
        seen = counts.get(base, 0)
        counts[base] = seen + 1
        slugs.add(base if seen == 0 else f"{base}-{seen}")
    return slugs


def _markdown_files():
    files = []
    for pattern in ("*.md", "*.mdc"):
        files.extend(ROOT.rglob(pattern))
    return [path for path in files if ".git" not in path.parts]


def broken_links():
    problems = []
    for path in _markdown_files():
        text = _without_fences(_without_frontmatter(path.read_text(encoding="utf-8")))
        for match in _LINK.finditer(text):
            raw = unquote(match.group(1).strip())
            if re.match(r"^[a-z][a-z0-9+.-]*:", raw, re.I):
                continue
            path_part, _, fragment = raw.partition("#")
            if path_part in ("",):
                target = path
            else:
                target = (path.parent / path_part).resolve()
            try:
                target.relative_to(ROOT.resolve())
            except ValueError:
                problems.append(f"{path.relative_to(ROOT)} -> {raw} leaves the project")
                continue
            if not target.exists():
                problems.append(f"{path.relative_to(ROOT)} -> {raw} (missing file)")
                continue
            if not fragment:
                continue
            if target.is_dir():
                problems.append(f"{path.relative_to(ROOT)} -> {raw} (anchor on a folder)")
                continue
            slugs = heading_slugs(target.read_text(encoding="utf-8"))
            if fragment not in slugs:
                problems.append(f"{path.relative_to(ROOT)} -> {raw} (missing heading)")
    return problems


class LinkChecks(unittest.TestCase):
    def test_github_slug_matches_known_headings(self):
        """Headings keep a working link, even with an apostrophe or an &."""
        self.assertEqual(github_slug("What you've agreed"), "what-youve-agreed")
        self.assertEqual(github_slug("Pages the assistant answers from"), "pages-the-assistant-answers-from")
        self.assertEqual(github_slug("How a change happens"), "how-a-change-happens")
        self.assertEqual(github_slug("Hours & FAQ"), "hours--faq")

    def test_relative_links_resolve(self):
        """Every link in the docs points at a real page and heading."""
        problems = broken_links()
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
