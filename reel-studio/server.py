#!/usr/bin/env python3
"""Reel Studio local server.

Serves index.html at http://localhost:8787 and forwards /v1/... requests to
api.openai.com, so the browser never has to call OpenAI directly (which some
browsers block for pages opened from a file).

Run:  python3 server.py
"""
import http.server
import os
import ssl
import sys
import urllib.error
import urllib.request
import webbrowser

PORT = 8787
OPENAI = "https://api.openai.com"
HERE = os.path.dirname(os.path.abspath(__file__))
FORWARD_HEADERS = ("authorization", "content-type")


def ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


CTX = ssl_context()


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/v1/"):
            return self.proxy()
        if self.path in ("/", "/index.html"):
            return self.serve_page()
        self.send_error(404)

    def do_POST(self):
        self.proxy()

    def do_DELETE(self):
        self.proxy()

    def serve_page(self):
        try:
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                body = f.read()
        except FileNotFoundError:
            self.send_error(404, "index.html must be in the same folder as server.py")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def proxy(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() in FORWARD_HEADERS}
        req = urllib.request.Request(OPENAI + self.path, data=body, headers=headers, method=self.command)
        try:
            resp = urllib.request.urlopen(req, context=CTX, timeout=300)
        except urllib.error.HTTPError as e:
            resp = e
        except Exception as e:
            print(f"  ! Could not reach OpenAI: {e}", file=sys.stderr)
            if isinstance(getattr(e, "reason", None), ssl.SSLError):
                print("    Fix: run 'Install Certificates.command' in your Python folder "
                      "(Applications > Python 3.x), then restart this server.", file=sys.stderr)
            msg = f'{{"error": {{"message": "The Reel Studio server could not reach OpenAI: {type(e).__name__}. See the Terminal window for details."}}}}'
            data = msg.encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        with resp:
            data = resp.read()
            self.send_response(resp.status)
            self.send_header("Content-Type", resp.headers.get("Content-Type", "application/octet-stream"))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    def log_message(self, fmt, *args):
        if self.path.startswith("/v1/") and self.command != "GET":
            print(f"  {self.command} {self.path.split('?')[0]}")


def main():
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        print(f"Port {PORT} is busy. Reel Studio may already be running: open http://localhost:{PORT}")
        return
    url = f"http://localhost:{PORT}"
    print(f"Reel Studio is running at {url}")
    print("Keep this window open while you use it. Press Ctrl+C to stop.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
