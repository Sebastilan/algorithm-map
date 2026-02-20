#!/usr/bin/env python3
"""Algorithm Map dev server — static files + POST /api/feedback."""

import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, HTTPServer

PORT = 8765


class AlgoMapHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/api/feedback":
            self._handle_feedback()
        else:
            self.send_error(404, "Not Found")

    def _handle_feedback(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except Exception:
            self._json_response(400, {"ok": False, "error": "Invalid JSON"})
            return

        map_path = body.get("mapPath", "")
        markdown = body.get("markdown", "")

        if not map_path or not markdown:
            self._json_response(400, {"ok": False, "error": "mapPath and markdown required"})
            return

        # mapPath is an absolute URL path like "/examples/bpc-phase1.json"
        # Strip leading slash to get relative path
        rel = map_path.lstrip("/")

        # Build feedback file path: same dir, swap extension to .feedback.md
        base, _ = os.path.splitext(rel)
        feedback_rel = base + ".feedback.md"

        # Security: normalize and verify path stays within CWD
        cwd = os.path.abspath(".")
        feedback_abs = os.path.normpath(os.path.join(cwd, feedback_rel))

        if not feedback_abs.startswith(cwd + os.sep) and feedback_abs != cwd:
            self._json_response(403, {"ok": False, "error": "Path escapes working directory"})
            return

        if not feedback_abs.endswith(".feedback.md"):
            self._json_response(403, {"ok": False, "error": "Only .feedback.md files allowed"})
            return

        # Write (overwrite) the feedback file
        os.makedirs(os.path.dirname(feedback_abs), exist_ok=True)
        with open(feedback_abs, "w", encoding="utf-8") as f:
            f.write(markdown)

        self._json_response(200, {"ok": True, "path": feedback_rel})

    def _json_response(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        # Colorize POST requests
        msg = format % args
        if "POST" in msg:
            sys.stderr.write(f"\033[33m{self.address_string()} - {msg}\033[0m\n")
        else:
            super().log_message(format, *args)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
    server = HTTPServer(("", PORT), AlgoMapHandler)
    print(f"Algorithm Map server running on http://localhost:{PORT}")
    print(f"  Renderer: http://localhost:{PORT}/renderer/render.html")
    print(f"  BPC demo: http://localhost:{PORT}/renderer/render.html?src=../examples/bpc-phase1.json")
    print(f"  POST /api/feedback enabled")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
