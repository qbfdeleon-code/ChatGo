"""Shared constants and helpers for the ChatWave wire protocol.

Every packet is a single JSON object terminated by a newline ("\\n").
Newline-delimited JSON fixes the classic TCP problem where one ``recv()``
can contain half a message or two messages glued together.

Client -> Server
    {"type": "login",   "username": str, "password": str, "avatar": str}
    {"type": "message", "to": str | null, "text": str}      # null = General chat
    {"type": "edit",    "id": int, "text": str}

Server -> Client
    {"type": "login_ok", "username", "avatar", "users": [...], "history": [...]}
    {"type": "login_error", "reason": str}
    {"type": "message",  "message": {id, sender, avatar, to, text, ts, edited}}
    {"type": "edited",   "id": int, "text": str, "to": str | null}
    {"type": "presence", "user": {username, avatar, online}}
    {"type": "system",   "text": str, "ts": float}
    {"type": "error",    "reason": str}
"""
from __future__ import annotations

import json
from datetime import datetime

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5555

GENERAL = "#general"          # conversation key of the public room
MAX_MESSAGE_LENGTH = 2000
USERNAME_PATTERN = r"^[A-Za-z0-9_.-]{2,20}$"

AVATARS = ["👤", "😀", "😎", "😂", "🥰", "😈", "🤖", "🐱", "🐶", "🐼"]


def encode(packet: dict) -> bytes:
    """Serialise a packet to bytes ready for ``socket.sendall``."""
    return (json.dumps(packet, ensure_ascii=False) + "\n").encode("utf-8")


def decode(line: str) -> dict:
    """Parse one received line. Raises ``ValueError`` on malformed input."""
    packet = json.loads(line)
    if not isinstance(packet, dict):
        raise ValueError("packet must be a JSON object")
    return packet


def format_timestamp(ts: float) -> str:
    """Format like the project spec: ``September 12, 2026 • 08:45 AM``."""
    return datetime.fromtimestamp(ts).strftime("%B %d, %Y • %I:%M %p")
