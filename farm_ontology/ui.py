"""One local page for the soybean field record.

Bind is loopback only. Recording does not call the network. Weather is
optional and is requested only when the form asks for it.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from farm_ontology.record import (
    add_note,
    list_notes,
    read_playbook,
    read_sop,
    record_observation,
    status,
)

PAGE = (__import__("pathlib").Path(__file__).resolve().parent / "ui_page.html").read_bytes()


class FieldHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 65_536:
            raise ValueError("request body is missing or too large")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
            return
        if path == "/api/status":
            self._json(200, status())
            return
        if path == "/api/playbook":
            self._json(200, {"playbook": read_playbook()})
            return
        if path == "/api/sop":
            self._json(200, {"sop": read_sop()})
            return
        if path == "/api/notes":
            self._json(200, list_notes())
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/observations":
                saved = record_observation(
                    latitude=payload.get("latitude"),
                    longitude=payload.get("longitude"),
                    note=str(payload.get("note") or ""),
                    metres=payload.get("metres"),
                    sample_id=payload.get("sample_id") or None,
                    photo_path=payload.get("photo") or None,
                    harvest_unit=payload.get("harvest_unit") or None,
                    moisture=payload.get("moisture"),
                    dry_run=bool(payload.get("dry_run")),
                    attach_weather=bool(payload.get("attach_weather")),
                )
                self._json(200, saved)
                return
            if path == "/api/notes":
                saved = add_note(
                    kind=str(payload.get("kind") or ""),
                    text=str(payload.get("text") or ""),
                    observation_file=payload.get("observation_file") or None,
                )
                self._json(200, saved)
                return
            self._json(404, {"error": "not found"})
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            self._json(400, {"error": str(error)})


def serve(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), FieldHandler)
    return server


def main() -> int:
    server = serve()
    host, port = server.server_address
    print(f"http://{host}:{port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
