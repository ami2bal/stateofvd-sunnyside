#!/usr/bin/env python3
from __future__ import annotations
import functools, http.server, os, sys

class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()
    def do_GET(self):
        if self.path in ("/", "/index.html", ""):
            self.send_response(302)
            self.send_header("Location", "/pixel/")
            self.end_headers()
            return
        return super().do_GET()

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8771
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)
    http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(H, directory=root)).serve_forever()

if __name__ == "__main__":
    main()
