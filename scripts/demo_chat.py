"""Serve a demo chat page for one customer message at a time.

Each message goes through the front desk: the urgent reply, your pages,
the answer, and the price check. The page adds no rules of its own.
The sample site starts with this server, so one command is enough.

The Claude key is read later, from the server's own settings, and is
never sent to the browser. DEMO_HOST and DEMO_PORT choose where the
page listens. The default is http://127.0.0.1:8080.

Usage: python3 scripts/demo_chat.py
"""

import errno
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import answer_reply
import front_desk
import serve_sample_site

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"
HOST_ENV = "DEMO_HOST"
PORT_ENV = "DEMO_PORT"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
# A real key is long. A short setting is left alone so a reply is not damaged.
_KEY_MIN = 20
_MAX_BODY = 8000
_PAGES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/style.css": "style.css",
    "/chat.js": "chat.js",
}
_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}
USAGE = (
    "Usage: python3 scripts/demo_chat.py\n"
    "Serves a chat page that runs each message through the front desk.\n"
    f"Listens on {DEFAULT_HOST} port {DEFAULT_PORT} unless {HOST_ENV} or {PORT_ENV} is set."
)


def listen_address():
    """Return the host and port from the environment, or the local default."""
    host = os.environ.get(HOST_ENV, "").strip() or DEFAULT_HOST
    if "://" in host or "/" in host or "\\" in host or any(char.isspace() for char in host):
        raise ValueError(f"Set {HOST_ENV} to a host or an address.")
    raw = os.environ.get(PORT_ENV, "").strip()
    if not raw:
        port = DEFAULT_PORT
    elif raw.isdigit():
        port = int(raw)
    else:
        raise ValueError(f"Set {PORT_ENV} to a port number.")
    if not 1 <= port <= 65535:
        raise ValueError(f"Set {PORT_ENV} to a port number.")
    return host, port


def _json_bytes(payload):
    text = json.dumps(payload, ensure_ascii=False)
    # Keep the reply as data. A browser that sniffs the body still sees text.
    text = text.replace("<", "\\u003c").replace(">", "\\u003e")
    return text.encode("utf-8")


def safe_reply(message, base_url):
    """Return the front-desk reply, with the key kept off the page.

    A failed call is already the outage reply. Any other failure becomes
    the callback reply. A reply that contains the key becomes the
    callback reply too, so the key is not sent on.
    """
    try:
        reply = front_desk.reply_to(message, base_url=base_url)
    except Exception:
        reply = answer_reply.callback_reply()
    if not isinstance(reply, str) or not reply.strip():
        return answer_reply.callback_reply()
    key = os.environ.get(answer_reply.KEY_ENV, "").strip()
    if key and len(key) >= _KEY_MIN and key in reply:
        return answer_reply.callback_reply()
    return reply


def _start_sample_site():
    server = serve_sample_site.make_server(serve_sample_site.DEFAULT_HOST, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, f"http://{host}:{port}"


class DemoServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, base_url):
        self.base_url = base_url
        super().__init__(address, DemoHandler)


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        name = _PAGES.get(path)
        if name is None:
            self._send_text(404, "Not found\n")
            return
        file_path = (DEMO / name).resolve()
        try:
            file_path.relative_to(DEMO.resolve())
        except ValueError:
            self._send_text(404, "Not found\n")
            return
        if not file_path.is_file():
            self._send_text(404, "Not found\n")
            return
        content_type = _TYPES.get(file_path.suffix, "application/octet-stream")
        self._send_bytes(200, file_path.read_bytes(), content_type)

    def do_POST(self):
        try:
            self._post()
        except Exception:
            self._send_json(200, {"reply": answer_reply.callback_reply()})

    def _post(self):
        path = unquote(urlsplit(self.path).path)
        if path != "/reply":
            self._send_json(404, {"reply": ""})
            return
        payload = self._read_json()
        if not isinstance(payload, dict):
            self._send_json(400, {"reply": ""})
            return
        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            self._send_json(400, {"reply": ""})
            return
        reply = safe_reply(message, self.server.base_url)
        self._send_json(200, {"reply": reply})

    def _read_json(self):
        raw_length = self.headers.get("Content-Length", "")
        if not raw_length.isdigit():
            return None
        length = int(raw_length)
        if length > _MAX_BODY:
            return None
        data = self.rfile.read(length)
        try:
            return json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _send_json(self, status, payload):
        self._send_bytes(status, _json_bytes(payload), "application/json; charset=utf-8")

    def _send_text(self, status, text):
        self._send_bytes(status, text.encode("utf-8"), "text/plain; charset=utf-8")

    def _send_bytes(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'",
        )
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def make_server(host, port, base_url):
    return DemoServer((host, port), base_url)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if any(arg in {"-h", "--help"} for arg in argv):
        print(USAGE, file=sys.stderr)
        return 2
    if argv:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        host, port = listen_address()
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    site = None
    try:
        site, base = _start_sample_site()
        try:
            server = make_server(host, port, base)
        except OSError as error:
            if error.errno != errno.EADDRINUSE:
                raise
            print(
                f"The demo chat is already running on port {port}. "
                f"Stop it with Ctrl+C, or set {PORT_ENV} to another port.",
                file=sys.stderr,
            )
            return 1
        bound_host, bound_port = server.server_address[:2]
        print(f"Demo chat at http://{bound_host}:{bound_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            return 0
        finally:
            server.server_close()
    finally:
        if site is not None:
            site.shutdown()
            site.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
