#!/usr/bin/env python3
"""Serve Quant Desk locally with a read-only Alpaca paper API proxy.

Credentials remain in this server process and are never sent to browser code.
Only three GET endpoints are exposed; order placement is intentionally absent.
"""

import argparse
import json
import os
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ALPACA_BASE = "https://paper-api.alpaca.markets"
ROUTES = {
    "/api/alpaca/account": "/v2/account",
    "/api/alpaca/positions": "/v2/positions",
    "/api/alpaca/orders": "/v2/orders?status=all&limit=15&direction=desc",
}


class Handler(SimpleHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if not path.startswith("/api/alpaca/"):
            return super().do_GET()

        upstream = ROUTES.get(path)
        if not upstream:
            return self.send_json(404, {"error": "unknown read-only endpoint"})

        key = os.environ.get("ALPACA_API_KEY", "")
        secret = os.environ.get("ALPACA_SECRET_KEY", "")
        if not key or not secret:
            return self.send_json(
                503,
                {"error": "paper credentials are not configured in the local server"},
            )

        request = urllib.request.Request(
            ALPACA_BASE + upstream,
            headers={
                "APCA-API-KEY-ID": key,
                "APCA-API-SECRET-KEY": secret,
                "Accept": "application/json",
                "User-Agent": "Quant-Desk local monitor",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = response.read()
                self.send_response(response.status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        except urllib.error.HTTPError as exc:
            self.send_json(exc.code, {"error": "Alpaca paper API rejected the request"})
        except Exception as exc:
            self.send_json(502, {"error": f"Alpaca paper API unavailable: {exc}"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Quant Desk: http://127.0.0.1:{args.port}/")
    print("Read-only Alpaca proxy enabled for account, positions, and orders.")
    server.serve_forever()


if __name__ == "__main__":
    main()
