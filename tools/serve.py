#!/usr/bin/env python3
"""Tiny static preview server: serves release/ and maps "/" to the atlas file.
The atlas itself needs NO server (open the HTML file directly); this is only
for previewing over HTTP.  Usage: python3 tools/serve.py [port]"""
import http.server, os, sys
ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "release")
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def do_GET(self):
        if self.path in ("/", "/index.html") or self.path.startswith("/?"):
            self.path = "/islamic-history-atlas.html"
        return super().do_GET()
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache"); super().end_headers()
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
http.server.ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
