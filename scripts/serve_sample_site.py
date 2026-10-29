"""Serve the Maple Street sample site over HTTP.

Usage: python3 scripts/serve_sample_site.py [--port PORT]
"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import read_pages

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "sample-site"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

pricing_live = False  # Set this to True when the Pricing page is live.

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


class SampleSiteServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if self._pricing_is_down(path):
            message = "Pricing is down for now\n"
            body = message.encode("utf-8")
            self.send_response(503)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        file_path = self._file_for(path)
        if file_path is None:
            self.send_error(404)
            return
        data = file_path.read_bytes()
        content_type = CONTENT_TYPES.get(file_path.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _pricing_is_down(self, path):
        if pricing_live:
            return False
        for page in read_pages.agreed_pages():
            if page["name"] == "Pricing" and path == page["path"]:
                return True
        return False

    def _file_for(self, path):
        if path == "/":
            path = "/index.html"
        relative = path.lstrip("/")
        if not relative:
            return None
        candidate = (SITE / relative).resolve()
        try:
            candidate.relative_to(SITE.resolve())
        except ValueError:
            return None
        if candidate.is_file():
            return candidate
        return None

    def log_message(self, fmt, *args):
        return


def make_server(host=DEFAULT_HOST, port=0):
    return SampleSiteServer((host, port), Handler)


def main(argv=None):
    global pricing_live
    parser = argparse.ArgumentParser(description="Serve the Maple Street sample site.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--pricing-live", action="store_true", help="Serve the Pricing page.")
    args = parser.parse_args(argv)
    if args.pricing_live:
        pricing_live = True
    server = make_server(DEFAULT_HOST, args.port)
    host, port = server.server_address
    print(f"Serving the sample site at http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
