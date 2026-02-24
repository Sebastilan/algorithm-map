#!/usr/bin/env python3
"""Algorithm Map dev server — static files + POST /api/feedback + GET /api/export."""

import json
import os
import sys
import urllib.request
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer

MULTI_CC_URL = "http://localhost:3002"
PORT = 8765


def _push_to_terminal(terminal_id, title, markdown):
    """POST feedback to a multi-cc terminal (non-blocking, called in thread)."""
    msg = f"[算法地图批注] **{title}**\n\n{markdown}"
    body = json.dumps({"text": msg}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{MULTI_CC_URL}/api/terminals/{terminal_id}/message",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=3)


class AlgoMapHandler(SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path.startswith("/api/export"):
            self._handle_export()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/feedback":
            self._handle_feedback()
        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ------------------------------------------------------------------
    # GET /api/export?src=_external/xxx.json&terminal=term_xxx
    # ------------------------------------------------------------------
    def _handle_export(self):
        from urllib.parse import urlparse, parse_qs, unquote
        qs = parse_qs(urlparse(self.path).query)
        src = unquote(qs.get("src", [""])[0]).lstrip("/") or "_external/algorithm-map.json"
        terminal_id = unquote(qs.get("terminal", [""])[0])

        cwd = os.path.abspath(".")
        json_abs = os.path.normpath(os.path.join(cwd, src))
        if not json_abs.startswith(cwd):
            self._json_response(403, {"error": "path escapes working directory"}); return
        try:
            with open(json_abs, encoding="utf-8") as f:
                map_json = f.read()
        except FileNotFoundError:
            self._json_response(404, {"error": f"not found: {src}"}); return

        map_path = "/" + src.replace("\\", "/")
        render_path = os.path.join(cwd, "renderer", "render.html")
        with open(render_path, encoding="utf-8") as f:
            html = f.read()

        inject = (
            f'\n<script>\n'
            f'window.__MAP_DATA__ = {map_json};\n'
            f'window.__MAP_PATH__ = {json.dumps(map_path)};\n'
            f'window.__TERMINAL_ID__ = {json.dumps(terminal_id or None)};\n'
            f'window.__API_ENDPOINTS__ = [\n'
            f'  "http://localhost:3002/api/map-feedback",\n'
            f'  "http://120.26.28.49:10001/api/map-feedback"\n'
            f'];\n'
            f'</script>\n'
        )
        html = html.replace("</head>", inject + "</head>", 1)
        body = html.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="algorithm-map.html"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    # ------------------------------------------------------------------
    # POST /api/feedback
    # Body: { mapPath, markdown, title?, terminalId? }
    # ------------------------------------------------------------------
    def _handle_feedback(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except Exception:
            self._json_response(400, {"ok": False, "error": "Invalid JSON"}); return

        map_path    = body.get("mapPath", "")
        markdown    = body.get("markdown", "")
        title       = body.get("title", "Algorithm Map")
        terminal_id = body.get("terminalId") or None

        if not map_path or not markdown:
            self._json_response(400, {"ok": False, "error": "mapPath and markdown required"}); return

        rel = map_path.lstrip("/")
        base, _ = os.path.splitext(rel)
        feedback_rel = base + ".feedback.md"

        cwd = os.path.abspath(".")
        feedback_abs = os.path.normpath(os.path.join(cwd, feedback_rel))
        if not feedback_abs.startswith(cwd + os.sep):
            self._json_response(403, {"ok": False, "error": "Path escapes working directory"}); return
        if not feedback_abs.endswith(".feedback.md"):
            self._json_response(403, {"ok": False, "error": "Only .feedback.md files allowed"}); return

        os.makedirs(os.path.dirname(feedback_abs), exist_ok=True)
        with open(feedback_abs, "w", encoding="utf-8") as f:
            f.write(markdown)

        # Push to terminal in background (non-blocking)
        def _push_async():
            if not terminal_id:
                sys.stderr.write("\033[33m[feedback] written (no terminal_id)\033[0m\n")
                return
            try:
                _push_to_terminal(terminal_id, title, markdown)
                sys.stderr.write(f"\033[32m[push] → {terminal_id}\033[0m\n")
            except Exception as e:
                sys.stderr.write(f"\033[31m[push] failed: {e}\033[0m\n")

        threading.Thread(target=_push_async, daemon=True).start()
        self._json_response(200, {"ok": True, "path": feedback_rel})

    def _json_response(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        msg = format % args
        if "POST" in msg:
            sys.stderr.write(f"\033[33m{self.address_string()} - {msg}\033[0m\n")
        else:
            super().log_message(format, *args)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
    server = HTTPServer(("", PORT), AlgoMapHandler)
    print(f"Algorithm Map server  http://localhost:{PORT}")
    print(f"  Renderer: http://localhost:{PORT}/renderer/render.html")
    print(f"  POST /api/feedback  GET /api/export")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
