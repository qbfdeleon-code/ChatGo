"""ChatGo server.

Accepts clients, checks logins, and passes messages between users.
Accounts are saved in users.json and messages in history.json.

Run it with:  python server.py
"""
import hashlib
import hmac
import json
import os
import re
import socket
import threading
import time

import config

USERS_FILE = "users.json"
HISTORY_FILE = "history.json"

lock = threading.RLock()    # the client threads share the data below, so we lock it
clients = {}                # username -> socket (only users who are online)


def load_file(filename, default):
    """Read a JSON file, or return `default` if it does not exist yet."""
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except ValueError:
            pass
    return default


def save_file(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


users = load_file(USERS_FILE, {})        # lowercase username -> account info
history = load_file(HISTORY_FILE, [])    # all messages, oldest first


# ---------------------------------------------------------------- sending
def send_packet(sock, packet):
    """Send one JSON packet (one line of text) to a client."""
    try:
        sock.sendall((json.dumps(packet, ensure_ascii=False) + "\n").encode("utf-8"))
    except OSError:
        pass


def broadcast(packet, skip=None):
    """Send a packet to everybody who is online."""
    with lock:
        for name, sock in list(clients.items()):
            if name != skip:
                send_packet(sock, packet)


def deliver(packet, sender, to):
    """Group messages go to everyone, private messages only to the two users."""
    if to is None:
        broadcast(packet)
        return
    with lock:
        for name in {sender, to}:
            if name in clients:
                send_packet(clients[name], packet)


# ---------------------------------------------------------------- accounts
def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()


def user_info(account):
    """The public part of an account (never includes the password)."""
    return {
        "username": account["username"],
        "avatar": account["avatar"],
        "picture": account["picture"],
        "online": account["username"] in clients,
    }


def register(packet):
    """Create a new account. Returns (username, error_message)."""
    name = str(packet.get("username", "")).strip()
    password = str(packet.get("password", ""))

    if not re.fullmatch(r"[A-Za-z0-9_]{2,20}", name):
        return None, "Username must be 2-20 letters, numbers or _."
    if len(password) < config.MIN_PASSWORD_LENGTH:
        return None, f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters."
    if name.lower() in users:
        return None, "That username is already taken."

    avatar = packet.get("avatar")
    if avatar not in config.AVATARS:
        avatar = config.AVATARS[0]
    picture = packet.get("picture")
    if not isinstance(picture, str) or len(picture) > config.MAX_PICTURE_TEXT:
        picture = None

    salt = os.urandom(8).hex()
    users[name.lower()] = {
        "username": name,
        "avatar": avatar,
        "picture": picture,
        "salt": salt,
        "password_hash": hash_password(password, salt),
    }
    save_file(USERS_FILE, users)
    return name, None


def login(packet):
    """Check a username and password. Returns (username, error_message)."""
    name = str(packet.get("username", "")).strip()
    password = str(packet.get("password", ""))
    account = users.get(name.lower())

    if account is None or not password:
        return None, "Wrong username or password."
    if not hmac.compare_digest(hash_password(password, account["salt"]),
                               account["password_hash"]):
        return None, "Wrong username or password."
    return account["username"], None


def history_for(username):
    """Group messages plus the private messages this user sent or received."""
    mine = [m for m in history
            if m["to"] is None or m["to"] == username or m["sender"] == username]
    return mine[-200:]


def authenticate(sock, packet):
    """Handle a login or register packet. Returns the username, or None if it failed."""
    with lock:
        if packet["type"] == "register":
            username, error = register(packet)
        else:
            username, error = login(packet)
        if error is None and username in clients:
            error = "That account is already logged in."
        if error:
            send_packet(sock, {"type": "login_error", "reason": error})
            return None

        clients[username] = sock
        account = users[username.lower()]
        send_packet(sock, {
            "type": "login_ok",
            "username": username,
            "avatar": account["avatar"],
            "picture": account["picture"],
            "users": [user_info(a) for a in users.values()],
            "history": history_for(username),
        })
        print(f"{username} joined")
        broadcast({"type": "status", "user": user_info(account)}, skip=username)
        broadcast({"type": "notice", "time": time.time(),
                   "text": f"🟢 {account['avatar']} {username} joined the chat!"}, skip=username)
    return username


# ---------------------------------------------------------------- messages
def handle_message(username, packet):
    text = str(packet.get("text", "")).strip()
    if text == "":
        return
    if len(text) > config.MAX_MESSAGE_LENGTH:
        send_packet(clients[username], {
            "type": "error",
            "reason": f"Message is too long (max {config.MAX_MESSAGE_LENGTH} characters)."})
        return

    with lock:
        to = packet.get("to")
        if to is not None:
            account = users.get(str(to).lower())
            if account is None:
                send_packet(clients[username], {"type": "error", "reason": "User not found."})
                return
            to = account["username"]

        message = {
            "id": len(history) + 1,
            "sender": username,
            "avatar": users[username.lower()]["avatar"],
            "to": to,                       # None means the group chat
            "text": text,
            "time": time.time(),
            "edited": False,
        }
        history.append(message)
        save_file(HISTORY_FILE, history)
        deliver({"type": "message", "message": message}, username, to)


def handle_edit(username, packet):
    text = str(packet.get("text", "")).strip()
    try:
        message_id = int(packet.get("id"))
    except (TypeError, ValueError):
        return
    if text == "" or len(text) > config.MAX_MESSAGE_LENGTH:
        send_packet(clients[username], {"type": "error", "reason": "Invalid message text."})
        return

    with lock:
        if message_id < 1 or message_id > len(history):
            return
        message = history[message_id - 1]
        if message["sender"] != username:           # you can only edit your own messages
            send_packet(clients[username], {"type": "error",
                                            "reason": "You can only edit your own messages."})
            return
        message["text"] = text
        message["edited"] = True
        save_file(HISTORY_FILE, history)
        deliver({"type": "edited", "id": message_id, "text": text, "to": message["to"]},
                username, message["to"])


# ---------------------------------------------------------------- clients
def handle_client(sock, address):
    """Runs in its own thread for every connected client."""
    username = None
    reader = sock.makefile("r", encoding="utf-8")
    try:
        for line in reader:
            try:
                packet = json.loads(line)
            except ValueError:
                continue
            if not isinstance(packet, dict):
                continue

            kind = packet.get("type")
            if username is None:                    # not logged in yet
                if kind in ("login", "register"):
                    username = authenticate(sock, packet)
            elif kind == "message":
                handle_message(username, packet)
            elif kind == "edit":
                handle_edit(username, packet)
    except (OSError, UnicodeDecodeError):
        pass
    finally:
        disconnect(username, sock)


def disconnect(username, sock):
    with lock:
        if username is not None and clients.get(username) is sock:
            del clients[username]
            print(f"{username} left")
            account = users[username.lower()]
            broadcast({"type": "status", "user": user_info(account)})
            broadcast({"type": "notice", "time": time.time(),
                       "text": f"🔴 {account['avatar']} {username} left the chat."})
    sock.close()


def run_server(host="0.0.0.0", port=config.PORT):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()

    print("================================")
    print("💬 CHATGO SERVER")
    print("================================")
    print(f"Waiting for users on port {port}... (Ctrl+C to stop)")

    try:
        while True:
            sock, address = server.accept()
            thread = threading.Thread(target=handle_client, args=(sock, address), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.close()


if __name__ == "__main__":
    run_server()
