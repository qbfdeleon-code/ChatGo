"""SQLite storage for accounts and chat history."""
from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import threading
import time


class Database:
    """Thread-safe wrapper around a single SQLite connection."""

    def __init__(self, path: str = "chatwave.db") -> None:
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    # ------------------------------------------------------------------ setup
    def _create_tables(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username      TEXT PRIMARY KEY COLLATE NOCASE,
                    avatar        TEXT NOT NULL,
                    salt          TEXT,
                    password_hash TEXT,
                    created_at    REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender    TEXT NOT NULL,
                    avatar    TEXT NOT NULL,
                    recipient TEXT,
                    text      TEXT NOT NULL,
                    ts        REAL NOT NULL,
                    edited    INTEGER NOT NULL DEFAULT 0
                );
                """
            )

    # --------------------------------------------------------------- accounts
    @staticmethod
    def _hash(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000
        ).hex()

    def authenticate(self, username: str, password: str, avatar: str) -> tuple[bool, str]:
        """Log in an existing account or register a new one.

        Returns ``(True, canonical_username)`` on success or
        ``(False, reason)`` on failure. The password is optional: an account
        created without one can be used without one.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()

            if row is None:  # new account
                salt = pw_hash = None
                if password:
                    salt = os.urandom(16).hex()
                    pw_hash = self._hash(password, salt)
                with self._conn:
                    self._conn.execute(
                        "INSERT INTO users (username, avatar, salt, password_hash, created_at)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (username, avatar, salt, pw_hash, time.time()),
                    )
                return True, username

            if row["password_hash"]:
                supplied = self._hash(password, row["salt"])
                if not hmac.compare_digest(supplied, row["password_hash"]):
                    return False, "Incorrect password."

            with self._conn:
                self._conn.execute(
                    "UPDATE users SET avatar = ? WHERE username = ?", (avatar, username)
                )
            return True, row["username"]

    def find_user(self, username: str) -> str | None:
        """Return the canonical spelling of ``username`` or ``None``."""
        with self._lock:
            row = self._conn.execute(
                "SELECT username FROM users WHERE username = ?", (username,)
            ).fetchone()
        return row["username"] if row else None

    def all_users(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT username, avatar FROM users ORDER BY username COLLATE NOCASE"
            ).fetchall()
        return [{"username": r["username"], "avatar": r["avatar"]} for r in rows]

    # --------------------------------------------------------------- messages
    @staticmethod
    def _to_dict(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "sender": row["sender"],
            "avatar": row["avatar"],
            "to": row["recipient"],
            "text": row["text"],
            "ts": row["ts"],
            "edited": bool(row["edited"]),
        }

    def add_message(self, sender: str, avatar: str, recipient: str | None, text: str) -> dict:
        ts = time.time()
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO messages (sender, avatar, recipient, text, ts)"
                " VALUES (?, ?, ?, ?, ?)",
                (sender, avatar, recipient, text, ts),
            )
            msg_id = cur.lastrowid
        return {
            "id": msg_id, "sender": sender, "avatar": avatar,
            "to": recipient, "text": text, "ts": ts, "edited": False,
        }

    def edit_message(self, msg_id: int, sender: str, text: str) -> dict | None:
        """Edit a message. Only its author may do so; returns the new row or ``None``."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM messages WHERE id = ?", (msg_id,)
            ).fetchone()
            if row is None or row["sender"] != sender:
                return None
            with self._conn:
                self._conn.execute(
                    "UPDATE messages SET text = ?, edited = 1 WHERE id = ?", (text, msg_id)
                )
            row = self._conn.execute(
                "SELECT * FROM messages WHERE id = ?", (msg_id,)
            ).fetchone()
        return self._to_dict(row)

    def history_for(self, username: str, limit: int = 200) -> list[dict]:
        """Public messages plus every DM the user sent or received (oldest first)."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM (
                    SELECT * FROM messages
                    WHERE recipient IS NULL OR recipient = ? OR sender = ?
                    ORDER BY id DESC LIMIT ?
                ) ORDER BY id ASC
                """,
                (username, username, limit),
            ).fetchall()
        return [self._to_dict(r) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
