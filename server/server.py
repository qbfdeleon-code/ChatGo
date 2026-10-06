"""ChatWave TCP server.

One thread per connected client. Packets are newline-delimited JSON (see
``common/protocol.py``). Accounts and history are stored in SQLite.
"""
from __future__ import annotations

import logging
import re
import socket
import threading
import time

from common import protocol
from server.database import Database

log = logging.getLogger("chatwave.server")


class Session:
    """One connected client."""

    def __init__(self, conn: socket.socket, addr: tuple) -> None:
        self.conn = conn
        self.addr = addr
        self.username: str | None = None
        self.avatar: str = "👤"
        self._send_lock = threading.Lock()

    def send(self, packet: dict) -> bool:
        try:
            with self._send_lock:
                self.conn.sendall(protocol.encode(packet))
            return True
        except OSError:
            return False

    def close(self) -> None:
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.conn.close()
        except OSError:
            pass


class ChatServer:
    def __init__(self, host: str = "0.0.0.0", port: int = protocol.DEFAULT_PORT,
                 db_path: str = "chatwave.db") -> None:
        self.host = host
        self.port = port
        self.db = Database(db_path)
        self._sock: socket.socket | None = None
        self._running = False
        self._lock = threading.Lock()
        self.sessions: dict[str, Session] = {}   # logged-in users, by username

    # ------------------------------------------------------------- lifecycle
    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen()
        self._sock.settimeout(0.5)               # lets stop() break the accept loop
        self.port = self._sock.getsockname()[1]  # resolves port 0 in tests
        self._running = True

    def serve_forever(self) -> None:
        if self._sock is None:
            self.start()
        log.info("Listening on %s:%s", self.host, self.port)
        while self._running:
            try:
                conn, addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            conn.settimeout(None)
            log.info("Connection from %s:%s", *addr[:2])
            threading.Thread(
                target=self._handle_client, args=(Session(conn, addr),), daemon=True
            ).start()

    def start_in_background(self) -> threading.Thread:
        self.start()
        thread = threading.Thread(target=self.serve_forever, daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._running = False
        with self._lock:
            sessions = list(self.sessions.values())
        for session in sessions:
            session.close()
        if self._sock:
            self._sock.close()

    # ------------------------------------------------------- per-client loop
    def _handle_client(self, session: Session) -> None:
        try:
            reader = session.conn.makefile("r", encoding="utf-8", newline="\n")
            for line in reader:
                line = line.strip()
                if not line:
                    continue
                try:
                    packet = protocol.decode(line)
                except ValueError:
                    continue
                self._dispatch(session, packet)
        except (OSError, UnicodeDecodeError):
            pass
        finally:
            self._disconnect(session)

    def _dispatch(self, session: Session, packet: dict) -> None:
        kind = packet.get("type")
        if session.username is None:
            if kind == "login":
                self._handle_login(session, packet)
            return
        if kind == "message":
            self._handle_message(session, packet)
        elif kind == "edit":
            self._handle_edit(session, packet)

    # --------------------------------------------------------------- handlers
    def _handle_login(self, session: Session, packet: dict) -> None:
        username = str(packet.get("username", "")).strip()
        password = str(packet.get("password", ""))
        avatar = str(packet.get("avatar") or "👤")[:8]

        if not re.match(protocol.USERNAME_PATTERN, username):
            session.send({"type": "login_error",
                          "reason": "Username must be 2-20 characters (letters, numbers, _ . -)."})
            return

        ok, result = self.db.authenticate(username, password, avatar)
        if not ok:
            session.send({"type": "login_error", "reason": result})
            return

        canonical = result
        with self._lock:
            if canonical in self.sessions:
                session.send({"type": "login_error",
                              "reason": "That account is already logged in."})
                return
            session.username = canonical
            session.avatar = avatar
            self.sessions[canonical] = session

        session.send({
            "type": "login_ok",
            "username": canonical,
            "avatar": avatar,
            "users": self._user_list(),
            "history": self.db.history_for(canonical),
        })
        log.info("%s logged in", canonical)
        self._broadcast({"type": "presence",
                         "user": {"username": canonical, "avatar": avatar, "online": True}},
                        skip=session)
        self._broadcast({"type": "system", "ts": time.time(),
                         "text": f"🟢 {avatar} {canonical} joined the chat!"}, skip=session)

    def _handle_message(self, session: Session, packet: dict) -> None:
        text = str(packet.get("text", "")).strip()[: protocol.MAX_MESSAGE_LENGTH]
        if not text:
            return
        recipient = None
        if packet.get("to"):
            recipient = self.db.find_user(str(packet["to"]))
            if recipient is None:
                session.send({"type": "error", "reason": "That user does not exist."})
                return

        msg = self.db.add_message(session.username, session.avatar, recipient, text)
        self._deliver({"type": "message", "message": msg}, session.username, recipient)

    def _handle_edit(self, session: Session, packet: dict) -> None:
        text = str(packet.get("text", "")).strip()[: protocol.MAX_MESSAGE_LENGTH]
        try:
            msg_id = int(packet.get("id"))
        except (TypeError, ValueError):
            return
        if not text:
            return
        msg = self.db.edit_message(msg_id, session.username, text)
        if msg is None:
            session.send({"type": "error", "reason": "You can only edit your own messages."})
            return
        self._deliver({"type": "edited", "id": msg["id"], "text": msg["text"], "to": msg["to"]},
                      session.username, msg["to"])

    def _disconnect(self, session: Session) -> None:
        name = session.username
        if name:
            with self._lock:
                if self.sessions.get(name) is session:
                    del self.sessions[name]
                else:
                    name = None
        session.close()
        if name:
            log.info("%s disconnected", name)
            self._broadcast({"type": "presence",
                             "user": {"username": name, "avatar": session.avatar, "online": False}})
            self._broadcast({"type": "system", "ts": time.time(),
                             "text": f"🔴 {session.avatar} {name} left the chat."})

    # ---------------------------------------------------------------- helpers
    def _user_list(self) -> list[dict]:
        with self._lock:
            online = set(self.sessions)
        return [{**u, "online": u["username"] in online} for u in self.db.all_users()]

    def _broadcast(self, packet: dict, skip: Session | None = None) -> None:
        with self._lock:
            targets = [s for s in self.sessions.values() if s is not skip]
        for s in targets:
            s.send(packet)

    def _deliver(self, packet: dict, sender: str, recipient: str | None) -> None:
        """Public message -> everybody. Direct message -> sender and recipient only."""
        if recipient is None:
            self._broadcast(packet)
            return
        with self._lock:
            targets = {self.sessions.get(sender), self.sessions.get(recipient)}
        for s in targets:
            if s is not None:
                s.send(packet)
