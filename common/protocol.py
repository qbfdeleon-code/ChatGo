"""Shared constants and helpers for the ChatGo wire protocol.

Every packet is a single JSON object terminated by a newline ("\\n").
Newline-delimited JSON fixes the classic TCP problem where one ``recv()``
can contain half a message or two messages glued together.

Client -> Server
    {"type": "register", "username", "password", "avatar", "picture"}   # create account
    {"type": "login",    "username", "password"}
    {"type": "message",  "to": str | null, "text": str}     # null = group chat
    {"type": "edit",     "id": int, "text": str}

Server -> Client
    {"type": "login_ok", "username", "avatar", "picture", "users": [...], "history": [...]}
    {"type": "login_error", "reason": str}
    {"type": "message",  "message": {id, sender, avatar, to, text, ts, edited}}
    {"type": "edited",   "id": int, "text": str, "to": str | null}
    {"type": "presence", "user": {username, avatar, picture, online}}
    {"type": "system",   "text": str, "ts": float}
    {"type": "error",    "reason": str}

``picture`` is an optional base64-encoded 96x96 image (JPEG/PNG) or null.
"""
from __future__ import annotations

import json
from datetime import datetime

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5555

ROOM_TITLE = "Group 2 Chat"
GENERAL = "#general"          # conversation key of the public room

MAX_MESSAGE_LENGTH = 300      # characters per chat message
MIN_PASSWORD_LENGTH = 4
MAX_PASSWORD_LENGTH = 64
USERNAME_PATTERN = r"^[A-Za-z0-9_.-]{2,20}$"

PICTURE_SIZE = 96             # profile pictures are scaled to 96x96 by the client
MAX_PICTURE_B64 = 60_000      # server-side size cap for the encoded picture

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
