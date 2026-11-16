"""Stdio MCP server for the field record. No secrets and no network of its own.

Weather, when a tool call asks for it, is the only network call, and it
goes through the record. Logs stay off stdout.
"""

from __future__ import annotations

import json
import sys

from farm_ontology.record import (
    add_note,
    list_notes,
    read_playbook,
    read_sop,
    record_observation,
    status,
)

PROTOCOL = "2024-11-05"
SERVER = {"name": "farm-ontology-field", "version": "0.1.0"}

TOOLS = [
    {
        "name": "show_status",
        "description": "Show the field record status. Class C stays closed and financial use stays false.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "read_playbook",
        "description": "Read the soybean harvest playbook.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "read_sop",
        "description": "Read the field SOP.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "record_field_observation",
        "description": "Write one soybean field observation. GPS accuracy stays unknown unless metres are given. The weather grid is 0.05 degrees and is not shrunk to the plant.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "note": {"type": "string"},
                "metres": {"type": "number"},
                "sample_id": {"type": "string"},
                "photo": {"type": "string"},
                "harvest_unit": {"type": "string"},
                "moisture": {"type": "number"},
                "dry_run": {"type": "boolean"},
                "attach_weather": {"type": "boolean"},
            },
            "required": ["latitude", "longitude"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_notes",
        "description": "List recorded field observations and verification or feedback notes.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "add_note",
        "description": "Add a verification note or a feedback note to the field record.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["verification", "feedback"]},
                "text": {"type": "string"},
                "observation_file": {"type": "string"},
            },
            "required": ["kind", "text"],
            "additionalProperties": False,
        },
    },
]


def _text(payload) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}], "isError": False}


def _fail(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def call_tool(name: str, arguments: dict | None) -> dict:
    args = arguments or {}
    try:
        if name == "show_status":
            return _text(status())
        if name == "read_playbook":
            return _text({"playbook": read_playbook()})
        if name == "read_sop":
            return _text({"sop": read_sop()})
        if name == "record_field_observation":
            saved = record_observation(
                latitude=args.get("latitude"),
                longitude=args.get("longitude"),
                note=str(args.get("note") or ""),
                metres=args.get("metres"),
                sample_id=args.get("sample_id"),
                photo_path=args.get("photo"),
                harvest_unit=args.get("harvest_unit"),
                moisture=args.get("moisture"),
                dry_run=bool(args.get("dry_run")),
                attach_weather=bool(args.get("attach_weather")),
            )
            return _text(saved)
        if name == "list_notes":
            return _text(list_notes())
        if name == "add_note":
            saved = add_note(
                kind=str(args.get("kind") or ""),
                text=str(args.get("text") or ""),
                observation_file=args.get("observation_file"),
            )
            return _text(saved)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return _fail(str(error))
    return _fail(f"unknown tool {name}")


def handle(message: dict) -> dict | None:
    method = message.get("method")
    msg_id = message.get("id")
    if method and method.startswith("notifications/"):
        return None
    if msg_id is None:
        return None
    if method == "initialize":
        version = (message.get("params") or {}).get("protocolVersion") or PROTOCOL
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER,
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = message.get("params") or {}
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": call_tool(str(params.get("name") or ""), params.get("arguments") or {}),
        }
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"method not found: {method}"},
    }


def read_message(stream) -> dict | None:
    line = stream.readline()
    if not line:
        return None
    headers = {}
    while line not in (b"\r\n", b"\n"):
        if b":" not in line:
            return None
        key, value = line.decode("ascii", "replace").split(":", 1)
        headers[key.strip().lower()] = value.strip()
        line = stream.readline()
        if not line:
            return None
    length = int(headers.get("content-length", "0"))
    if length <= 0 or length > 1_000_000:
        return None
    body = stream.read(length)
    return json.loads(body.decode("utf-8"))


def write_message(stream, message: dict) -> None:
    payload = json.dumps(message).encode("utf-8")
    stream.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii"))
    stream.write(payload)
    stream.flush()


def main() -> int:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        message = read_message(stdin)
        if message is None:
            return 0
        reply = handle(message)
        if reply is not None:
            write_message(stdout, reply)


if __name__ == "__main__":
    raise SystemExit(main())
