"""Automated tests for the Saturday night messages on the demo page.

CaseFlowChecks is the "Each Saturday night chip gets the right reply" area.
Each ready message is sent through the demo, and the reply type is the
one that message should get. The docstring of each test is what the
run prints.

Run one area with
python3 scripts/run_checks.py tests/test_case_flow.py:CaseFlowChecks.
"""

import json
import os
import re
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
import front_desk
import read_pages
import serve_sample_site
import urgent_reply

BURST = "It's Saturday night and my sink is leaking"
DRAIN = "How much is drain cleaning?"
HEATER = "Water heater price?"
PIZZA = "Do you sell pizza?"
PROOF = "15 of 15 test questions answered right, 4 Nov 2026"
URGENT_TAG = "Urgent rule · no AI needed"
PHONE = "030 0000 0000"


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
        import demo_chat
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
        try:
            with urllib.request.urlopen(self.url + path, timeout=5) as response:
                body = response.read().decode("utf-8")
                return response.status, dict(response.headers), body
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8")
            return error.code, dict(error.headers), raw

    def post(self, message, trace=False):
        payload = {"message": message}
        if trace:
            payload["trace"] = True
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.url + "/reply",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read().decode("utf-8")
            return response.status, raw, json.loads(raw)


class CaseFlowChecks(unittest.TestCase):
    def setUp(self):
        self.env = _SavedEnv()
        self.demo = RunningDemo()

    def tearDown(self):
        self.demo.close()
        serve_sample_site.pricing_live = True
        self.env.restore()

    def _traced(self, message):
        status, raw, parsed = self.demo.post(message, trace=True)
        self.assertEqual(status, 200, message)
        self.assertEqual(set(parsed), {"reply", "checks", "tag", "sources"}, message)
        self.assertNotIn("—", raw, message)
        self.assertNotIn("simulated", raw.casefold(), message)
        self.assertNotIn("simulation", raw.casefold(), message)
        plain_status, plain_raw, plain = self.demo.post(message, trace=False)
        self.assertEqual(plain_status, 200, message)
        self.assertEqual(plain, {"reply": parsed["reply"]}, message)
        self.assertNotIn("checks", json.loads(plain_raw), message)
        return parsed

    def test_a_burst_pipe_gets_the_urgent_reply(self):
        """It's Saturday night and my sink is leaking gets the urgent reply."""
        expected = urgent_reply.fixed_urgent_reply()
        trace = {}
        direct = front_desk.reply_to(BURST, base_url=self.demo.base, trace=trace)
        self.assertEqual(direct, expected)
        self.assertEqual(trace.get("steps"), ["urgent"])
        self.assertNotIn("pages", trace)
        parsed = self._traced(BURST)
        self.assertEqual(parsed["reply"], expected)
        self.assertEqual(parsed["checks"], ["Urgent rule"])
        self.assertEqual(parsed["tag"], URGENT_TAG)
        self.assertEqual(parsed["sources"], [])
        self.assertIn(PHONE, parsed["reply"])
        self.assertNotIn("From ", parsed["reply"])
        self.assertNotIn("$", parsed["reply"])

    def test_drain_cleaning_gets_the_pricing_reply(self):
        """How much is drain cleaning? gets the price from the Pricing page."""
        parsed = self._traced(DRAIN)
        self.assertEqual(parsed["reply"], "A drain cleaning is $149. From Pricing.")
        self.assertEqual(parsed["checks"], ["Page match", "Price check"])
        self.assertEqual(parsed["tag"], "")
        self.assertEqual(len(parsed["sources"]), 1)
        source = parsed["sources"][0]
        self.assertEqual(source["label"], "Pricing page")
        self.assertEqual(set(source), {"label", "excerpt"})
        pages = read_pages.read_pages(self.demo.base)
        pricing = next(page for page in pages if page["name"] == "Pricing")
        self.assertIn(source["excerpt"], pricing["text"])
        self.assertIn("$149", source["excerpt"])
        self.assertNotIn("Home Services", source["excerpt"])

    def test_a_water_heater_price_gets_the_callback(self):
        """Water heater price? gets the callback reply."""
        expected = answer_reply.callback_reply()
        parsed = self._traced(HEATER)
        self.assertEqual(parsed["reply"], expected)
        self.assertNotEqual(parsed["reply"], urgent_reply.fixed_urgent_reply())
        self.assertEqual(parsed["checks"], ["Page match", "Price check"])
        self.assertEqual(parsed["tag"], "")
        self.assertEqual(parsed["sources"], [])
        self.assertNotIn("$", parsed["reply"])
        self.assertIn(PHONE, parsed["reply"])

    def test_pizza_gets_the_off_topic_reply(self):
        """Do you sell pizza? gets the off-topic reply."""
        expected = answer_reply.off_topic_reply()
        parsed = self._traced(PIZZA)
        self.assertEqual(parsed["reply"], expected)
        self.assertNotEqual(parsed["reply"], answer_reply.callback_reply())
        self.assertNotEqual(parsed["reply"], answer_reply.outage_reply())
        self.assertEqual(parsed["checks"], ["Page match", "Price check"])
        self.assertEqual(parsed["tag"], "")
        self.assertEqual(parsed["sources"], [])
        self.assertNotIn(PHONE, parsed["reply"])

    def test_the_page_shows_the_saturday_night_flow(self):
        """The page shows the four messages, the greeting, and the quiet footer."""
        status, _headers, body = self.demo.get("/")
        self.assertEqual(status, 200)
        for message in (BURST, DRAIN, HEATER, PIZZA):
            self.assertIn(f'data-message="{message}"', body)
            self.assertIn(message, body)
        self.assertIn("Maple Street Plumbing", body)
        self.assertIn("Saturday night", body)
        self.assertNotIn('class="scene"', body)
        self.assertIn('<h1 class="dk-product">Maple Street front desk</h1>', body)
        self.assertIn("Portfolio demo · fictional business", body)
        self.assertNotIn("sample data", body)
        self.assertIn("Hi, I'm the Maple Street front desk.", body)
        self.assertIn("How can I help?", body)
        self.assertNotIn(PROOF, body)
        self.assertNotIn('href="/docs/test-results.md"', body)
        self.assertNotIn("Next: the same rules on a phone call", body)
        self.assertNotIn("A live chat assistant. Voice is the next step.", body)
        self.assertIn(
            'href="https://roxanatapia.dev/cases/front-desk">How it\'s built</a>',
            body,
        )
        self.assertIn("/demo-kit/motion.js", body)
        self.assertNotIn("—", body)
        self.assertNotIn("simulated", body.casefold())
        self.assertNotIn("simulation", body.casefold())
        self.assertIsNone(re.search(r"\(\d{3}\)\s*\d{3}", body))
        script = (ROOT / "demo" / "chat.js").read_text(encoding="utf-8")
        css = (ROOT / "demo" / "style.css").read_text(encoding="utf-8")
        self.assertNotIn("Answered in ", script)
        self.assertNotIn("toFixed(1)", script)
        self.assertNotIn("Behind this reply", script)
        self.assertNotIn("Urgent rule", script)
        self.assertNotIn("no AI needed", script)
        self.assertIn("prefers-reduced-motion: reduce", script)
        self.assertIn("dk-enter", script)
        self.assertIn("textContent", script)
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("1.2s", script)
        self.assertNotIn("—", script)
        self.assertIn("prefers-reduced-motion: reduce", css)
        self.assertIn(".typing", css)
        self.assertNotIn("\n  height: 100dvh;", css)
        self.assertIn("min-height: 100dvh", css)
        self.assertIn("overflow: visible", css)
        self.assertIn("max-width: 28rem", css)
        self.assertIn("max-width: 42rem", css)
        desktop = css.split("@media (min-width: 800px)", 1)[1]
        self.assertIn("max-width: 42rem", desktop)
        self.assertLess(css.index("max-width: 28rem"), css.index("@media (min-width: 800px)"))
        self.assertIn("h1.dk-product {\n  margin: 0;\n}", css)
        self.assertNotIn("—", css)
        results = (ROOT / "docs" / "test-results.md").read_text(encoding="utf-8")
        self.assertIn("15 of 15", results)
        self.assertIn("Nov 4, 2026", results)
        doc_status, doc_headers, doc = self.demo.get("/docs/test-results.md")
        self.assertEqual(doc_status, 200)
        self.assertIn("text/plain", doc_headers.get("Content-Type", ""))
        self.assertIn("15 of 15", doc)
        self.assertEqual(doc, results)
        blocked, _blocked_headers, _blocked_body = self.demo.get("/docs/agreements.md")
        self.assertEqual(blocked, 404)
        escaped, _escaped_headers, _escaped_body = self.demo.get("/docs/../scripts/demo_chat.py")
        self.assertEqual(escaped, 404)


if __name__ == "__main__":
    unittest.main()
