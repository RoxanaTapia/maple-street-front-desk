"""Shared helpers for the answer tests."""

import os
import re
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import agreed
import serve_sample_site

AGREEMENTS = ROOT / "docs" / "agreements.md"
CLOCK = re.compile(r"\d{1,2}:\d{2} am to \d{1,2}:\d{2} pm", re.IGNORECASE)
question_rows = agreed.question_rows
page_named = agreed.page_named

class RunningSite:
    def __init__(self):
        serve_sample_site.pricing_live = True
        self.httpd = serve_sample_site.make_server("127.0.0.1", 0)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        deadline = time.time() + 3
        last_error = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(self.base + "/", timeout=0.5) as response:
                    response.read()
                    if response.status == 200:
                        return
            except Exception as error:
                last_error = error
                time.sleep(0.02)
        raise AssertionError(f"sample site did not start: {last_error}")

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)

class _SavedEnv:
    """Keep a developer key from turning the automated tests into a live call."""

    def __init__(self):
        self.key = os.environ.pop("ANTHROPIC_API_KEY", None)
        self.model = os.environ.pop("CLAUDE_MODEL", None)

    def restore(self):
        if self.key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = self.key
        if self.model is None:
            os.environ.pop("CLAUDE_MODEL", None)
        else:
            os.environ["CLAUDE_MODEL"] = self.model

class _FrozenClock:
    """A clock that always reports one instant, so the failure note is exact."""

    when = datetime(2026, 11, 7, 15, 30, 0, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls.when

def docs():
    files = []
    for pattern in ("*.md", "*.mdc"):
        files.extend(ROOT.rglob(pattern))
    return [path for path in files if ".git" not in path.parts]

def _wrapped_forms(message):
    """The same words with quotes, markdown, or a question mark around them."""
    forms = [
        f'"{message}"',
        f"'{message}'",
        f"`{message}`",
        f"**{message}**",
        f"*{message}*",
        f"_{message}_",
        f"“{message}”",
        f"‘{message}’",
        f"> {message}",
        f"# {message}",
        f"({message})",
        f"[{message}]",
        f'`"{message}"`',
        f'"{message}"?',
        message if message.endswith("?") else f"{message}?",
    ]
    return forms
