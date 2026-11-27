"""Serve the task API over HTTP with the standard library."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from tasks_api.app import App
from tasks_api.store import TaskStore


def handler_for(app: App) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def dispatch(self) -> None:
            url = urlsplit(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                body: Any = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                self.reply(400, {"error": "body must be valid JSON"})
                return
            status, payload = app.handle(
                self.command, url.path, dict(parse_qsl(url.query)), body, dict(self.headers.items())
            )
            self.reply(status, payload)

        def reply(self, status: int, payload: Any) -> None:
            data = b"" if payload is None else json.dumps(payload).encode("utf-8")
            self.send_response(status)
            if data:
                self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = do_PATCH = do_DELETE = dispatch

    return Handler


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the task API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data", type=Path, help="JSON file that keeps the tasks between restarts")
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), handler_for(App(TaskStore(args.data))))
    print(f"Serving on http://{args.host}:{args.port}")
    server.serve_forever()
