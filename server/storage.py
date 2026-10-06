"""Persistence layer for the ChatWave server (accounts + message history).

Data is stored as small JSON files so the project has no database dependency.
Passwords are never stored in plain text: each account keeps a random salt and a
PBKDF2-SHA256 hash. Pass ``data_dir=None`` for a purely in-memory store (tests).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
from pathlib import Path

MAX_STORED_MESSAGES = 500
PBKDF2_ROUNDS = 120_000


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS).hex()


class Storage:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        self._lock = threading.RLock()
        self._dir = Path(data_dir) if data_dir else None
        self._accounts: dict[str, dict] = {}   # lower-case username -> record
        self._messages: list[dict] = []
        if self._dir:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._accounts = self._load("accounts.json", {})
            self._messages = self._load("history.json", [])

    # ------------------------------------------------------------------ accounts
    def authenticate(self, username: str, password: str, avatar: str) -> tuple[bool, str]:
        """Log in an existing account or register a new one.

        Passwords are optional: an account created without one can be used
        by anyone, an account created with one always requires it.
        """
        key = username.lower()
        with self._lock:
            account = self._accounts.get(key)
            if account is None:
                record = {"username": username, "avatar": avatar, "salt": None, "hash": None}
                if password:
                    salt = secrets.token_bytes(16)
                    record["salt"] = salt.hex()
                    record["hash"] = _hash_password(password, salt)
                self._accounts[key] = record
                self._save()
                return True, ""
            if account["hash"]:
                expected = account["hash"]
                given = _hash_password(password, bytes.fromhex(account["salt"]))
                if not hmac.compare_digest(expected, given):
                    return False, "Incorrect password for this username."
            if account["avatar"] != avatar:
                account["avatar"] = avatar
                self._save()
            return True, ""

    def find_account(self, username: str) -> dict | None:
        with self._lock:
            account = self._accounts.get(str(username).lower())
            return dict(account) if account else None

    def list_accounts(self) -> list[dict]:
        with self._lock:
            return [{"username": a["username"], "avatar": a["avatar"]}
                    for a in sorted(self._accounts.values(), key=lambda a: a["username"].lower())]

    # ------------------------------------------------------------------ messages
    def add_message(self, message: dict) -> None:
        with self._lock:
            self._messages.append(message)
            del self._messages[:-MAX_STORED_MESSAGES]
            self._save()

    def edit_message(self, message_id: str, editor: str, text: str) -> dict | None:
        """Edit a message. Returns the updated message, or None if not allowed."""
        with self._lock:
            for message in self._messages:
                if message["id"] == message_id:
                    if message["sender"].lower() != editor.lower():
                        return None
                    message["text"] = text
                    message["edited"] = True
                    self._save()
                    return dict(message)
            return None

    def history_for(self, username: str) -> list[dict]:
        """Group messages plus private messages sent to / by this user."""
        key = username.lower()
        with self._lock:
            return [dict(m) for m in self._messages
                    if not m["to"] or m["to"].lower() == key or m["sender"].lower() == key]

    # --------------------------------------------------------------------- disk
    def _load(self, name: str, default):
        path = self._dir / name
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default

    def _save(self) -> None:
        if not self._dir:
            return
        for name, data in (("accounts.json", self._accounts), ("history.json", self._messages)):
            tmp = self._dir / (name + ".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self._dir / name)
