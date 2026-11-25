"""Serve a demo chat page for one customer message at a time.

Each message goes through the front desk: the urgent reply, your pages,
the answer, and the price check. The page adds no rules of its own.
The sample site starts with this server, so one command is enough.
The page uses the shared demo kit in vendor/demo-kit for the header,
the theme menu, and the fonts. It also serves favicon.svg,
favicon-32.png, apple-touch-icon.png, and favicon.ico.

The Claude key is read later, from the server's own settings, and is
never sent to the browser. DEMO_HOST and DEMO_PORT choose where the
page listens. The default is http://127.0.0.1:8080.

Messages that reach the AI are counted for the Berlin day. CHAT_DAILY_LIMIT
is the whole chat, and CHAT_VISITOR_DAILY_LIMIT is one visitor. At either
cap, the visitor gets a short note to come back tomorrow or book a call,
and the AI is not called. An urgent message still gets the fixed reply.

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
import chat_limit
import front_desk
import serve_sample_site

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"
KIT = ROOT / "vendor" / "demo-kit"
KIT_PREFIX = "/demo-kit/"
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
_ROOT_FILES = {
    "/favicon.svg": KIT / "favicon.svg",
    "/favicon-32.png": KIT / "favicon-32.png",
    "/apple-touch-icon.png": KIT / "apple-touch-icon.png",
    "/favicon.ico": DEMO / "favicon.ico",
}
_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
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


def _content_type(path):
    return _TYPES.get(path.suffix.lower(), "application/octet-stream")


def _inside(path, root):
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return path.is_file()


def static_file(url_path):
    """Return a file this server may send, or None.

    The chat page, the shared kit, and the four icons are included.
    A path that leaves those folders is not.
    """
    if not url_path.startswith("/") or "\\" in url_path or "\x00" in url_path:
        return None
    root_file = _ROOT_FILES.get(url_path)
    if root_file is not None:
        return root_file if _inside(root_file, ROOT) else None
    name = _PAGES.get(url_path)
    if name is not None:
        file_path = DEMO / name
        return file_path if _inside(file_path, DEMO) else None
    if not url_path.startswith(KIT_PREFIX):
        return None
    rel = url_path[len(KIT_PREFIX):]
    if not rel or rel.startswith("/") or any(part == ".." for part in rel.split("/")):
        return None
    file_path = KIT / rel
    return file_path if _inside(file_path, KIT) else None


def _json_bytes(payload):
    text = json.dumps(payload, ensure_ascii=False)
    # Keep the reply as data. A browser that sniffs the body still sees text.
    text = text.replace("<", "\\u003c").replace(">", "\\u003e")
    return text.encode("utf-8")


def safe_reply(message, base_url, visitor=""):
    """Return the front-desk reply, with the key kept off the page.

    A crash, a blank reply, or a reply that contains the key becomes
    the outage reply. The key and the customer message are not logged
    and are not sent on. A fact the pages don't cover stays the
    callback reply. This request counts toward the public chat's daily
    limit when it would reach the AI.
    """
    try:
        with chat_limit.public_chat(visitor):
            reply = front_desk.reply_to(message, base_url=base_url)
    except Exception:
        return answer_reply.outage_reply()
    if not isinstance(reply, str) or not reply.strip():
        return answer_reply.outage_reply()
    key = os.environ.get(answer_reply.KEY_ENV, "").strip()
    if key and len(key) >= _KEY_MIN and key in reply:
        return answer_reply.outage_reply()
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
        file_path = static_file(path)
        if file_path is None:
            self._send_text(404, "Not found\n")
            return
        self._send_bytes(200, file_path.read_bytes(), _content_type(file_path))

    def do_POST(self):
        try:
            self._post()
        except Exception:
            self._send_json(200, {"reply": answer_reply.outage_reply()})

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
        reply = safe_reply(message, self.server.base_url, visitor=self._visitor())
        self._send_json(200, {"reply": reply})

    def _visitor(self):
        connected = self.client_address[0] if self.client_address else ""
        return chat_limit.visitor_key(self.headers.get("X-Forwarded-For", ""), connected)

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
        chat_limit.limits()
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
