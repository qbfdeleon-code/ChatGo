"""Integration tests: real sockets against a real (in-memory) server."""
import base64
import socket
import time

import pytest

from common import protocol
from server.server import ChatServer

PASSWORD = "secret1"


class Peer:
    """Tiny raw-socket client used to talk to the server."""

    def __init__(self, port):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=3)
        self.reader = self.sock.makefile("r", encoding="utf-8", newline="\n")

    def send(self, **packet):
        self.sock.sendall(protocol.encode(packet))

    def recv(self):
        return protocol.decode(self.reader.readline())

    def recv_type(self, kind):
        for _ in range(15):
            packet = self.recv()
            if packet["type"] == kind:
                return packet
        raise AssertionError(f"no {kind!r} packet received")

    def register(self, name, password=PASSWORD, avatar="😎", picture=None):
        self.send(type="register", username=name, password=password,
                  avatar=avatar, picture=picture)
        return self.recv()

    def login(self, name, password=PASSWORD):
        self.send(type="login", username=name, password=password)
        return self.recv()

    def close(self):
        self.reader.close()      # the buffered reader keeps the fd alive otherwise
        self.sock.close()


@pytest.fixture
def server():
    srv = ChatServer("127.0.0.1", 0, ":memory:")
    srv.start_in_background()
    yield srv
    srv.stop()


@pytest.fixture
def connect(server):
    peers = []

    def _connect(name=None, **kw):
        """New connection; with a name, registers that account and is logged in."""
        peer = Peer(server.port)
        peers.append(peer)
        if name:
            assert peer.register(name, **kw)["type"] == "login_ok"
        return peer

    yield _connect
    for p in peers:
        p.close()


def wait_offline(server, name):
    for _ in range(40):
        if name not in server.sessions:
            return
        time.sleep(0.05)
    raise AssertionError(f"{name} never disconnected")


# ------------------------------------------------------------------ accounts
def test_register_logs_in_and_returns_session(connect):
    reply = connect().register("Hail", avatar="😎")
    assert reply["type"] == "login_ok"
    assert reply["username"] == "Hail" and reply["avatar"] == "😎"
    assert reply["picture"] is None and reply["history"] == []


def test_invalid_username_rejected(connect):
    assert connect().register("x")["type"] == "login_error"


def test_short_password_rejected(connect):
    assert connect().register("Hail", password="abc")["type"] == "login_error"


def test_username_must_be_unique(connect):
    connect("Hail")
    assert connect().register("hail")["type"] == "login_error"


def test_login_checks_username_and_password(connect, server):
    connect("Maria", password="secret1").close()
    wait_offline(server, "Maria")
    assert connect().login("Maria", "wrong-pass")["type"] == "login_error"
    assert connect().login("Nobody", "secret1")["type"] == "login_error"
    assert connect().login("Maria", "")["type"] == "login_error"
    assert connect().login("Maria", "secret1")["type"] == "login_ok"


def test_duplicate_login_rejected(connect):
    connect("Hail")
    assert connect().login("hail")["type"] == "login_error"


def test_profile_picture_is_stored_and_shared(connect):
    picture = base64.b64encode(b"fake-image-bytes").decode()
    connect("Alice", picture=picture)
    users = {u["username"]: u for u in connect().register("Bob")["users"]}
    assert users["Alice"]["picture"] == picture
    assert users["Bob"]["picture"] is None


def test_invalid_picture_is_ignored(connect):
    reply = connect().register("Alice", picture="***not base64***")
    assert reply["type"] == "login_ok" and reply["picture"] is None


# ------------------------------------------------------------------ messages
def test_public_message_reaches_everyone(connect):
    a, b = connect("Alice"), connect("Bob")
    a.send(type="message", to=None, text="Hello!")
    for peer in (a, b):
        msg = peer.recv_type("message")["message"]
        assert msg["text"] == "Hello!" and msg["sender"] == "Alice" and msg["to"] is None


def test_direct_message_is_private(connect):
    a, b, c = connect("Alice"), connect("Bob"), connect("Cara")
    a.send(type="message", to="Bob", text="secret")
    assert b.recv_type("message")["message"]["text"] == "secret"
    assert a.recv_type("message")["message"]["to"] == "Bob"
    c.send(type="message", to=None, text="ping")
    assert c.recv_type("message")["message"]["text"] == "ping"   # first message Cara sees


def test_message_length_limit(connect):
    a = connect("Alice")
    a.send(type="message", to=None, text="x" * protocol.MAX_MESSAGE_LENGTH)
    assert len(a.recv_type("message")["message"]["text"]) == 300
    a.send(type="message", to=None, text="x" * (protocol.MAX_MESSAGE_LENGTH + 1))
    assert "300" in a.recv_type("error")["reason"]


def test_edit_own_message_only(connect):
    a, b = connect("Alice"), connect("Bob")
    a.send(type="message", to=None, text="helo")
    msg_id = b.recv_type("message")["message"]["id"]
    b.send(type="edit", id=msg_id, text="hacked")
    assert b.recv_type("error")
    a.send(type="edit", id=msg_id, text="hello")
    edited = b.recv_type("edited")
    assert edited["id"] == msg_id and edited["text"] == "hello"


def test_edit_respects_length_limit(connect):
    a = connect("Alice")
    a.send(type="message", to=None, text="short")
    msg_id = a.recv_type("message")["message"]["id"]
    a.send(type="edit", id=msg_id, text="y" * 301)
    assert a.recv_type("error")


def test_history_sent_on_login(connect):
    a = connect("Alice")
    a.send(type="message", to=None, text="before you joined")
    a.recv_type("message")
    history = connect().register("Bob")["history"]
    assert [m["text"] for m in history] == ["before you joined"]
