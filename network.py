"""Connection to the server."""
import json
import socket
import threading

from PyQt6.QtCore import QObject, pyqtSignal


class LoginError(Exception):
    """Login failed."""


class ServerConnection(QObject):
    packet_received = pyqtSignal(dict)     # new data from the server
    disconnected = pyqtSignal()            # the connection was lost

    def __init__(self):
        super().__init__()
        self.sock = None
        self.reader = None
        self.closing = False

    def connect_and_login(self, host, port, mode, username, password, avatar=None, picture=None):
        """Connect, then log in or sign up."""
        packet = {"type": mode, "username": username, "password": password}
        if mode == "register":
            packet["avatar"] = avatar
            packet["picture"] = picture
        try:
            self.sock = socket.create_connection((host, port), timeout=5)
            self.reader = self.sock.makefile("r", encoding="utf-8")
            self.send(packet)
            line = self.reader.readline()
        except OSError:
            self.close()
            raise ConnectionError("Could not connect to the server.")

        if line == "":
            self.close()
            raise ConnectionError("The server closed the connection.")
        reply = json.loads(line)
        if reply.get("type") != "login_ok":
            self.close()
            raise LoginError(reply.get("reason", "Login failed."))
        self.sock.settimeout(None)
        return reply

    def start_listening(self):
        """Listen for packets in the background."""
        threading.Thread(target=self.listen, daemon=True).start()

    def listen(self):
        try:
            for line in self.reader:
                try:
                    self.packet_received.emit(json.loads(line))
                except ValueError:
                    pass
        except (OSError, ValueError):
            pass
        if not self.closing:
            self.disconnected.emit()

    def send(self, packet):
        """Returns True if the packet was sent."""
        if self.sock is None:
            return False
        try:
            self.sock.sendall((json.dumps(packet, ensure_ascii=False) + "\n").encode("utf-8"))
            return True
        except OSError:
            return False

    def close(self):
        self.closing = True
        if self.sock is not None:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)    # stop the listener
            except OSError:
                pass
        for item in (self.reader, self.sock):
            try:
                if item:
                    item.close()
            except OSError:
                pass
        self.sock = None
