"""ChatWave TCP chat server.

One thread per connected client. All shared state (the table of online sessions)
is protected by a lock; message history and accounts live in ``Storage``.
"""
from __future__ import annotations

import logging
import socket
import threading
import time
import uuid
from collections import deque

from common.protocol import (
    AVATARS, DEFAULT_HOST, DEFAULT_PORT, EDIT, EDITED, ERROR, LOGIN, LOGIN_ERROR, LOGIN_OK,
    MAX_MESSAGE_LENGTH, MESSAGE, PUBLIC_CHAT, SYSTEM, USERNAME_PATTERN, USERNAME_RULES, USERS,
    PacketReader, ProtocolError, encode_packet,
)
from server.storage import Storage

log = logging.getLogger("chatwave.server")
AUTH_TIMEOUT = 15  # seconds a new connection has to send its login packet


class Session:
    """One connected client socket."""

    def __init__(self, sock: socket.socket, address) -> None:
        self.sock = sock
        self.address = address
        self.username: str | None = None
        self.avatar: str = AVATARS[0]
        self._reader = PacketReader()
        self._pending: deque[dict] = deque()
        self._send_lock = threading.Lock()

    def next_packet(self) -> dict | None:
        """Block until a full packet arrives; None means the client disconnected."""
        while not self._pending:
            data = self.sock.recv(4096)
            if not data:
                return None
            self._pending.extend(self._reader.feed(data))
        return self._pending.popleft()

    def send(self, packet: dict) -> bool:
        try:
            with self._send_lock:
                self.sock.sendall(encode_packet(packet))
            return True
        except OSError:
            return False

    def close(self) -> None:
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()


class ChatServer:
    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT, data_dir=None) -> None:
        self.host = host
        self.port = port
        self.storage = Storage(data_dir)
        self.sessions: dict[str, Session] = {}   # lower-case username -> session
        self.lock = threading.RLock()
        self.ready = threading.Event()           # set once the socket is listening
        self._stop = threading.Event()
        self._sock: socket.socket | None = None

    # ------------------------------------------------------------- lifecycle
    def serve_forever(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen()
        self._sock.settimeout(0.5)               # lets the loop notice shutdown()
        self.port = self._sock.getsockname()[1]  # useful when port=0 (tests)
        log.info("Listening on %s:%s", self.host, self.port)
        self.ready.set()
        while not self._stop.is_set():
            try:
                client, address = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_client, args=(client, address),
                             daemon=True).start()
        self._sock.close()

    def shutdown(self) -> None:
        self._stop.set()
        with self.lock:
            for session in list(self.sessions.values()):
                session.close()

    # ------------------------------------------------------- client handling
    def _handle_client(self, sock: socket.socket, address) -> None:
        session = Session(sock, address)
        try:
            sock.settimeout(AUTH_TIMEOUT)
            if not self._authenticate(session):
                return
            sock.settimeout(None)
            self._announce_join(session)
            while (packet := session.next_packet()) is not None:
                self._dispatch(session, packet)
        except (OSError, ProtocolError) as exc:
            log.debug("Connection %s ended: %s", address, exc)
        finally:
            self._disconnect(session)

    def _authenticate(self, session: Session) -> bool:
        packet = session.next_packet()
        if packet is None:
            return False
        if packet["type"] != LOGIN:
            session.send({"type": LOGIN_ERROR, "reason": "Please log in first."})
            return False

        username = str(packet.get("username", "")).strip()
        password = str(packet.get("password") or "")
        avatar = packet.get("avatar") if packet.get("avatar") in AVATARS else AVATARS[0]
        if not USERNAME_PATTERN.match(username):
            session.send({"type": LOGIN_ERROR, "reason": USERNAME_RULES})
            return False

        with self.lock:
            if username.lower() in self.sessions:
                session.send({"type": LOGIN_ERROR,
                              "reason": "That user is already connected."})
                return False
            ok, reason = self.storage.authenticate(username, password, avatar)
            if not ok:
                session.send({"type": LOGIN_ERROR, "reason": reason})
                return False
            # keep the capitalisation chosen when the account was created
            username = self.storage.find_account(username)["username"]
            session.username, session.avatar = username, avatar
            self.sessions[username.lower()] = session
            # login_ok is sent while holding the lock so no other packet can
            # reach this client before it.
            session.send({
                "type": LOGIN_OK, "username": username, "avatar": avatar,
                "users": self._users_snapshot(),
                "history": self.storage.history_for(username),
            })
        log.info("%s logged in from %s", username, session.address[0])
        return True

    def _disconnect(self, session: Session) -> None:
        was_online = False
        if session.username:
            with self.lock:
                if self.sessions.get(session.username.lower()) is session:
                    del self.sessions[session.username.lower()]
                    was_online = True
        session.close()
        if was_online:
            log.info("%s disconnected", session.username)
            self._broadcast({"type": SYSTEM, "timestamp": time.time(),
                             "text": f"🔴 {session.avatar} {session.username} left the chat."})
            self._broadcast_users()

    # -------------------------------------------------------------- dispatch
    def _dispatch(self, session: Session, packet: dict) -> None:
        kind = packet.get("type")
        if kind == MESSAGE:
            self._on_message(session, packet)
        elif kind == EDIT:
            self._on_edit(session, packet)
        else:
            session.send({"type": ERROR, "reason": "Unknown request."})

    @staticmethod
    def _clean_text(value) -> str | None:
        if not isinstance(value, str):
            return None
        value = value.strip()
        if not value or len(value) > MAX_MESSAGE_LENGTH:
            return None
        return value

    def _on_message(self, session: Session, packet: dict) -> None:
        text = self._clean_text(packet.get("text"))
        if text is None:
            session.send({"type": ERROR,
                          "reason": f"Messages must be 1-{MAX_MESSAGE_LENGTH} characters."})
            return
        target = packet.get("to")
        recipient = None
        if target not in (None, "", PUBLIC_CHAT):
            account = self.storage.find_account(target)
            if account is None:
                session.send({"type": ERROR, "reason": "That user does not exist."})
                return
            recipient = account["username"]

        message = {
            "id": uuid.uuid4().hex[:12], "sender": session.username, "avatar": session.avatar,
            "text": text, "timestamp": time.time(), "to": recipient, "edited": False,
        }
        self.storage.add_message(message)
        self._deliver(message, {"type": MESSAGE, "message": message})

    def _on_edit(self, session: Session, packet: dict) -> None:
        text = self._clean_text(packet.get("text"))
        if text is None:
            session.send({"type": ERROR, "reason": "Edited text is not valid."})
            return
        message = self.storage.edit_message(str(packet.get("id", "")), session.username, text)
        if message is None:
            session.send({"type": ERROR, "reason": "You can only edit your own messages."})
            return
        self._deliver(message, {"type": EDITED, "id": message["id"], "text": text})

    # ------------------------------------------------------------- sending
    def _deliver(self, message: dict, packet: dict) -> None:
        """Send a packet to everyone who may see ``message``."""
        with self.lock:
            if message["to"]:
                keys = {message["sender"].lower(), message["to"].lower()}
                targets = [self.sessions[k] for k in keys if k in self.sessions]
            else:
                targets = list(self.sessions.values())
        for session in targets:
            session.send(packet)

    def _broadcast(self, packet: dict) -> None:
        with self.lock:
            targets = list(self.sessions.values())
        for session in targets:
            session.send(packet)

    def _users_snapshot(self) -> list[dict]:
        with self.lock:
            users = []
            for account in self.storage.list_accounts():
                live = self.sessions.get(account["username"].lower())
                users.append({"username": account["username"],
                              "avatar": live.avatar if live else account["avatar"],
                              "online": live is not None})
            return users

    def _broadcast_users(self) -> None:
        self._broadcast({"type": USERS, "users": self._users_snapshot()})

    def _announce_join(self, session: Session) -> None:
        self._broadcast({"type": SYSTEM, "timestamp": time.time(),
                         "text": f"🟢 {session.avatar} {session.username} joined the chat!"})
        self._broadcast_users()
