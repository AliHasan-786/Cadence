"""Minimal diagnostic endpoint — no BigQuery imports.

If GET /api/test returns 200 but / and /health still 500, the bug is in
api/index.py's BigQuery/auth import chain.
If GET /api/test also 500s, the Vercel-Python config itself is broken.
"""

from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true, "from": "api/test.py", "imports": []}')
