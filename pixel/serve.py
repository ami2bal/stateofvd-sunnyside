#!/usr/bin/env python3
"""Serveur dev no-cache — racine = proto/.

URLs :
  http://127.0.0.1:8771/          → redirect /sunnyside/
  http://127.0.0.1:8771/sunnyside/  (alias propre, runtime actuel)
  http://127.0.0.1:8771/state-of-vd-pixel/  (alias historique)
  http://127.0.0.1:8771/state-of-vd/        (jeu vectoriel main)
"""
from __future__ import annotations

import functools
import http.server
import os
import sys


PIXEL_DIRNAME = "state-of-vd-pixel"  # dossier workspace (historique)
ALIASES = {
    "/sunnyside": PIXEL_DIRNAME,
    "/sunnyside/": PIXEL_DIRNAME,
    "/state-of-vd-sunnyside": PIXEL_DIRNAME,
    "/state-of-vd-sunnyside/": PIXEL_DIRNAME,
}


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        # Alias URL → dossier physique
        for prefix, target in ALIASES.items():
            if path == prefix or path.startswith(prefix.rstrip("/") + "/"):
                rest = path[len(prefix.rstrip("/")) :]
                if not rest.startswith("/"):
                    rest = "/" + rest if rest else "/"
                path = f"/{target}{rest}"
                break
        return super().translate_path(path)

    def do_GET(self):
        if self.path in ("/", "/index.html", ""):
            self.send_response(302)
            self.send_header("Location", "/sunnyside/")
            self.end_headers()
            return
        # /sunnyside sans slash final → avec slash (évite boucle sur /sunnyside/)
        bare = self.path.split("?", 1)[0]
        if bare in ("/sunnyside", "/state-of-vd-sunnyside"):
            self.send_response(302)
            self.send_header("Location", bare + "/")
            self.end_headers()
            return
        return super().do_GET()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8771
    pixel_dir = os.path.dirname(os.path.abspath(__file__))
    proto_root = os.path.dirname(pixel_dir)
    os.chdir(proto_root)
    handler = functools.partial(NoCacheHandler, directory=proto_root)
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Proto root → http://127.0.0.1:{port}/")
        print(f"  Sunnyside → http://127.0.0.1:{port}/sunnyside/")
        print(f"  (alias)   → http://127.0.0.1:{port}/state-of-vd-pixel/")
        print(f"  Main      → http://127.0.0.1:{port}/state-of-vd/")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
