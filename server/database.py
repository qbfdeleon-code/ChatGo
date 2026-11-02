"""SQLite storage for accounts and chat history."""
from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import threading
import time

BAD_LOGIN = "Incorrect username or password. New here? Choose Sign Up."


class Database:
    """Thread-safe wrapper around a single SQLite connection."""

    def __init__(self, path: str = "chatgo.db") -> None:
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    # ------------------------------------------------------------------ setup
    def _create_tables(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username      TEXT PRIMARY KEY COLLATE NOCASE,
                    avatar        TEXT NOT NULL,
                    salt          TEXT,
                    password_hash TEXT,
                    picture       TEXT,
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
            columns = {r["name"] for r in self._conn.execute("PRAGMA table_info(users)")}
            if "picture" not in columns:             # database from an older version
                with self._conn:
                    self._conn.execute("ALTER TABLE users ADD COLUMN picture TEXT")

    # --------------------------------------------------------------- accounts
    @staticmethod
    def _hash(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000
        ).hex()

    def register(self, username: str, password: str, avatar: str,
                 picture: str | None) -> tuple[bool, str]:
        """Create an account. Returns ``(True, username)`` or ``(False, reason)``."""
        with self._lock:
            if self.find_user(username) is not None:
                return False, "That username is already taken."
            salt = os.urandom(16).hex()
            with self._conn:
                self._conn.execute(
                    "INSERT INTO users (username, avatar, salt, password_hash, picture, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (username, avatar, salt, self._hash(password, salt), picture, time.time()),
                )
        return True, username

    def authenticate(self, username: str, password: str) -> tuple[bool, str]:
        """Check a login. Returns ``(True, canonical_username)`` or ``(False, reason)``."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
        if row is None or not row["password_hash"]:
            return False, BAD_LOGIN
        supplied = self._hash(password, row["salt"])
        if not hmac.compare_digest(supplied, row["password_hash"]):
            return False, BAD_LOGIN
        return True, row["username"]

    def find_user(self, username: str) -> str | None:
        """Return the canonical spelling of ``username`` or ``None``."""
        with self._lock:
            row = self._conn.execute(
                "SELECT username FROM users WHERE username = ?", (username,)
            ).fetchone()
        return row["username"] if row else None

    def get_user(self, username: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT username, avatar, picture FROM users WHERE username = ?", (username,)
            ).fetchone()
        return dict(row) if row else None

    def all_users(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT username, avatar, picture FROM users ORDER BY username COLLATE NOCASE"
            ).fetchall()
        return [dict(r) for r in rows]

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
