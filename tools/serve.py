#!/usr/bin/env python3
"""
Lokaler Vorschau-Server fuer den Kurs.

    python tools/serve.py [port]

Danach die ausgegebene URL im Browser oeffnen. LiaScript rendert
clientseitig und holt die Datei direkt von hier.

Wichtig ist der CORS-Header: ohne ihn faellt LiaScript auf den oeffentlichen
Proxy api.allorigins.win zurueck -- und der kann localhost natuerlich nicht
erreichen, was zu einer irrefuehrenden Fehlermeldung fuehrt.
"""
import functools
import http.server
import socketserver
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8901
    if not (ROOT / "README.md").exists():
        sys.exit("README.md fehlt -- erst `python build.py` ausfuehren")

    local = f"http://localhost:{port}/README.md"
    print(f"Kursverzeichnis : {ROOT}")
    print(f"Vorschau        : https://liascript.github.io/course/?{local}")
    print(f"Rohdatei        : {local}")
    print("\nBeenden mit Strg-C\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(
            ("127.0.0.1", port),
            functools.partial(Handler, directory=str(ROOT))) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nbeendet")


if __name__ == "__main__":
    main()
