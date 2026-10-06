"""Client-side networking: connect, log in, then listen for packets on a thread."""
from __future__ import annotations

import socket
import threading

from PyQt6.QtCore import QObject, pyqtSignal

from common import protocol


class LoginError(Exception):
    """The server rejected the login (bad password, name taken, ...)."""


class NetworkClient(QObject):
    packet_received = pyqtSignal(dict)   # emitted from the reader thread (queued to the GUI)
    disconnected = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._sock: socket.socket | None = None
        self._reader = None
        self._send_lock = threading.Lock()
        self._closing = False

    def connect_and_login(self, host: str, port: int, username: str, password: str,
                          avatar: str, timeout: float = 5.0) -> dict:
        """Blocking connect + login handshake. Returns the ``login_ok`` packet."""
        try:
            self._sock = socket.create_connection((host, port), timeout=timeout)
            self._reader = self._sock.makefile("r", encoding="utf-8", newline="\n")
            self._sock.sendall(protocol.encode({
                "type": "login", "username": username, "password": password, "avatar": avatar,
            }))
            line = self._reader.readline()
            if not line:
                raise ConnectionError("The server closed the connection.")
            reply = protocol.decode(line)
        except (OSError, ValueError) as exc:
            self.close()
            raise ConnectionError(str(exc) or "Could not connect.") from exc
        except ConnectionError:
            self.close()
            raise

        if reply.get("type") != "login_ok":
            self.close()
            raise LoginError(reply.get("reason", "Login failed."))
        self._sock.settimeout(None)
        return reply

    def start_listening(self) -> None:
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self) -> None:
        try:
            for line in self._reader:
                try:
                    self.packet_received.emit(protocol.decode(line))
                except ValueError:
                    continue
        except (OSError, ValueError):
            pass
        if not self._closing:
            self.disconnected.emit("Connection to the server was lost.")

    def send(self, packet: dict) -> bool:
        if self._sock is None:
            return False
        try:
            with self._send_lock:
                self._sock.sendall(protocol.encode(packet))
            return True
        except OSError:
            return False

    def close(self) -> None:
        self._closing = True
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        for resource in (self._reader, self._sock):
            try:
                if resource:
                    resource.close()
            except OSError:
                pass
        self._sock = None
