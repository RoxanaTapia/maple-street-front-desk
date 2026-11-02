"""Checks that an urgent message gets the fixed reply.

UrgentReplyChecks is the "Urgent messages get the fixed reply" area.
The words and the reply are read from your agreements. The docstring of
each test is what the checklist prints.

Run this area with
python3 scripts/run_checks.py tests/test_urgent.py:UrgentReplyChecks.
"""

import contextlib
import io
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import urgent_reply

AGREEMENTS = ROOT / "docs" / "agreements.md"
PHONE = re.compile(r"\(\d{3}\) \d{3}-\d{4}")


def _section(heading):
    found = False
    lines = []
    for line in AGREEMENTS.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if found:
                break
            found = line[3:].strip() == heading
            continue
        if found:
            lines.append(line)
    if not found:
        raise AssertionError(f"missing section {heading}")
    return lines


def quoted_urgent_words():
    words = []
    for line in _section("Urgent messages"):
        for word in re.findall(r"\*\*([^*]+)\*\*", line):
            word = word.strip()
            if word:
                words.append(word)
    return words


def blockquote_reply():
    parts = []
    for line in _section("Urgent messages"):
        stripped = line.strip()
        if stripped.startswith(">"):
            part = stripped[1:].strip()
            if part:
                parts.append(part)
    return " ".join(parts)


def _is_urgent_question(row):
    return row["group"] == "Handled by a set reply" and "urgent reply" in row["detail"].lower()


def question_rows():
    rows = []
    in_section = False
    group = None
    for line in AGREEMENTS.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if in_section:
                break
            in_section = line[3:].strip() == "The 15 test questions"
            continue
        if not in_section:
            continue
        bold = re.fullmatch(r"\*\*(.+?)\*\*", line.strip())
        if bold:
            group = bold.group(1).strip()
            continue
        match = re.match(r"^\d+\.\s+(.+)$", line.strip())
        if not match or not group:
            continue
        text = match.group(1).strip()
        mark = text.find("?")
        if mark == -1:
            question, detail = text, ""
        else:
            question = text[: mark + 1].strip()
            detail = text[mark + 1 :].strip()
        rows.append({"question": question, "detail": detail, "group": group})
    return rows


def near_misses(word):
    misses = [word + "x", "x" + word]
    parts = word.split()
    if len(parts) > 1:
        misses.append(" ".join(reversed(parts)))
        misses.append("  ".join(parts))
        misses.append(", ".join(parts))
        misses.append(parts[0])
        misses.append(parts[-1])
        misses.append(" ".join(parts[:-1] + [parts[-1] + "ing"]))
    elif len(word) > 6:
        misses.append(word[:-3])
    return misses


class UrgentReplyChecks(unittest.TestCase):
    def test_each_urgent_word_gets_the_fixed_reply(self):
        """Each urgent word gets the fixed reply, and nothing else."""
        words = quoted_urgent_words()
        reply = blockquote_reply()
        self.assertGreaterEqual(len(words), 1)
        self.assertTrue(reply)
        self.assertEqual(urgent_reply.urgent_words(), words)
        self.assertEqual(urgent_reply.fixed_urgent_reply(), reply)
        for word in words:
            for message in (
                word,
                word.upper(),
                word.title(),
                f"  {word}!  ",
                f"Help, we have {word} tonight.",
                f"Are you open Saturdays? {word}",
            ):
                got = urgent_reply.reply_if_urgent(message)
                self.assertEqual(got, reply, message)
                self.assertNotIn("\n", got)
        self.assertEqual(urgent_reply.reply_if_urgent(" and ".join(words)), reply)
        urgent_questions = [row for row in question_rows() if _is_urgent_question(row)]
        self.assertGreaterEqual(len(urgent_questions), 1)
        for row in urgent_questions:
            self.assertEqual(urgent_reply.reply_if_urgent(row["question"]), reply)

    def test_a_normal_question_is_not_treated_as_urgent(self):
        """A normal question is not treated as urgent."""
        normal = [row for row in question_rows() if not _is_urgent_question(row)]
        self.assertGreaterEqual(len(normal), 1)
        for row in normal:
            self.assertIsNone(
                urgent_reply.reply_if_urgent(row["question"]),
                row["question"],
            )
        for word in quoted_urgent_words():
            for message in near_misses(word):
                self.assertIsNone(urgent_reply.reply_if_urgent(message), message)
        self.assertIsNone(urgent_reply.reply_if_urgent(""))
        self.assertIsNone(urgent_reply.reply_if_urgent("   "))
        self.assertIsNone(urgent_reply.reply_if_urgent(None))
        phone = PHONE.search(blockquote_reply())
        self.assertIsNotNone(phone)
        self.assertIsNone(urgent_reply.reply_if_urgent(f"Please call {phone.group(0)}"))

    def test_the_words_and_the_reply_are_read_from_your_agreements(self):
        """The words and the reply are read from your agreements."""
        words = quoted_urgent_words()
        reply = blockquote_reply()
        source = (SCRIPTS / "urgent_reply.py").read_text(encoding="utf-8")
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        how = (ROOT / "docs" / "how-it-works.md").read_text(encoding="utf-8")
        self.assertNotIn(reply, source)
        self.assertNotIn(reply, behaviour)
        self.assertNotIn(reply, readme)
        self.assertNotIn(reply, how)
        for word in words:
            self.assertNotIn(f'"{word}"', source)
            self.assertNotIn(f"'{word}'", source)
            self.assertNotIn(word, behaviour)
        sample = (
            "## Urgent messages\n\n"
            "When a message mentions **roof leak** or **no water**, it replies with exactly this:\n\n"
            "> Please call\n"
            "> the owner.\n"
        )
        self.assertEqual(
            urgent_reply.urgent_words(sample),
            ["roof leak", "no water"],
        )
        self.assertEqual(
            urgent_reply.fixed_urgent_reply(sample),
            "Please call the owner.",
        )
        self.assertEqual(
            urgent_reply.reply_if_urgent("There is a roof leak", text=sample),
            "Please call the owner.",
        )
        self.assertIsNone(urgent_reply.reply_if_urgent("hello", text=sample))
        with self.assertRaises(ValueError):
            urgent_reply.reply_if_urgent(
                "roof leak",
                text="## Urgent messages\n\nWhen a message mentions **roof leak**, reply.\n",
            )
        with self.assertRaises(ValueError):
            urgent_reply.urgent_words(text="## When the pages don't say\n\n> Hello.\n")
        with self.assertRaises(ValueError):
            urgent_reply.fixed_urgent_reply(text="## Urgent messages\n\n**roof leak**\n")

    def test_an_urgent_message_does_not_read_your_pages(self):
        """An urgent message does not read your pages."""
        source = (SCRIPTS / "urgent_reply.py").read_text(encoding="utf-8")
        for banned in (
            "read_pages",
            "urllib",
            "urlopen",
            "socket",
            "subprocess",
            "sample-site",
            "openai",
            "anthropic",
        ):
            self.assertNotIn(banned, source)
        word = quoted_urgent_words()[0]
        self.assertEqual(
            urgent_reply.reply_if_urgent(f"We have {word}."),
            blockquote_reply(),
        )

    def test_the_phone_number_in_the_urgent_reply_is_not_a_price(self):
        """The phone number in the urgent reply is not treated as a price."""
        reply = blockquote_reply()
        phone = PHONE.search(reply)
        self.assertIsNotNone(phone)
        self.assertNotIn("$", reply)
        for word in quoted_urgent_words():
            got = urgent_reply.reply_if_urgent(f"{word} costs $50")
            self.assertEqual(got, reply)
            self.assertIn(phone.group(0), got)
            self.assertNotIn("$", got)

    def test_checking_a_message_prints_the_fixed_reply(self):
        """Checking a message prints the fixed reply when it is urgent, and says it is not when it is not."""
        reply = blockquote_reply()
        for word in quoted_urgent_words():
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = urgent_reply.main([f"We have {word}."])
            self.assertEqual(code, 0)
            self.assertEqual(stdout.getvalue(), reply + "\n")
        normal = next(row["question"] for row in question_rows() if not _is_urgent_question(row))
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = urgent_reply.main(normal.split())
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), urgent_reply.NOT_URGENT + "\n")
        self.assertNotEqual(stdout.getvalue().strip(), reply)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(urgent_reply.main(["--help"]), 2)
        self.assertIn("Usage:", stderr.getvalue())
        self.assertNotIn(reply, stderr.getvalue())
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(urgent_reply.main([]), 2)

    def test_you_see_this_check_on_the_pull_request(self):
        """You see this check on the pull request as Urgent messages get the fixed reply."""
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("name: Urgent messages get the fixed reply\n", workflow)
        self.assertIn("tests/test_urgent.py:UrgentReplyChecks", workflow)
        behaviour = (ROOT / "docs" / "behaviour.md").read_text(encoding="utf-8")
        self.assertIn("An urgent message", behaviour)
        self.assertIn("fixed urgent reply", behaviour)
        how = (ROOT / "docs" / "how-it-works.md").read_text(encoding="utf-8")
        section = how.split("## 1 · Spot an emergency", 1)[1].split("## 2 ·", 1)[0]
        self.assertIn("**Urgent messages get the fixed reply**", section)


if __name__ == "__main__":
    unittest.main()
