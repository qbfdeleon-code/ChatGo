"""Integration tests: real sockets against a real (in-memory) server."""
import socket
import time

import pytest

from common import protocol
from server.server import ChatServer


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

    def login(self, name, password="", avatar="😎"):
        self.send(type="login", username=name, password=password, avatar=avatar)
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
        peer = Peer(server.port)
        peers.append(peer)
        if name:
            assert peer.login(name, **kw)["type"] == "login_ok"
        return peer

    yield _connect
    for p in peers:
        p.close()


def test_login_returns_session(connect):
    reply = connect().login("Hail", avatar="😎")
    assert reply["type"] == "login_ok"
    assert reply["username"] == "Hail" and reply["avatar"] == "😎"
    assert reply["history"] == []


def test_invalid_username_rejected(connect):
    assert connect().login("x")["type"] == "login_error"


def test_wrong_password_rejected(connect, server):
    first = connect("Maria", password="secret")
    first.close()
    assert connect().login("Maria", password="nope")["type"] == "login_error"
    for _ in range(20):                      # wait for the server to notice the disconnect
        if "Maria" not in server.sessions:
            break
        time.sleep(0.05)
    assert connect().login("Maria", password="secret")["type"] == "login_ok"


def test_duplicate_login_rejected(connect):
    connect("Hail")
    assert connect().login("hail")["type"] == "login_error"


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


def test_edit_own_message_only(connect):
    a, b = connect("Alice"), connect("Bob")
    a.send(type="message", to=None, text="helo")
    msg_id = b.recv_type("message")["message"]["id"]
    b.send(type="edit", id=msg_id, text="hacked")
    assert b.recv_type("error")
    a.send(type="edit", id=msg_id, text="hello")
    edited = b.recv_type("edited")
    assert edited["id"] == msg_id and edited["text"] == "hello"


def test_history_sent_on_login(connect):
    a = connect("Alice")
    a.send(type="message", to=None, text="before you joined")
    a.recv_type("message")
    history = connect().login("Bob")["history"]
    assert [m["text"] for m in history] == ["before you joined"]
