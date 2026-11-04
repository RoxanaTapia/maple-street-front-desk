"""Checks for the demo chat page.

DemoChatChecks is the "The demo chat gives the same replies" area.
The page runs each message through the front desk. The docstring of
each test is what the checklist prints.

Run one area with
python3 scripts/run_checks.py tests/test_demo.py:DemoChatChecks.
"""

import json
import os
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

import answer_reply
import demo_chat
import front_desk
import read_pages
import serve_sample_site
import urgent_reply

DEMO_LINE = "This is a demo. It answers only from Maple Street's pages."


class _SavedEnv:
    def __init__(self):
        self.values = {
            name: os.environ.pop(name, None)
            for name in ("ANTHROPIC_API_KEY", "CLAUDE_MODEL", "DEMO_HOST", "DEMO_PORT")
        }

    def restore(self):
        for name, value in self.values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class RunningDemo:
    def __init__(self):
        serve_sample_site.pricing_live = True
        self.site = serve_sample_site.make_server(serve_sample_site.DEFAULT_HOST, 0)
        self.site_thread = threading.Thread(target=self.site.serve_forever, daemon=True)
        self.site_thread.start()
        site_host, site_port = self.site.server_address[:2]
        self.base = f"http://{site_host}:{site_port}"
        self._wait(self.base + "/")
        self.demo = demo_chat.make_server("127.0.0.1", 0, self.base)
        self.demo_thread = threading.Thread(target=self.demo.serve_forever, daemon=True)
        self.demo_thread.start()
        host, port = self.demo.server_address[:2]
        self.url = f"http://{host}:{port}"
        self._wait(self.url + "/")

    def _wait(self, url):
        deadline = time.time() + 3
        last_error = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=0.5) as response:
                    response.read()
                    if response.status == 200:
                        return
            except Exception as error:
                last_error = error
                time.sleep(0.02)
        raise AssertionError(f"demo did not start: {last_error}")

    def close(self):
        self.demo.shutdown()
        self.demo.server_close()
        self.demo_thread.join(timeout=2)
        self.site.shutdown()
        self.site.server_close()
        self.site_thread.join(timeout=2)

    def get(self, path):
        with urllib.request.urlopen(self.url + path, timeout=5) as response:
            body = response.read().decode("utf-8")
            return response.status, dict(response.headers), body

    def post(self, message, extra=None):
        payload = {"message": message}
        if extra:
            payload.update(extra)
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.url + "/reply",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                raw = response.read().decode("utf-8")
                return response.status, dict(response.headers), raw, json.loads(raw)
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return error.code, dict(error.headers), raw, parsed


class DemoChatChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self._post = answer_reply._post_message
        self.demo = RunningDemo()

    def tearDown(self):
        answer_reply._post_message = self._post
        self.demo.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def _reply(self, message):
        status, headers, raw, parsed = self.demo.post(message)
        self.assertEqual(status, 200, message)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        self.assertEqual(parsed, {"reply": parsed.get("reply")}, message)
        self.assertIsInstance(parsed["reply"], str)
        return raw, parsed["reply"]

    def test_an_urgent_message_gets_the_urgent_reply(self):
        """I have a frozen pipe gets the urgent reply."""
        expected = urgent_reply.fixed_urgent_reply()
        self.assertEqual(urgent_reply.reply_if_urgent("I have a frozen pipe"), expected)
        raw, got = self._reply("I have a frozen pipe")
        self.assertEqual(got, expected)
        self.assertEqual(got, front_desk.reply_to("I have a frozen pipe", base_url=self.demo.base))
        self.assertNotIn("\n", got)
        self.assertNotIn("<", raw)

    def test_hours_come_from_the_hours_page(self):
        """What are your hours gets an answer from Hours & FAQ."""
        expected = front_desk.reply_to("What are your hours?", base_url=self.demo.base)
        callback = answer_reply.callback_reply()
        pages = read_pages.read_pages(self.demo.base)
        hours = next(page for page in pages if page["name"] == "Hours & FAQ")
        self.assertNotEqual(expected, callback)
        self.assertTrue(expected.endswith("From Hours & FAQ."))
        body = expected[: -len("From Hours & FAQ.")].strip()
        self.assertIn(body, hours["text"])
        self.assertIn("8:00 am", expected)
        raw, got = self._reply("What are your hours?")
        self.assertEqual(got, expected)
        self.assertNotIn("<", raw)

    def test_a_question_the_pages_dont_cover_gets_the_callback(self):
        """Do you sell pizza gets the callback reply."""
        callback = answer_reply.callback_reply()
        self.assertEqual(
            front_desk.reply_to("Do you sell pizza?", base_url=self.demo.base),
            callback,
        )
        raw, got = self._reply("Do you sell pizza?")
        self.assertEqual(got, callback)
        self.assertNotIn("<", raw)

    def test_a_reply_is_shown_as_text(self):
        """A reply is shown as text, not as HTML."""
        marker = "<script>alert(1)</script>"
        original = front_desk.reply_to

        def fake(message, base_url=None, writer=None, client=None):
            return marker

        front_desk.reply_to = fake
        try:
            status, headers, raw, parsed = self.demo.post("Hello")
        finally:
            front_desk.reply_to = original
        self.assertEqual(status, 200)
        self.assertEqual(parsed["reply"], marker)
        self.assertNotIn("<script>", raw)
        self.assertNotIn("<img", raw)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        script = (ROOT / "demo" / "chat.js").read_text(encoding="utf-8")
        self.assertIn("textContent", script)
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("insertAdjacentHTML", script)
        self.assertNotIn("document.write", script)
        page = (ROOT / "demo" / "index.html").read_text(encoding="utf-8")
        self.assertIn('name="viewport"', page)
        self.assertIn(DEMO_LINE, page)

    def test_the_key_never_appears_in_a_response(self):
        """The Claude key never appears in a response."""
        secret = "demo-key-should-stay-on-the-server"
        self.assertGreaterEqual(len(secret), demo_chat._KEY_MIN)
        os.environ["ANTHROPIC_API_KEY"] = secret

        def leak(payload, key, timeout):
            self.assertEqual(key, secret)
            self.assertNotIn(secret, json.dumps(payload))
            return {"content": [{"type": "text", "text": f"The key is {key}"}]}

        answer_reply._post_message = leak
        for path in ("/", "/style.css", "/chat.js"):
            status, headers, body = self.demo.get(path)
            self.assertEqual(status, 200, path)
            self.assertNotIn(secret, body, path)
            self.assertNotIn(secret, str(headers), path)
        for message in ("I have a frozen pipe", "What are your hours?", "Do you sell pizza?"):
            status, headers, raw, parsed = self.demo.post(message, extra={"apiKey": secret})
            self.assertEqual(status, 200, message)
            self.assertNotIn(secret, raw, message)
            self.assertNotIn(secret, parsed["reply"], message)
            self.assertNotIn(secret, str(headers), message)
        self.assertEqual(parsed["reply"], answer_reply.callback_reply())
        for name in ("demo/index.html", "demo/style.css", "demo/chat.js", "scripts/demo_chat.py"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn(secret, text, name)
            self.assertNotIn("sk-ant-", text, name)
        source = (ROOT / "scripts" / "demo_chat.py").read_text(encoding="utf-8")
        self.assertNotIn("print(os.environ", source)
        self.assertIn("def log_message", source)

    def test_the_address_comes_from_the_environment(self):
        """The demo listens on the host and port from the environment."""
        self.assertEqual(demo_chat.listen_address(), ("127.0.0.1", 8080))
        os.environ["DEMO_HOST"] = "0.0.0.0"
        os.environ["DEMO_PORT"] = "9090"
        self.assertEqual(demo_chat.listen_address(), ("0.0.0.0", 9090))
        os.environ["DEMO_PORT"] = "nope"
        with self.assertRaises(ValueError):
            demo_chat.listen_address()
        os.environ["DEMO_PORT"] = "8080"
        os.environ["DEMO_HOST"] = "http://127.0.0.1"
        with self.assertRaises(ValueError):
            demo_chat.listen_address()
        source = (ROOT / "scripts" / "demo_chat.py").read_text(encoding="utf-8")
        self.assertIn("DEMO_HOST", source)
        self.assertIn("DEMO_PORT", source)
        self.assertEqual(demo_chat.DEFAULT_HOST, "127.0.0.1")

    def test_enter_sends_the_message(self):
        """Press Enter sends the message, and Shift+Enter adds a new line."""
        page = (ROOT / "demo" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "demo" / "chat.js").read_text(encoding="utf-8")
        self.assertIn("Press Enter to send. Shift+Enter adds a new line.", page)
        self.assertIn('id="message-hint"', page)
        self.assertIn("keydown", script)
        self.assertIn("shiftKey", script)
        self.assertIn("isComposing", script)
        self.assertIn("compositionstart", script)
        self.assertIn("compositionend", script)
        self.assertIn("keyCode === 229", script)
        self.assertIn("!box.value.trim()", script)
        self.assertIn("requestSubmit", script)

    def test_the_page_says_it_is_a_demo(self):
        """The page says it is a demo that answers only from Maple Street's pages."""
        status, _headers, body = self.demo.get("/")
        self.assertEqual(status, 200)
        self.assertIn(DEMO_LINE, body)
        self.assertIn("Maple Street Front Desk", body)
