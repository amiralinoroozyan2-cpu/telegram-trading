from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Callable


class _HealthHandler(BaseHTTPRequestHandler):
    status_provider: Callable[[], dict[str, str]] = lambda: {"status": "ok"}

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        payload = json.dumps(type(self).status_provider(), ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


class HealthServer:
    def __init__(self, host: str, port: int) -> None:
        self.server = ThreadingHTTPServer((host, port), _HealthHandler)
        self.thread = Thread(target=self.server.serve_forever, name="health-server", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
