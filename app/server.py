"""
TWC offline demo server. Python stdlib only - no pip installs.
Serves the static UI and streams agent events as NDJSON.

Run:  python server.py
Then open http://localhost:8765 (opens automatically).
"""

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import agent

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass  # keep the console clean during the demo

    # ------------------------------------------------------------ helpers

    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    # ------------------------------------------------------------ GET

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/state":
            with open(os.path.join(agent.DATA_DIR, "inbox.json"),
                      "r", encoding="utf-8") as f:
                inbox = json.load(f)
            self._send_json({
                "inbox": inbox,
                "outbox": agent.OUTBOX,
                "quotes": agent.QUOTES,
                "documents": sorted(os.listdir(agent.DOCS_DIR)),
                "context_files": sorted(os.listdir(agent.CONTEXT_DIR)),
                "model": agent.CONFIG["model"],
                "hardware_label": agent.CONFIG.get("hardware_label", ""),
            })
            return

        if path == "/api/document":
            # /api/document?name=x handled via header-free simple parse
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            name = (q.get("name") or [""])[0]
            full = agent._safe_name(name, agent.DOCS_DIR)
            if not full:
                self._send_json({"error": "not found"}, 404)
                return
            with open(full, "r", encoding="utf-8") as f:
                self._send_json({"name": name, "text": f.read()})
            return

        # static files
        if path == "/":
            path = "/index.html"
        full = os.path.normpath(os.path.join(STATIC_DIR, path.lstrip("/")))
        if not full.startswith(STATIC_DIR) or not os.path.isfile(full):
            self.send_error(404)
            return
        ext = os.path.splitext(full)[1].lower()
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ------------------------------------------------------------ POST

    def do_POST(self):
        if self.path == "/api/run":
            try:
                req = self._read_body()
            except (ValueError, json.JSONDecodeError):
                self._send_json({"error": "bad request"}, 400)
                return

            scenario = req.get("scenario", "agent")
            history = req.get("history", [])
            user_message = req.get("message", "")

            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            def write_chunk(data):
                payload = (json.dumps(data) + "\n").encode("utf-8")
                self.wfile.write(hex(len(payload))[2:].encode() + b"\r\n")
                self.wfile.write(payload + b"\r\n")
                self.wfile.flush()

            try:
                for event in agent.run_agent(scenario, history, user_message):
                    write_chunk(event)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                return  # client closed the tab mid-stream
            # terminating chunk
            self.wfile.write(b"0\r\n\r\n")
            return

        if self.path == "/api/reset":
            agent.OUTBOX.clear()
            agent.QUOTES.clear()
            self._send_json({"ok": True})
            return

        self._send_json({"error": "not found"}, 404)


def main():
    port = agent.CONFIG.get("port", 8765)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{port}"
    print("=" * 56)
    print("  Gulf Coast Machining Co. - Agentic AI Demo")
    print(f"  Model:  {agent.CONFIG['model']} (via Ollama, fully local)")
    print(f"  URL:    {url}")
    print("  Ctrl+C to stop")
    print("=" * 56)
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
