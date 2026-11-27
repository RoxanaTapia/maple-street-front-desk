"""Automated tests for the shared look on the chat page.

IconChecks is the "The four icons are served" area.
DemoKitCopyChecks is the "The demo kit copy matches" area.
The docstring of each test is what the checklist prints.

Run one area with
python3 scripts/run_checks.py tests/test_brand.py:IconChecks
or
python3 scripts/run_checks.py tests/test_brand.py:DemoKitCopyChecks.
"""

import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import demo_chat

KIT = ROOT / "vendor" / "demo-kit"
ICONS = {
    "/favicon.svg": "image/svg+xml",
    "/favicon-32.png": "image/png",
    "/apple-touch-icon.png": "image/png",
    "/favicon.ico": "image/x-icon",
}


class _Demo:
    def __init__(self):
        self.server = demo_chat.make_server("127.0.0.1", 0, "http://127.0.0.1:9")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.url = f"http://{host}:{port}"
        deadline = time.time() + 3
        last_error = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(self.url + "/favicon.svg", timeout=0.5) as response:
                    response.read()
                    if response.status == 200:
                        return
            except Exception as error:
                last_error = error
                time.sleep(0.02)
        raise AssertionError(f"demo did not start: {last_error}")

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def get(self, path):
        try:
            with urllib.request.urlopen(self.url + path, timeout=5) as response:
                return response.status, response.headers.get("Content-Type", ""), response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.headers.get("Content-Type", ""), error.read()


class IconChecks(unittest.TestCase):
    def setUp(self):
        self.demo = _Demo()

    def tearDown(self):
        self.demo.close()

    def test_the_four_icon_paths_answer(self):
        """favicon.svg, favicon-32.png, apple-touch-icon.png, and favicon.ico each return 200."""
        expected = {
            "/favicon.svg": KIT / "favicon.svg",
            "/favicon-32.png": KIT / "favicon-32.png",
            "/apple-touch-icon.png": KIT / "apple-touch-icon.png",
            "/favicon.ico": ROOT / "demo" / "favicon.ico",
        }
        self.assertEqual(set(expected), set(ICONS))
        for path, file_path in expected.items():
            status, content_type, body = self.demo.get(path)
            self.assertEqual(status, 200, path)
            self.assertIn(ICONS[path], content_type, path)
            self.assertEqual(body, file_path.read_bytes(), path)
        page_status, _page_type, page = self.demo.get("/")
        text = page.decode("utf-8")
        self.assertEqual(page_status, 200)
        for path in ICONS:
            self.assertIn(path, text, path)

    def test_the_shared_kit_files_load_from_this_server(self):
        """The theme, the font, and the stylesheet load from this server."""
        files = {
            "/demo-kit/demo-kit.css": "text/css",
            "/demo-kit/theme-init.js": "text/javascript",
            "/demo-kit/theme.js": "text/javascript",
            "/demo-kit/fonts/plus-jakarta-sans-latin.woff2": "font/woff2",
            "/demo-kit/fonts/bricolage-grotesque-latin.woff2": "font/woff2",
        }
        for path, kind in files.items():
            status, content_type, body = self.demo.get(path)
            self.assertEqual(status, 200, path)
            self.assertIn(kind, content_type, path)
            rel = path[len("/demo-kit/") :]
            self.assertEqual(body, (KIT / rel).read_bytes(), path)
        _status, _kind, script = self.demo.get("/demo-kit/theme-init.js")
        self.assertIn(b"rt_theme", script)
        for blocked in (
            "/demo-kit/../demo/index.html",
            "/demo-kit/%2e%2e/demo/index.html",
            "/demo-kit/fonts/../../scripts/demo_chat.py",
        ):
            status, _kind, _body = self.demo.get(blocked)
            self.assertEqual(status, 404, blocked)


class DemoKitCopyChecks(unittest.TestCase):
    def test_the_copied_kit_matches_version_2(self):
        """The copied demo kit matches version 2."""
        self.assertTrue((KIT / "check-hash.sh").is_file())
        self.assertEqual((KIT / "VERSION").read_text(encoding="utf-8").strip(), "2")
        pin = (ROOT / "vendor" / "DEMO-KIT.txt").read_text(encoding="utf-8")
        self.assertIn("5ad3b4bfc52f411cb6a634651a13bd62f9d3e584", pin)
        self.assertIn("Version: 2", pin)
        done = subprocess.run(
            ["sh", "check-hash.sh"],
            cwd=KIT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(done.returncode, 0, done.stderr or done.stdout)
        summed = subprocess.run(
            ["sha256sum", "--quiet", "-c", "SHA256SUMS"],
            cwd=KIT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(summed.returncode, 0, summed.stderr or summed.stdout)


if __name__ == "__main__":
    unittest.main()
