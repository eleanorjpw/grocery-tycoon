#!/usr/bin/env python3
"""
Local preview server for the WASM build in ./web.

It sends the cross-origin-isolation headers pygbag needs (a plain
`python -m http.server` does NOT, so the game won't start without this).

Usage:  python3 serve_web.py   then open http://localhost:8000
"""
import http.server
import os
import socketserver

PORT = 8000
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DIRECTORY, **k)

    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "credentialless")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving ./web at http://localhost:{PORT}  (Ctrl+C to stop)")
        httpd.serve_forever()
